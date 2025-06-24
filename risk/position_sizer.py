import math
import config.market_config as market_config

class PositionSizer:
    def __init__(self, risk_config):
        self.risk_config = risk_config
        self.dollar_per_point = market_config.DOLLAR_PER_POINT

    def calculate_size(self, account_balance, entry_price, stop_loss_price, symbol, is_high_conviction=False):
        """
        Calculates position size using the fixed-fractional model.
        - account_balance: The total equity in the account.
        - entry_price: The expected entry price of the trade.
        - stop_loss_price: The price at which the trade will be exited for a loss.
        - symbol: The symbol being traded, to get its value per point.
        Returns the number of contracts to trade.
        """
        if symbol not in self.dollar_per_point:
            print(f"ERROR: Dollar per point not defined for symbol {symbol}.")
            return 0

        # 1. Calculate risk per contract in dollars
        stop_loss_points = abs(entry_price - stop_loss_price)
        if stop_loss_points == 0:
            print("ERROR: Stop loss distance cannot be zero.")
            return 0
        
        value_per_point = self.dollar_per_point[symbol]
        risk_per_contract = stop_loss_points * value_per_point

        # 2. Calculate total risk amount for the trade
        risk_display = ""
        if hasattr(self.risk_config, 'RISK_DOLLAR_AMOUNT') and self.risk_config.RISK_DOLLAR_AMOUNT is not None:
            total_risk_amount = self.risk_config.RISK_DOLLAR_AMOUNT
            risk_display = f"${total_risk_amount:,.2f}"
        else:
            total_risk_amount = account_balance * self.risk_config.RISK_PER_TRADE
            risk_display = f"{self.risk_config.RISK_PER_TRADE*100}%"

        # 2a. Apply conviction multiplier if applicable
        if is_high_conviction:
            total_risk_amount *= self.risk_config.HIGH_CONVICTION_RISK_MULTIPLIER
            print(f"  - High conviction setup! Applying {self.risk_config.HIGH_CONVICTION_RISK_MULTIPLIER}x risk multiplier. New risk: ${total_risk_amount:,.2f}")
            risk_display += f" (x{self.risk_config.HIGH_CONVICTION_RISK_MULTIPLIER} Conviction)"

        # 3. Calculate position size
        if risk_per_contract == 0:
            print("ERROR: Risk per contract is zero. Cannot calculate position size.")
            return 0
            
        position_size = total_risk_amount / risk_per_contract
        
        # 4. Adjust for limits and round down
        final_size = math.floor(position_size)
        
        if final_size > self.risk_config.MAX_POSITION_SIZE:
            final_size = self.risk_config.MAX_POSITION_SIZE
            
        if final_size == 0:
            print("Warning: Calculated position size is zero. Risk may be too high for account size.")

        print(f"Position Sizing: Acct=${account_balance:,.2f}, Risk/Trade={risk_display}, SL_Points={stop_loss_points:.2f}, Risk/Contract=${risk_per_contract:.2f} -> Size={final_size} contracts")

        return final_size
