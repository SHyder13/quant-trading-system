class StopLossManager:
    def __init__(self, risk_config):
        self.risk_config = risk_config

    def calculate_stop_from_candle(self, signal_direction, pivot_candle, symbol):
        """
        Calculates the stop-loss price based on the high/low of the retest pivot candle.
        The buffer used is symbol-specific.
        """
        if pivot_candle is None or symbol is None:
            print("ERROR: Cannot calculate stop loss without a pivot candle and symbol.")
            return None

        buffer = self.risk_config.STOP_LOSS_BUFFER_POINTS.get(symbol)
        if buffer is None:
            print(f"ERROR: No stop-loss buffer configured for symbol '{symbol}'.")
            return None
        stop_price = None

        if signal_direction == 'BUY':
            # For a long trade, stop is placed just below the low of the pivot candle.
            pivot_low = pivot_candle['low']
            stop_price = pivot_low - buffer
            print(f"Setting BUY stop loss at {stop_price:.2f} (Pivot Low: {pivot_low:.2f}, Buffer: {buffer:.2f})")
        elif signal_direction == 'SELL':
            # For a short trade, stop is placed just above the high of the pivot candle.
            pivot_high = pivot_candle['high']
            stop_price = pivot_high + buffer
            print(f"Setting SELL stop loss at {stop_price:.2f} (Pivot High: {pivot_high:.2f}, Buffer: {buffer:.2f})")
        
        return stop_price

    def set_initial_stop(self, signal_direction, broken_level_price):
        """
        DEPRECATED: Calculates the initial stop-loss price based on the broken level.
        Prefer calculate_stop_from_candle for dynamic placement.
        """
        if not broken_level_price:
            print("ERROR: Cannot set stop loss without a broken_level_price.")
            return None

        buffer = self.risk_config.LEVEL_TOLERANCE_POINTS * 2

        stop_price = None
        if signal_direction == 'BUY':
            stop_price = broken_level_price - buffer
            print(f"Setting initial BUY stop loss at {stop_price:.2f} (Level: {broken_level_price:.2f}, Buffer: {buffer:.2f})")
        elif signal_direction == 'SELL':
            stop_price = broken_level_price + buffer
            print(f"Setting initial SELL stop loss at {stop_price:.2f} (Level: {broken_level_price:.2f}, Buffer: {buffer:.2f})")
        
        return stop_price

    def trail_stop(self, current_price, stop_price, signal_direction):
        print("Trailing stop loss...")
        # Add trailing stop logic here
        return stop_price
