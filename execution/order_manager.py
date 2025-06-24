import config.risk_config as risk_config
from risk.position_sizer import PositionSizer
from risk.take_profit_manager import TakeProfitManager

class OrderManager:
    def __init__(self, broker_interface, account_balance):
        """Initializes the OrderManager with a broker interface and account balance."""
        self.broker_interface = broker_interface
        self.position_sizer = PositionSizer(risk_config)
        self.tp_manager = TakeProfitManager(risk_config)
        self.account_balance = account_balance
        self.active_orders = {} # To track orders

    def execute_trade(self, symbol, side, entry_price, stop_loss_price, is_high_conviction=False):
        """
        Manages the entire lifecycle of a trade: sizing, calculating TP, and placing a native OCA bracket order.
        """
        print(f"--- Initiating Trade Execution for {side} {symbol} ---")
        
        # 1. Calculate Position Size with potential conviction boost
        quantity = self.position_sizer.calculate_size(
            account_balance=self.account_balance,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            symbol=symbol,
            is_high_conviction=is_high_conviction
        )
        
        if quantity == 0:
            print("TRADE FAILED: Position size is zero. Aborting trade.")
            return None

        # 2. Calculate Take-Profit Price
        take_profit_price = self.tp_manager.calculate_take_profit(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            side=side
        )

        print(f"  - Calculated Entry: {entry_price:.2f}, SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}")

        # 3. Place the single OCA bracket order
        print(f"  - Submitting {side} market order for {quantity} lot(s) of {symbol} with OCA bracket...")
        
        order_id = self.broker_interface.submit_order(
            symbol=symbol,
            quantity=quantity,
            order_type='MARKET',
            side=side,
            stop_price=stop_loss_price,    # Pass SL price for the bracket
            limit_price=take_profit_price  # Pass TP price for the bracket
        )

        if order_id:
            print(f"--- SUCCESS: Trade executed. Order ID: {order_id} ---")
            self.active_orders[order_id] = {'status': 'PENDING', 'symbol': symbol, 'side': side, 'type': 'MARKET_BRACKET'}
            return order_id, quantity
        else:
            print("--- TRADE FAILED: Broker failed to submit the order. ---")
            return None, 0

    def close_position(self, symbol, side, quantity, original_order_id):
        """Closes an open position by submitting an opposing market order and cancelling the original bracket."""
        print(f"--- Initiating Position Close for {side} {symbol} ---")
        
        # 1. Cancel the original Stop-Loss/Take-Profit bracket order
        print(f"  - Cancelling original bracket order: {original_order_id}")
        self.cancel_order(original_order_id)

        # 2. Submit an opposing market order to flatten the position
        closing_side = 'SELL' if side == 'BUY' else 'BUY'
        print(f"  - Submitting {closing_side} market order for {quantity} lot(s) of {symbol} to close position...")
        
        close_order_id = self.broker_interface.submit_order(
            symbol=symbol,
            quantity=quantity,
            order_type='MARKET',
            side=closing_side,
        )

        if close_order_id:
            print(f"--- SUCCESS: Position close order submitted. Order ID: {close_order_id} ---")
        else:
            print("--- FAILED: Broker failed to submit the closing order. Manual intervention may be required. ---")
            
        return close_order_id

    def cancel_order(self, order_id):
        """Cancels a single order by its ID."""
        if not order_id or order_id not in self.active_orders:
            return False
        
        success = self.broker_interface.cancel_order(order_id)
        if success:
            del self.active_orders[order_id]
        return success
