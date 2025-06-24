class PerformanceTracker:
    def __init__(self):
        self.trades = []

    def record_trade(self, trade_details):
        self.trades.append(trade_details)

    def calculate_sharpe_ratio(self):
        print("Calculating Sharpe Ratio...")
        # Add Sharpe Ratio calculation logic here
        return 1.5 # Example value

    def calculate_max_drawdown(self):
        print("Calculating Max Drawdown...")
        # Add Max Drawdown calculation logic here
        return -0.1 # Example value (10%)
