# strategy_config.py

# --- Break and Retest Strategy Parameters ---

# The symbols the bot is allowed to trade.
TRADABLE_SYMBOLS = ['MNQ', 'MES']

# The number of consecutive candle closes required to confirm a breakout.
BREAK_CONFIRMATION_CANDLES = 2

# Defines how close the price must get to a broken level to be considered a valid retest.
# This value is in points.
RETEST_TOLERANCE_POINTS = {
    'MNQ': 15.0, # Wider tolerance for volatile Nasdaq futures
    'MES': 4.5,  # Tighter tolerance for S&P futures
}

# The minimum volume required on a breakout candle for a signal to be considered valid.
# This is now a dictionary to support different thresholds per symbol.
MIN_BREAKOUT_VOLUME = {
    'MNQ': 80,  # Corresponds to NQ
    'MES': 20,   # Corresponds to ES
}

# Defines the minimum required ratio of the candle's body to its total range (high-low)
# for it to be considered a 'Conviction Candle'. A higher value means a more decisive candle.
CONVICTION_CANDLE_BODY_RATIO = {
    'MNQ': 0.7,  # Requires a strong 70% body
    'MES': 0.6,  # Slightly more lenient for MES
}

# The number of minutes to wait for a retest before invalidating the setup.
RETEST_TIMEOUT_MINUTES = 60

# If True, allows the bot to take trades that retest the 13 EMA as dynamic support/resistance,
# even if the price does not pull back to the original broken static level.
ALLOW_EMA_DIP_BUYS = True

# If True, requires the 13, 48, and 200 EMAs to be perfectly stacked in the direction of the
# trend before a 13 EMA dip buy signal can be considered valid.
REQUIRE_EMA_STACK_FOR_DIP_BUYS = True

# --- Trend Filtering ---

# Defines a tolerance band (as a percentage) around the 200 EMA. A trade can be taken
# if the price is within this percentage of the 200 EMA, even if it's on the 'wrong' side.
# For example, a value of 0.001 means a 0.1% tolerance.
EMA_BIAS_TOLERANCE_PERCENT = 0.001

# The number of seconds to wait between each main loop cycle.
LOOP_INTERVAL_SECONDS = 60

# The time windows during which the bot is allowed to look for and manage trades.
MORNING_SESSION_START = "09:30" # ET
MORNING_SESSION_END = "11:00"   # ET
AFTERNOON_SESSION_START = "14:00" # ET
AFTERNOON_SESSION_END = "16:00"   # ET

# The minimum volume required on a breakout candle (not currently used).
MIN_VOLUME_THRESHOLD = 10000

# Defines how close the price wick must be to the 13 EMA to confirm a retest confluence.
# This value is in points.
EMA_CONFLUENCE_TOLERANCE_POINTS = {
    'MNQ': 40,
    'MES': 4.5, # Increased from 1.0 to match user example and retest tolerance
}

# Defines how close the price wick must be to the 48 EMA to confirm a retest confluence.
EMA_CONFLUENCE_TOLERANCE_POINTS_48 = {
    'MNQ': 20,
    'MES': 10,
}
