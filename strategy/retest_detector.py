class RetestDetector:
    def __init__(self, strategy_config, symbol):
        self.strategy_config = strategy_config
        self.symbol = symbol
        self.tolerance = self.strategy_config.RETEST_TOLERANCE_POINTS.get(self.symbol)
        self.ema_confluence_tolerance_13 = self.strategy_config.EMA_CONFLUENCE_TOLERANCE_POINTS.get(self.symbol)
        self.ema_confluence_tolerance_48 = self.strategy_config.EMA_CONFLUENCE_TOLERANCE_POINTS_48.get(self.symbol)
        if self.tolerance is None or self.ema_confluence_tolerance_13 is None or self.ema_confluence_tolerance_48 is None:
            raise ValueError(f"Tolerances not fully configured for symbol: {self.symbol}")
        self.reset()

    def check_for_retest(self, latest_bar, broken_level_price, break_direction, latest_emas):
        """
        Checks for a confirmed retest using a two-stage process.
        Returns a tuple of (pivot_candle, rejection_candle, confluence_type) on success, otherwise None.
        """
        if broken_level_price is None or latest_bar is None:
            return None, None, None

        # Stage 1: Wait for a candle to touch the broken level with EMA confluence.
        if self.state == 'AWAITING_TOUCH':
            ema_13 = latest_emas.get('ema_13')
            ema_48 = latest_emas.get('ema_48')
            if not ema_13 or not ema_48:
                return None, None, None # Not enough data for EMAs yet

            # Check for touch of the key level
            is_touching_level = False
            if break_direction == 'up' and latest_bar['low'] <= broken_level_price + self.tolerance:
                is_touching_level = True
            elif break_direction == 'down' and latest_bar['high'] >= broken_level_price - self.tolerance:
                is_touching_level = True

            if not is_touching_level:
                return None, None, None

            # Check for confluence with either the 13 or 48 EMA
            is_near_ema_13 = abs(latest_bar['low'] - ema_13) <= self.ema_confluence_tolerance_13 or \
                             abs(latest_bar['high'] - ema_13) <= self.ema_confluence_tolerance_13
            
            is_near_ema_48 = abs(latest_bar['low'] - ema_48) <= self.ema_confluence_tolerance_48 or \
                             abs(latest_bar['high'] - ema_48) <= self.ema_confluence_tolerance_48

            confluence_type = None
            if is_near_ema_13:
                confluence_type = '13_EMA'
            elif is_near_ema_48:
                confluence_type = '48_EMA'

            if confluence_type:
                print(f"RetestDetector: Pivot candle detected with {confluence_type} confluence. Awaiting rejection.")
                self.pivot_candle = latest_bar
                self.confluence_type = confluence_type
                self.state = 'AWAITING_REJECTION'
            
            return None, None, None

        # Stage 2: Wait for the next candle to confirm rejection.
        if self.state == 'AWAITING_REJECTION':
            rejection_confirmed = False
            current_price = latest_bar['close']

            if break_direction == 'up' and current_price > broken_level_price:
                rejection_confirmed = True
            elif break_direction == 'down' and current_price < broken_level_price:
                rejection_confirmed = True

            if rejection_confirmed:
                print(f"*** RETEST CONFIRMED by candle closing at {current_price:.2f} ***")
                confirmed_pivot_candle = self.pivot_candle
                rejection_candle = latest_bar
                confirmed_confluence = self.confluence_type
                self.reset()
                return confirmed_pivot_candle, rejection_candle, confirmed_confluence

        return None, None, None

    def reset(self):
        """Resets the retest detector's state machine."""
        self.state = 'AWAITING_TOUCH'
        self.pivot_candle = None
        self.confluence_type = None
