import logging
import pandas as pd
from typing import Tuple, Optional

class RetestDetector:
    """
    Detects a retest of a previously broken price level.
    This detector is stateless and evaluates each candle independently.
    """
    def __init__(self, strategy_config: dict, symbol: str, logger: Optional[logging.Logger] = None):
        self.strategy_config = strategy_config
        self.symbol = symbol
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Get the tolerance for the retest from the config
        self.tolerance = self.strategy_config.RETEST_TOLERANCE_POINTS.get(self.symbol)
        if self.tolerance is None:
            self.logger.error(f"Retest tolerance not configured for symbol: {self.symbol}")
            raise ValueError(f"Tolerances not fully configured for symbol: {self.symbol}")

    def check_for_retest(self, latest_bar: pd.Series, broken_level_price: float, break_direction: str) -> Tuple[Optional[pd.Series], Optional[pd.Series], Optional[str]]:
        """
        Checks if the latest bar constitutes a retest of the broken level.

        A retest is defined as a candle's wick touching the broken level within a 
        defined tolerance. The same candle is returned as both the pivot and rejection
        candle, as it represents the turning point.

        Args:
            latest_bar: The most recent market data candle.
            broken_level_price: The price of the level that was broken.
            break_direction: The direction of the initial break ('up' or 'down').

        Returns:
            A tuple containing (pivot_candle, rejection_candle, confluence_type).
            Returns (None, None, None) if no retest is detected.
        """
        if broken_level_price is None or latest_bar is None:
            return None, None, None

        retest_zone_upper = broken_level_price + self.tolerance
        retest_zone_lower = broken_level_price - self.tolerance
        is_retest = False

        if break_direction == 'up':
            # After a break up, a retest happens if the candle's low touches the old resistance.
            if latest_bar['low'] <= retest_zone_upper and latest_bar['high'] > broken_level_price:
                is_retest = True

        elif break_direction == 'down':
            # After a break down, a retest happens if the candle's high touches the old support.
            if latest_bar['high'] >= retest_zone_lower and latest_bar['low'] < broken_level_price:
                is_retest = True

        if is_retest:
            self.logger.info(f"Retest of level {broken_level_price:.2f} detected for {self.symbol}.")
            # The retest candle itself is considered the pivot for stop-loss and rejection signal.
            return latest_bar, latest_bar, 'STATIC'

        return None, None, None

    def reset(self):
        """
        Resets the detector's state. Kept for API compatibility.
        """
        # This detector is stateless, so there's nothing to reset.
        pass
