class RetestDetector:
    def __init__(self, strategy_config, symbol):
        self.strategy_config = strategy_config
        self.symbol = symbol
        self.tolerance = self.strategy_config.RETEST_TOLERANCE_POINTS.get(self.symbol)
        self.ema_confluence_tolerance_13 = self.strategy_config.EMA_CONFLUENCE_TOLERANCE_POINTS.get(self.symbol)
        self.ema_confluence_tolerance_48 = self.strategy_config.EMA_CONFLUENCE_TOLERANCE_POINTS_48.get(self.symbol)
        if self.tolerance is None or self.ema_confluence_tolerance_13 is None or self.ema_confluence_tolerance_48 is None:
            raise ValueError(f"Tolerances not fully configured for symbol: {self.symbol}")
        # The detector is now stateless, so reset does nothing but is kept for compatibility.
        self.reset()

    def check_for_retest(self, latest_bar, broken_level_price, break_direction, latest_emas):
        """
        Checks for a single-candle retest and rejection.
        A valid retest candle touches the broken level and closes in the direction of the trade.
        EMA confluence is checked but not required for a signal.
        Returns a tuple of (pivot_candle, rejection_candle, confluence_type) on success.
        """
        if broken_level_price is None or latest_bar is None:
            return None, None, None

        retest_zone_upper = broken_level_price + self.tolerance
        retest_zone_lower = broken_level_price - self.tolerance

        wick_touched_zone = False
        is_rejection_candle = False

        # A more robust definition of a rejection candle based on its closing price within its range.
        candle_midpoint = (latest_bar['high'] + latest_bar['low']) / 2

        if break_direction == 'up':
            # For a buy, the wick must touch the support level.
            wick_touched_zone = latest_bar['low'] <= retest_zone_upper
            # The candle must close in the upper half of its range, showing rejection of lower prices.
            is_rejection_candle = latest_bar['close'] >= candle_midpoint
        elif break_direction == 'down':
            # For a sell, the wick must touch the resistance level.
            wick_touched_zone = latest_bar['high'] >= retest_zone_lower
            # The candle must close in the lower half of its range, showing rejection of higher prices.
            is_rejection_candle = latest_bar['close'] <= candle_midpoint

        if wick_touched_zone and is_rejection_candle:
            # This candle is our signal. It acts as both pivot and rejection.
            # Now, check for confluence as a bonus.
            ema_13 = latest_emas.get('ema_13')
            ema_48 = latest_emas.get('ema_48')
            confluence_type = None

            if break_direction == 'up' and ema_13 and abs(latest_bar['low'] - ema_13) <= self.ema_confluence_tolerance_13:
                confluence_type = '13_EMA'
            elif break_direction == 'up' and ema_48 and abs(latest_bar['low'] - ema_48) <= self.ema_confluence_tolerance_48:
                confluence_type = '48_EMA'
            elif break_direction == 'down' and ema_13 and abs(latest_bar['high'] - ema_13) <= self.ema_confluence_tolerance_13:
                confluence_type = '13_EMA'
            elif break_direction == 'down' and ema_48 and abs(latest_bar['high'] - ema_48) <= self.ema_confluence_tolerance_48:
                confluence_type = '48_EMA'

            # The stop loss will be based on this single candle.
            # We return it as both pivot and rejection for compatibility with the backtester.
            return latest_bar, latest_bar, confluence_type

        return None, None, None

    def reset(self):
        """
        Resets the detector's state. As the detector is now stateless, this method
        is kept for compatibility but has no internal effect.
        """
        pass # No state to reset
