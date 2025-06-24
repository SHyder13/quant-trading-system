class Position:
    """Represents a single open position in the portfolio."""
    def __init__(self, symbol, quantity, entry_price, side, stop_order_id=None):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.side = side  # 'BUY' or 'SELL'
        self.stop_order_id = stop_order_id

    def __repr__(self):
        return (f"Position(symbol={self.symbol}, quantity={self.quantity}, "
                f"entry_price={self.entry_price}, side={self.side}, stop_order_id={self.stop_order_id})")

class PortfolioManager:
    def __init__(self, starting_capital=100000):
        self.positions = {} # Key: symbol, Value: Position object
        self.cash = starting_capital
        self.starting_capital = starting_capital

    def add_position(self, symbol, quantity, entry_price, side, stop_order_id=None):
        """Adds a new position to the portfolio."""
        if self.has_position(symbol):
            print(f"Warning: Cannot add new position for {symbol}. A position already exists.")
            return False
        
        new_position = Position(symbol, quantity, entry_price, side, stop_order_id)
        self.positions[symbol] = new_position
        print(f"Portfolio: Added {new_position}")
        return True

    def remove_position(self, symbol):
        """Removes a position from the portfolio (e.g., when closed)."""
        if not self.has_position(symbol):
            print(f"Warning: Cannot remove position for {symbol}. No position exists.")
            return
        
        removed_position = self.positions.pop(symbol)
        print(f"Portfolio: Removed {removed_position}")

    def get_position(self, symbol):
        """Retrieves the position for a given symbol."""
        return self.positions.get(symbol)

    def has_position(self, symbol):
        """Checks if a position exists for a given symbol."""
        return symbol in self.positions

    def get_all_positions(self):
        """Returns a list of all current positions."""
        return list(self.positions.values())

    def get_account_balance(self):
        """Calculates the total account value (cash + unrealized P&L). STUB for now."""
        # This is a simplified version. A real implementation would mark-to-market all open positions.
        return self.cash
