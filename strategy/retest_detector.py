class RetestDetector:
    def __init__(self, strategy_config, symbol):
        self.strategy_config = strategy_config
        self.symbol = symbol
        self.tolerance = self.strategy_config.RETEST_TOLERANCE_POINTS.get(self.symbol)
        if self.tolerance is None:
            raise ValueError(f"Tolerances not fully configured for symbol: {self.symbol}")
        self.reset()

    def check_for_retest(self, latest_bar, broken_level_price, break_direction):
        """
        Checks for a single-candle retest and rejection.
        A valid retest candle touches the broken level and closes in the direction of the trade.
        Returns a tuple of (pivot_candle, rejection_candle, confluence_type) on success.
        """
        if broken_level_price is None or latest_bar is None:
            return None, None, None

        # --- 1. Standard Retest of Static Level ---
        retest_zone_upper = broken_level_price + self.tolerance
        retest_zone_lower = broken_level_price - self.tolerance
        candle_midpoint = (latest_bar['high'] + latest_bar['low']) / 2

        wick_touched_static_level = False
        is_rejection_candle = False

        if break_direction == 'up':
            # Price broke ABOVE resistance – acceptable retest if the LOW of rejection candle touches level within tolerance band
            wick_touched_static_level = (latest_bar['low'] <= retest_zone_upper) and (latest_bar['low'] >= retest_zone_lower)
            is_rejection_candle = latest_bar['close'] >= candle_midpoint
        elif break_direction == 'down':
            # Price broke BELOW support – acceptable retest if the HIGH of rejection candle touches level within tolerance band
            wick_touched_static_level = (latest_bar['high'] >= retest_zone_lower) and (latest_bar['high'] <= retest_zone_upper)
            is_rejection_candle = latest_bar['close'] <= candle_midpoint

        if wick_touched_static_level and is_rejection_candle:
            print(f"    - Retest Type: Static Level @ {broken_level_price:.2f}")
            return latest_bar, latest_bar, 'STATIC'

        return None, None, None

    def reset(self):
        """
        Resets the detector's state. As the detector is now stateless, this method
        is kept for compatibility but has no internal effect.
        """
        pass # No state to reset
