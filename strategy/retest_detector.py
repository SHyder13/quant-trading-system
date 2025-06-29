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
        Checks for a single-candle retest and rejection.
        A valid retest candle touches the broken level and closes in the direction of the trade.
        EMA confluence is checked but not required for a signal.
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

        # --- 2. 13 EMA Dip Buy/Sell (if enabled) ---
        if self.strategy_config.ALLOW_EMA_DIP_BUYS:
            ema_13 = latest_emas.get('ema_13')
            if ema_13:
                ema_retest_zone_upper = ema_13 + self.ema_confluence_tolerance_13
                ema_retest_zone_lower = ema_13 - self.ema_confluence_tolerance_13
                
                price_on_correct_side = False
                wick_touched_ema = False

                if break_direction == 'up':
                    price_on_correct_side = latest_bar['close'] > broken_level_price
                    wick_touched_ema = latest_bar['low'] <= ema_retest_zone_upper
                elif break_direction == 'down':
                    price_on_correct_side = latest_bar['close'] < broken_level_price
                    wick_touched_ema = latest_bar['high'] >= ema_retest_zone_lower

                if price_on_correct_side and wick_touched_ema and is_rejection_candle:
                    # --- EMA Stack Trend Filter ---
                    if self.strategy_config.REQUIRE_EMA_STACK_FOR_DIP_BUYS:
                        ema_48 = latest_emas.get('ema_48')
                        ema_200 = latest_emas.get('ema_200')
                        if not (ema_48 and ema_200):
                            return None, None, None # Not enough data for the stack

                        is_bullish_stack = latest_bar['close'] > ema_13 > ema_48 > ema_200
                        is_bearish_stack = latest_bar['close'] < ema_13 < ema_48 < ema_200

                        if (break_direction == 'up' and not is_bullish_stack) or \
                           (break_direction == 'down' and not is_bearish_stack):
                            print(f"    - EMA Dip Rejected: Trend stack not aligned.")
                            return None, None, None # Trend filter blocks the trade

                    print(f"    - Retest Type: 13 EMA Dip @ {ema_13:.2f} (Trend Confirmed)")
                    return latest_bar, latest_bar, '13_EMA_DIP'

        return None, None, None

    def reset(self):
        """
        Resets the detector's state. As the detector is now stateless, this method
        is kept for compatibility but has no internal effect.
        """
        pass # No state to reset
