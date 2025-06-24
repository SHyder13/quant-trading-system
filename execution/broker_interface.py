import requests
import logging
from datetime import datetime, timedelta

class BrokerInterface:
    def __init__(self, username, api_key, account_name, base_url="https://api.topstepx.com/api"):
        self.base_url = base_url
        self.username = username
        self.api_key = api_key
        self.account_name = account_name
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.session_token = None
        self.token_expiration = None
        self.account_id = None
        self.account_balance = None
        self.contract_cache = {}
        self._authenticate()

    def _authenticate(self):
        """Logs in to the API to get a new session token."""
        print("Authenticating with API...")
        endpoint = 'Auth/loginKey'
        url = f"{self.base_url}/{endpoint}"
        payload = {"userName": self.username, "apiKey": self.api_key}
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get('success') and data.get('token'):
                self.session_token = data['token']
                self.token_expiration = datetime.now() + timedelta(hours=23, minutes=55) # Refresh before 24h
                self.session.headers.update({'Authorization': f'Bearer {self.session_token}'})
                print("Authentication successful. Session token obtained.")
                self._initialize_broker_details()
                return True
            else:
                logging.critical(f"Authentication failed: {data.get('errorMessage', 'No token in response')}")
                return False
        except requests.exceptions.RequestException as e:
            logging.critical(f"Authentication request failed: {e}")
            return False

    def _refresh_token(self):
        """Refreshes the current session token."""
        print("Refreshing session token...")
        endpoint = 'Auth/validate'
        # This endpoint might not return a new token directly, but re-validates.
        # Based on docs, it seems we might need to re-authenticate fully.
        # For now, let's assume re-authentication is the safest path.
        return self._authenticate()

    def _is_token_valid(self):
        """Checks if the token exists and is not expired."""
        return self.session_token and datetime.now() < self.token_expiration

    def _initialize_broker_details(self):
        """Fetches account details after a successful authentication."""
        account = self._get_active_account(self.account_name)
        if account:
            self.account_id = account.get('id')
            self.account_balance = account.get('balance')
            print(f"Broker initialized for account '{account.get('name')}'. ID: {self.account_id}, Balance: {self.account_balance}")
        else:
            logging.error(f"CRITICAL: Could not retrieve account '{self.account_name}'. Order placement will fail.")

    def _make_request(self, method, endpoint, **kwargs):
        """Centralized request function with token management."""
        if not self._is_token_valid():
            print("Session token invalid or expired. Re-authenticating...")
            if not self._authenticate():
                return None # Stop if authentication fails

        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            if response.status_code == 401:
                print("Received 401 Unauthorized. Token may have been invalidated. Re-authenticating...")
                if self._authenticate():
                    # Retry the request once after re-authentication
                    response = self.session.request(method, url, **kwargs)
            
            response.raise_for_status()
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                # Successful request (2xx status) but empty or non-JSON body.
                # This can happen on successful order placement.
                return {'success': True, 'data': None}
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error on endpoint '{endpoint}': {http_err} - {http_err.response.text}")
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request error on endpoint '{endpoint}': {req_err}")
        return None

    def _get_active_account(self, account_name):
        """Fetches the full object for the specified active account by name."""
        print(f"Searching for active account: {account_name}...")
        payload = {"onlyActiveAccounts": True}
        data = self._make_request('POST', 'account/search', json=payload)
        if data and data.get('success') and data.get('accounts'):
            for account in data['accounts']:
                if account.get('name') == account_name:
                    print(f"Found active account: ID {account.get('id')}, Name: {account.get('name')}, Balance {account.get('balance')}")
                    return account
            
            logging.error(f"Account '{account_name}' not found in the list of active accounts.")
            return None
        else:
            logging.error(f"Failed to get account details. Response: {data}")
            return None

    def get_account_balance(self):
        """Returns the account balance stored during initialization."""
        return self.account_balance

    def get_latest_bar(self, symbol):
        """Fetches the most recent 1-minute bar for a symbol."""
        print(f"Fetching latest bar for {symbol}...")
        # We fetch 1 bar from 5 minutes ago to now to ensure we get data
        start_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"
        end_time = datetime.utcnow().isoformat() + "Z"
        
        contract_id = self._get_contract_id(symbol)
        if not contract_id:
            return None

        bar_request_details = {
            'contractId': contract_id,
            'unit': 2, # 2 = Minute
            'unitNumber': 1,
            'startTime': start_time,
            'endTime': end_time,
            'includePartialBar': True,
            'live': False, # Added missing required field
            'limit': 5     # Added missing required field, get a few bars to be safe
        }

        # The API requires the payload to be nested in a 'request' field, similar to order/place
        payload = bar_request_details.copy()
        payload['request'] = bar_request_details

        data = self._make_request('POST', 'history/retrieveBars', json=payload)
        if data and data.get('success') and data.get('bars'):
            return data['bars'][-1] # Return the most recent bar
        else:
            logging.error(f"Could not fetch latest bar for {symbol}. Response: {data}")
            return None

    def _get_contract_details(self, symbol):
        """Fetches the full contract details for a given symbol, using a cache."""
        # The cache now stores the full details dictionary, not just the ID.
        if symbol in self.contract_cache and isinstance(self.contract_cache[symbol], dict):
            return self.contract_cache[symbol]

        print(f"Fetching contract details for symbol: {symbol}...")
        payload = {"live": False, "searchText": symbol}
        data = self._make_request('POST', 'contract/search', json=payload)
        
        if data and data.get('success') and data.get('contracts'):
            contract_details = data['contracts'][0]
            print(f"Found contract '{contract_details.get('name')}' for symbol '{symbol}'")
            self.contract_cache[symbol] = contract_details # Cache the full details
            return contract_details
        else:
            logging.error(f"Failed to get contract details for {symbol}. Response: {data}")
            return None

    def _get_contract_id(self, symbol):
        """Fetches the contract ID from the cached contract details."""
        details = self._get_contract_details(symbol)
        if details:
            return details.get('id')
        return None

    def submit_order(self, symbol, quantity, order_type, side, stop_price=None, limit_price=None, **kwargs):
        """Submits an order to the broker, handling market and stop orders."""
        print(f"Submitting order: {side} {quantity} {symbol} @ {order_type}")
        contract_details = self._get_contract_details(symbol)
        if not self.account_id or not contract_details:
            logging.error("Cannot place order: Missing account_id or contract_details.")
            return None
        contract_id = contract_details.get('id')

        if not self.account_id or not contract_id:
            logging.error("Cannot place order: Missing account_id or contract_id.")
            return None

        # API requires integer codes for order types
        # Per documentation, Stop orders must be StopWithLimit (4), requiring a limit price.
        order_type_map = {'LIMIT': 1, 'MARKET': 2, 'STOP': 4}
        api_order_type = order_type_map.get(order_type.upper())
        if not api_order_type:
            logging.error(f"Invalid order type: {order_type}")
            return None

        # Based on platform feedback and further errors, the only remaining hypothesis
        # is a zero-indexed enum for the side. BUY=0, SELL=1.
        side_map = {'BUY': 0, 'SELL': 1}
        api_side = side_map.get(side.upper())
        if api_side is None:
            logging.error(f"Invalid order side: {side}")
            return None

        order_details = {
            "accountId": self.account_id,
            "contractId": contract_id,
            "type": api_order_type,
            "side": api_side,
            "size": quantity,
            "timeInForce": "GTC"
        }

        if api_order_type == 2: # Market Order with OCA bracket
            if stop_price and limit_price:
                print(f"  - Attaching OCA bracket with SL: {stop_price} and TP: {limit_price}")
                order_details['stopLoss'] = stop_price
                order_details['takeProfit'] = limit_price

        elif api_order_type == 4: # Standalone StopWithLimit Order
            if not stop_price:
                logging.error("Stop order requires a stop_price.")
                return None
            order_details['stopPrice'] = stop_price
            # For a StopWithLimit, we must also provide a limit price.
            # We'll set it a few ticks away to avoid missing a fill in a fast market.
            tick_size = contract_details.get('tickSize', 0.25)
            slippage_buffer = 10 * tick_size # 10 ticks slippage protection
            if side.upper() == 'SELL':
                sl_limit_price = stop_price - slippage_buffer
            else: # BUY
                sl_limit_price = stop_price + slippage_buffer
            order_details['limitPrice'] = sl_limit_price
            print(f"  - with Stop Price: {stop_price} and Limit Price: {sl_limit_price}")

        elif api_order_type == 1: # Limit Order
            if not limit_price:
                logging.error("Limit order requires a limit_price.")
                return None
            order_details['limitPrice'] = limit_price
            print(f"  - with Limit Price: {limit_price}")

        # The API validator is paradoxical, requiring both a flat payload for deserialization
        # and a 'request' field for a separate validation rule. The hybrid model is the only solution.
        payload = order_details.copy()
        payload['request'] = order_details

        response_data = self._make_request('POST', 'order/place', json=payload)
        
        if response_data and response_data.get('success'):
            # Successful submission, check if data and orderId are present
            if response_data.get('data') and response_data['data'].get('orderId'):
                order_id = response_data['data'].get('orderId')
                print(f"Order submitted successfully. Order ID: {order_id}")
                return order_id
            else:
                # Successful submission, but no immediate order ID returned.
                print("Order submitted successfully. Check platform for fill details.")
                return "SUBMITTED" # Return a generic success status
        else:
            error_msg = response_data.get('errorMessage', 'Unknown error') if response_data else 'No response'
            logging.error(f"Failed to submit order. Response: {error_msg}")
            return None

    def check_order_status(self, order_id):
        payload = {"orderId": order_id}
        data = self._make_request('POST', 'order/status', json=payload)
        if data and data.get('success') and data.get('data'):
            status = data['data'].get('status')
            print(f"Order {order_id} status: {status}")
            return status
        else:
            error_msg = data.get('errorMessage', 'Unknown error') if data else 'No response'
            logging.error(f"Failed to get order status: {error_msg}")
            return None

    def cancel_order(self, order_id):
        """Cancels an open order by its ID."""
        if not order_id:
            logging.error("Cannot cancel order: Missing order_id.")
            return False

        print(f"Cancelling order: {order_id}")
        payload = {"orderId": order_id}
        response_data = self._make_request('POST', 'order/cancel', json=payload)

        if response_data and response_data.get('success'):
            print(f"Order {order_id} cancelled successfully.")
            return True
        else:
            error_msg = response_data.get('errorMessage', 'Unknown error') if response_data else 'No response'
            logging.error(f"Failed to cancel order {order_id}. Response: {error_msg}")
            return False
