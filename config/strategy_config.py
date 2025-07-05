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
    'MNQ': 500, # Increased for higher conviction breakouts
    'MES': 250,  # Increased for higher conviction breakouts
}

# Defines the minimum required ratio of the candle's body to its total range (high-low)
# for it to be considered a 'Conviction Candle'. A higher value means a more decisive candle.
CONVICTION_CANDLE_BODY_RATIO = {
    'MNQ': 0.7,  # Requires a strong 70% body
    'MES': 0.6,  # Slightly more lenient for MES
}

# The number of minutes to wait for a retest before invalidating the setup.
RETEST_TIMEOUT_MINUTES = 60

# The number of seconds to wait between each main loop cycle.
LOOP_INTERVAL_SECONDS = 60

# The time windows during which the bot is allowed to look for and manage trades.
MORNING_SESSION_START = "09:30" # ET
MORNING_SESSION_END = "11:00"   # ET
# Afternoon session disabled – set to None
AFTERNOON_SESSION_START = None # ET
AFTERNOON_SESSION_END = None   # ET

# The minimum volume required on a breakout candle (not currently used).
MIN_VOLUME_THRESHOLD = 10000
