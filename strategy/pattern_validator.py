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
