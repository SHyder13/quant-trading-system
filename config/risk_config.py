# The fixed dollar amount to risk on a single trade. This will be used instead of RISK_PER_TRADE if set.
RISK_DOLLAR_AMOUNT = 250

# The percentage of account equity to risk on a single trade. Used if RISK_DOLLAR_AMOUNT is None.
RISK_PER_TRADE = 0.01 # 1%

# The maximum number of contracts to hold in a single position.
MAX_POSITION_SIZE = 10
# The maximum daily loss limit. The bot will stop trading for the day if this is hit.
MAX_DAILY_LOSS = -500

# The daily profit goal. The bot will stop trading for the day if this is hit.
DAILY_PROFIT_GOAL = 500
MAX_LEVERAGE = 3.0

# Defines the tolerance in points for a price to be considered 'at' a level.
LEVEL_TOLERANCE_POINTS = 1.5

# Defines the buffer in points to be placed beyond the retest candle's high/low for a stop-loss.
# This is now symbol-specific to account for varying volatility.
STOP_LOSS_BUFFER_POINTS = {
    'MNQ': 25.0,  # Higher volatility, needs a wider stop
    'MES': 3.0,   # Lower volatility
    'M2K': 7.5
}
POSITION_CONCENTRATION_LIMIT = 0.05

# A multiplier to increase risk on high-conviction setups (e.g., 13 EMA touch at a key level).
# A value of 1.5 would risk 1.5x the standard RISK_DOLLAR_AMOUNT.
HIGH_CONVICTION_RISK_MULTIPLIER = 1.5

# The initial account balance to be used by the backtester.
INITIAL_ACCOUNT_BALANCE = 2000

# The risk-to-reward ratio for setting take-profit targets.
# A value of 2.0 means the take-profit will be set at twice the risk distance.
TAKE_PROFIT_RRR = 2.0
