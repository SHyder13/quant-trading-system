import logging

class BreakDetector:
    def __init__(self, strategy_config, symbol, logger=None):
        self.strategy_config = strategy_config
        self.symbol = symbol
        self.logger = logging.getLogger(self.__class__.__name__)
        self.break_confirmation_candles = self.strategy_config.BREAK_CONFIRMATION_CANDLES
        self.conviction_candle_body_ratio = self.strategy_config.CONVICTION_CANDLE_BODY_RATIO.get(self.symbol)
        self.min_breakout_volume = self.strategy_config.MIN_BREAKOUT_VOLUME.get(self.symbol)
        self.candle_closes_since_break = 0
        self.previous_bar = None
        self.break_above_confirmations = 0
        self.break_below_confirmations = 0
        self.last_break_type = None
        self.last_pivot_candle = None
        
        # Fix: Initialize missing attributes to prevent AttributeError
        self.break_level = None
        self.break_direction = None
        self.break_time = None
        self.break_confirmed = False
        self.previous_candle = None

    def get_last_pivot_candle(self):
        """Returns the last identified pivot candle."""
        return self.last_pivot_candle

    def check_for_break(self, latest_bar, levels):
        """
        Checks for a single-candle break of a key level.
        A break is defined as the close price moving beyond the level, and it must
        be a new break (i.e., the previous candle was not already beyond the level).
        """
        if latest_bar is None or not levels:
            return None

        close_price = latest_bar['close']
        event = None

        # A break can only be confirmed if we have a previous bar to compare against.
        if self.previous_bar is not None:
            # Check for break of resistance levels (e.g., pdh, pmh)
            for level_name, level_value in levels.items():
                if level_name.endswith('h'):  # Identifies resistance levels like 'pdh', 'pmh'
                    print(f"Checking for break up of {level_name} at {level_value} with close price {close_price} and previous close {self.previous_bar['close']}", flush=True)
                    if close_price > level_value and self.previous_bar['close'] <= level_value:
                        print(f"*** BREAK UP DETECTED of {level_name} at {level_value} with close price {close_price} ***", flush=True)
                        event = {'type': 'up', 'level_name': level_name, 'level_value': level_value, 'candle': latest_bar}
                        break  # Exit loop once break is found

            # Check for break of support levels if no resistance break was found
            if not event:
                for level_name, level_value in levels.items():
                    if level_name.endswith('l'):  # Identifies support levels like 'pdl', 'pml'
                        print(f"Checking for break down of {level_name} at {level_value} with close price {close_price} and previous close {self.previous_bar['close']}", flush=True)
                        if close_price < level_value and self.previous_bar['close'] >= level_value:
                            print(f"*** BREAK DOWN DETECTED of {level_name} at {level_value} with close price {close_price} ***", flush=True)
                            event = {'type': 'down', 'level_name': level_name, 'level_value': level_value, 'candle': latest_bar}
                            break # Exit loop once break is found

        # --- A+ Setup: Single-Candle Break-Retest-Confirm Pattern ---
        is_high_conviction = False

        # Update previous bar for the next iteration's checks
        self.previous_bar = latest_bar
        
        return event

    def _check_confluence_break(self, latest_bar, levels, previous_emas, session_ema_period):
        if not previous_emas:
            return None

        ema_name = f'ema_{session_ema_period}'
        session_ema = previous_emas.get(ema_name)
        if not session_ema:
            print(f"Warning: {ema_name} not found in EMA data for confluence check.")
            return None

        # Check if the *previous* bar's low/high touched its own session EMA. The color of this "bounce" candle is irrelevant.
        is_touching_ema_for_long = self.previous_bar['low'] <= session_ema + self.ema_confluence_tolerance
        is_touching_ema_for_short = self.previous_bar['high'] >= session_ema - self.ema_confluence_tolerance

        # Check if the *latest* bar is a strong break of a level
        for level_name, level_value in levels.items():
            if level_value is None: continue

            # Bullish scenario: Previous bar touched EMA, current bar is a strong green candle breaking resistance
            if is_touching_ema_for_long and level_name in ['pdh', 'pmh'] and latest_bar['close'] > level_value:
                if latest_bar['close'] > latest_bar['open']: # Check for strength (green candle)
                    return {'type': 'confluence_break_up', 'level': level_value, 'candle': self.previous_bar}

            # Bearish scenario: Previous bar touched EMA, current bar is a strong red candle breaking support
            if is_touching_ema_for_short and level_name in ['pdl', 'pml'] and latest_bar['close'] < level_value:
                if latest_bar['close'] < latest_bar['open']: # Check for strength (red candle)
                    return {'type': 'confluence_break_down', 'level': level_value, 'candle': self.previous_bar}

        return None

    def reset(self):
        """Resets the confirmation state."""
        # Only print reset message if there was something to reset
        if self.break_above_confirmations > 0 or self.break_below_confirmations > 0:
            print("BreakDetector state has been reset.")

        self.break_above_confirmations = 0
        self.break_below_confirmations = 0
        self.last_break_type = None
        self.last_pivot_candle = None
        self.previous_bar = None
