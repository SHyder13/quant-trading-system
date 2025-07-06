import logging
import pandas as pd

class BreakDetector:
    def __init__(self, strategy_config, symbol, logger=None):
        self.strategy_config = strategy_config
        self.symbol = symbol
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Configuration parameters
        self.conviction_candle_body_ratio = self.strategy_config.CONVICTION_CANDLE_BODY_RATIO.get(self.symbol, 0.6)
        self.max_a_plus_extension = self.strategy_config.MAX_A_PLUS_ENTRY_EXTENSION.get(self.symbol, 30.0)
        
        # State variables
        self.previous_bar = None

    def check_for_break(self, latest_bar: pd.Series, levels: dict):
        """
        Checks for a break of a key level. A break is defined as the close price
        moving beyond the level, compared to the previous bar's close.
        Also identifies "A+" setups where a single candle performs a break and retest.
        """
        if latest_bar is None or not levels:
            return None

        # A break can only be confirmed if we have a previous bar to compare against.
        if self.previous_bar is None:
            self.previous_bar = latest_bar
            return None

        close_price = latest_bar['close']
        event = None

        # Check for break of resistance levels (e.g., pdh, pmh)
        for level_name, level_value in levels.items():
            if level_value is None: continue
            if level_name.endswith('h'):  # Identifies resistance levels like 'pdh', 'pmh'
                self.logger.debug(f"Checking break up of {level_name} ({level_value:.2f}) with close {close_price:.2f} (prev close: {self.previous_bar['close']:.2f})")
                if close_price > level_value and self.previous_bar['close'] <= level_value:
                    self.logger.info(f"BREAK UP DETECTED of {level_name} at {level_value:.2f} with close price {close_price:.2f}")
                    event = {'type': 'up', 'level_name': level_name, 'level_value': level_value, 'candle': latest_bar}
                    break

        # Check for break of support levels if no resistance break was found
        if not event:
            for level_name, level_value in levels.items():
                if level_value is None: continue
                if level_name.endswith('l'):  # Identifies support levels like 'pdl', 'pml'
                    self.logger.debug(f"Checking break down of {level_name} ({level_value:.2f}) with close {close_price:.2f} (prev close: {self.previous_bar['close']:.2f})")
                    if close_price < level_value and self.previous_bar['close'] >= level_value:
                        self.logger.info(f"BREAK DOWN DETECTED of {level_name} at {level_value:.2f} with close price {close_price:.2f}")
                        event = {'type': 'down', 'level_name': level_name, 'level_value': level_value, 'candle': latest_bar}
                        break

        # --- A+ Setup & High Conviction Check ---
        if event:
            candle_range = latest_bar['high'] - latest_bar['low']
            candle_body = abs(latest_bar['close'] - latest_bar['open'])
            is_high_conviction = False
            if candle_range > 0 and (candle_body / candle_range) >= self.conviction_candle_body_ratio:
                is_high_conviction = True

            # A+ Setup: A single candle that breaks, retests, and closes with conviction.
            # Filter out setups where the candle has extended too far from the level.
            if event['type'] == 'up':
                if latest_bar['low'] <= event['level_value'] and is_high_conviction:
                    extension = latest_bar['close'] - event['level_value']
                    if extension <= self.max_a_plus_extension:
                        self.logger.info(f"A+ LONG SETUP DETECTED for {self.symbol} at {event['level_value']:.2f} (Extension: {extension:.2f}pts)")
                        event['immediate_entry'] = True
                        event['high_conviction'] = True
                    else:
                        self.logger.info(f"A+ Long setup invalidated. Extension ({extension:.2f}pts) exceeds max ({self.max_a_plus_extension:.2f}pts). Waiting for retest.")

            # For a short, the high must touch/breach the level, but the close must be below it.
            elif event['type'] == 'down':
                if latest_bar['high'] >= event['level_value'] and is_high_conviction:
                    extension = event['level_value'] - latest_bar['close']
                    if extension <= self.max_a_plus_extension:
                        self.logger.info(f"A+ SHORT SETUP DETECTED for {self.symbol} at {event['level_value']:.2f} (Extension: {extension:.2f}pts)")
                        event['immediate_entry'] = True
                        event['high_conviction'] = True
                    else:
                        self.logger.info(f"A+ Short setup invalidated. Extension ({extension:.2f}pts) exceeds max ({self.max_a_plus_extension:.2f}pts). Waiting for retest.")
            
            if not event.get('immediate_entry') and is_high_conviction:
                event['high_conviction'] = True

        self.previous_bar = latest_bar
        return event

    def reset(self):
        """Resets the detector's state for a new trading day."""
        self.logger.info(f"Resetting BreakDetector state for {self.symbol}.")
        self.previous_bar = None
