class RiskCalculator:
    def __init__(self, risk_config):
        self.risk_config = risk_config

    def check_portfolio_risk(self, portfolio):
        print("Checking portfolio risk...")
        # Add portfolio risk calculation logic here
        # Example: check max daily loss
        if portfolio.daily_pnl < self.risk_config.MAX_DAILY_LOSS:
            return 'HALT_TRADING'
        return 'OK'
