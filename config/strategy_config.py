# strategy_config.py

# --- Break and Retest Strategy Parameters ---

# The symbols the bot is allowed to trade.
TRADABLE_SYMBOLS = ['MNQ', 'MES']

# The number of consecutive candle closes required to confirm a breakout.
BREAK_CONFIRMATION_CANDLES = 1

# Defines how close the price must get to a broken level to be considered a valid retest.
# This value is in points.
RETEST_TOLERANCE_POINTS = {
    'MNQ': 15.0, # Wider tolerance for volatile Nasdaq futures
    'MES': 4.5,  # Tighter tolerance for S&P futures
}

# The minimum volume required on a breakout candle for a signal to be considered valid.
# This is now a dictionary to support different thresholds per symbol.
MIN_BREAKOUT_VOLUME = {
    'MNQ': 100,  # Corresponds to NQ
    'MES': 50,   # Corresponds to ES
}

# The number of minutes to wait for a retest before invalidating the setup.
RETEST_TIMEOUT_MINUTES = 15

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
