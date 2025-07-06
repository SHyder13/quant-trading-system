import logging
import pandas as pd
from typing import Tuple

import config.strategy_config as strategy_config

class PatternValidator:
    """
    Validates a trading signal based on a set of rules for pattern quality,
    including volume, candle conviction, and confirmation.
    """
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.min_volume_map = strategy_config.MIN_BREAKOUT_VOLUME
        self.conviction_ratio_map = strategy_config.CONVICTION_CANDLE_BODY_RATIO
        self.min_distance_from_level = strategy_config.MIN_DISTANCE_FROM_LEVEL

    def validate_signal(self, signal_direction: str, context: dict) -> Tuple[bool, str]:
        """
        Validates the quality of a generated signal based on a series of checks.

        Args:
            signal_direction: The direction of the trade ('BUY' or 'SELL').
            context: A dictionary containing the candles and data for validation.

        Returns:
            A tuple: (is_valid: bool, reason: str).
        """
        # --- 1. Unpack Context and Basic Checks ---
        symbol = context.get('symbol')
        breakout_candle = context.get('breakout_candle')
        confirmation_candle = context.get('latest_bar')

        if not all([symbol, breakout_candle is not None, confirmation_candle is not None]):
            return False, "Missing essential context for validation."

        # --- 2. Volume Check on Breakout Candle ---
        min_volume = self.min_volume_map.get(symbol, 0)
        if breakout_candle['volume'] < min_volume:
            reason = f"Validation failed: Breakout volume ({breakout_candle['volume']}) is below minimum ({min_volume})."
            self.logger.warning(reason)
            return False, reason


                # --- 3. Confluence Check ---
        min_dist = self.min_distance_from_level.get(symbol, 0)
        is_conflicting, conflict_reason = self._check_level_confluence(
            signal_direction, confirmation_candle, context.get('levels', {}), min_dist
        )
        if is_conflicting:
            self.logger.warning(f"Validation failed: {conflict_reason}")
            return False, conflict_reason

        # --- 4. Confirmation Candle Check ---
        if signal_direction == 'BUY':
            if confirmation_candle['close'] <= confirmation_candle['open']:
                reason = f"Confirmation failed: Entry candle was not bullish."
                self.logger.warning(reason)
                return False, reason
        elif signal_direction == 'SELL':
            if confirmation_candle['close'] >= confirmation_candle['open']:
                reason = f"Confirmation failed: Entry candle was not bearish."
                self.logger.warning(reason)
                return False, reason

        self.logger.info(f"Signal for {symbol} validation successful.")
        return True, "Validation successful."

    def _check_level_confluence(self, signal_direction: str, entry_candle: dict, levels: dict, min_dist: float) -> Tuple[bool, str]:
        """
        Checks if the trade entry is too close to other significant levels.

        Args:
            signal_direction: The direction of the trade ('BUY' or 'SELL').
            entry_candle: The candle on which the trade would be entered.
            levels: A dictionary of other key levels (e.g., PDH, PDL).
            min_dist: The minimum required distance from other levels.

        Returns:
            A tuple: (is_conflicting: bool, reason: str).
        """
        entry_price = entry_candle['close']

        for level_name, level_value in levels.items():
            if level_value is None: 
                continue

            distance = abs(entry_price - level_value)

            if signal_direction == 'BUY':
                # For a long, check for resistance levels above that are too close
                if entry_price < level_value and distance < min_dist:
                    return True, f"Entry price {entry_price} is too close to resistance level {level_name} at {level_value}."
            
            elif signal_direction == 'SELL':
                # For a short, check for support levels below that are too close
                if entry_price > level_value and distance < min_dist:
                    return True, f"Entry price {entry_price} is too close to support level {level_name} at {level_value}."

        return False, ""
