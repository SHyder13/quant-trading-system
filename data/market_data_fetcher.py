import requests
import pandas as pd
from datetime import datetime, timedelta

class MarketDataFetcher:
    def __init__(self, session_token, base_url="https://gateway-api-demo.s2f.projectx.com/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {session_token}'})
        print("MarketDataFetcher initialized with session token.")

    def fetch_ohlcv(self, symbol, timeframe='1D', limit=100):
        """Fetches historical OHLCV data for a given symbol using the new API method."""

        contract_id = self._get_contract_id(symbol)
        if not contract_id:
            print(f"Could not find a contract for symbol '{symbol}'.")
            return None


        endpoint = f"{self.base_url}/History/retrieveBars"
        
        # Map our timeframe to the API's 'unit' parameter
        timeframe_map = {'1D': 4, '1H': 3, '1m': 2, '2m': 2} # Added '2m'
        unit = timeframe_map.get(timeframe)
        if not unit:
            print(f"Unsupported timeframe: {timeframe}")
            return None

        # Set unitNumber based on timeframe
        unit_number = 1
        if timeframe == '2m':
            unit_number = 2

        # Define the time range for the request, as it's likely required by the API.
        end_time = datetime.utcnow()
        # Fetch a few extra days of data to ensure we have what we need.
        start_time = end_time - timedelta(days=limit + 5)

        payload = {
            "contractId": contract_id,
            "live": False,
            "startTime": start_time.isoformat() + "Z",
            "endTime": end_time.isoformat() + "Z",
            "unit": unit,
            "unitNumber": unit_number, # Use dynamic unit_number
            "limit": limit, 
            "includePartialBar": False
        }

        try:
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

            if not data.get('success') or 'bars' not in data:
                # print(f"API Error while fetching bars: {data.get('errorMessage', 'No bars in response')}")
                return None

            # Convert to pandas DataFrame
            df = pd.DataFrame(data['bars'])
            if df.empty:
                # print(f"No historical data returned for {symbol}.")
                return None
                
            df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            

            return df.iloc[::-1] # Reverse to have oldest data first

        except requests.exceptions.RequestException as e:
            # print(f"Error fetching OHLCV data for {symbol}: {e}")
            return None

    def fetch_historical_data(self, symbol, start_date_str, end_date_str, timeframe='1m'):
        """Fetches historical OHLCV data for a given symbol between two dates using pagination."""
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))

        # print(f"DEBUG: fetch_historical_data received start_date: {start_date}")
        contract_id = self._get_contract_id(symbol, start_date)
        if not contract_id:
            return None

        timeframe_map = {'1D': 4, '1H': 3, '1m': 2, '2m': 2}
        unit = timeframe_map.get(timeframe)
        if not unit:
            # print(f"Unsupported timeframe: {timeframe}")
            return None
        unit_number = 2 if timeframe == '2m' else 1

        all_bars_df = pd.DataFrame()
        current_start = start_date


        while current_start < end_date:
            chunk_end = min(current_start + timedelta(days=7), end_date)


            payload = {
                "contractId": contract_id,
                "live": False,
                "startTime": current_start.isoformat().replace('+00:00', 'Z'),
                "endTime": chunk_end.isoformat().replace('+00:00', 'Z'),
                "unit": unit,
                "unitNumber": unit_number,
                "limit": 5000,  # Add a generous limit, pagination is handled by the date range
                "includePartialBar": False
            }
            # print(f"DEBUG: Fetching chunk with payload: {payload}")

            try:
                response = self.session.post(f"{self.base_url}/History/retrieveBars", json=payload)
                response.raise_for_status()
                data = response.json()

                if data.get('success') and 'bars' in data and data['bars']:
                    df = pd.DataFrame(data['bars'])
                    all_bars_df = pd.concat([all_bars_df, df])
                else:
                    # print(f"    - No bars in response or API error: {data.get('errorMessage', 'Empty response')}")
                    current_start = chunk_end
                    continue

            except requests.exceptions.RequestException as e:
                print(f"Error fetching chunk for {symbol}: {e}")
                # Decide if we should stop or continue
                break
            
            current_start = chunk_end

        if all_bars_df.empty:
            print(f"No historical data could be fetched for {symbol} in the specified range.")
            return None

        # Process the final combined dataframe
        all_bars_df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
        all_bars_df['timestamp'] = pd.to_datetime(all_bars_df['timestamp'])
        all_bars_df.set_index('timestamp', inplace=True)
        # Remove duplicates from overlapping requests and sort
        all_bars_df = all_bars_df[~all_bars_df.index.duplicated(keep='first')]
        all_bars_df.sort_index(inplace=True)

        print(f"Successfully fetched a total of {len(all_bars_df)} historical data points for {symbol}.")
        return all_bars_df

    def _get_contract_id(self, symbol, historical_date=None):
        """
        Helper to get a contract ID.
        - For historical data, it determines the correct contract based on the date.
        - For live data, it searches for the currently active contract.
        """
        symbol_map = {'MNQ': 'NQ', 'MES': 'EP'}
        search_symbol = symbol_map.get(symbol, symbol)

        print(f"Searching for contract for '{symbol}' (using search term '{search_symbol}')...")
        endpoint = f"{self.base_url}/Contract/search"
        payload = {"live": False, "searchText": search_symbol}
        
        try:
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

            if not (data and data.get('success') and data.get('contracts')):
                print(f"Could not find any contract for {symbol} in response: {data}")
                return None

            contracts = data['contracts']

            if historical_date:
                month = historical_date.month
                year_short = str(historical_date.year)[-2:]
                
                if 1 <= month <= 3: contract_month_code = 'H'
                elif 4 <= month <= 6: contract_month_code = 'M'
                elif 7 <= month <= 9: contract_month_code = 'U'
                else: contract_month_code = 'Z'
                
                expected_suffix = contract_month_code + year_short
                print(f"Historical date provided. Searching for contract with suffix: {expected_suffix}")

                for contract in contracts:
                    contract_name = contract.get('name', '')
                    if symbol in contract_name and expected_suffix in contract_name:
                        print(f"Found historical contract: {contract.get('description')} with ID: {contract['id']}")
                        return contract['id']
                
                print(f"Warning: Could not find a specific historical contract for {symbol} with suffix {expected_suffix}. Falling back to the first available contract for the symbol.")
                # Fallback to first contract that matches the symbol if specific date not found
                for contract in contracts:
                    if symbol in contract.get('name', ''):
                        return contract['id']
                return contracts[0]['id'] # Further fallback

            else: # Live data: find active contract
                for contract in contracts:
                    if contract.get('activeContract') and symbol in contract.get('name', ''):
                        print(f"Found active contract: {contract.get('description')} with ID: {contract['id']}")
                        return contract['id']
                
                print(f"Warning: No specific active contract found for {symbol}. Falling back to the first in the list.")
                return contracts[0]['id']

        except requests.exceptions.RequestException as e:
            print(f"Error searching for contract {symbol}: {e}")
            return None
