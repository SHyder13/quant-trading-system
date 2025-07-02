import config.strategy_config as strategy_config

class PatternValidator:
    def __init__(self):
        self.min_volume_map = strategy_config.MIN_BREAKOUT_VOLUME
        self.conviction_ratio_map = strategy_config.CONVICTION_CANDLE_BODY_RATIO
        self.ema_tolerance = strategy_config.EMA_BIAS_TOLERANCE_PERCENT

    def validate_signal(self, signal, context):
        """
        Validates the quality of a generated signal based on market bias and a simplified confirmation rule.
        Returns a tuple: (is_valid: bool, reason: str)
        """
        # Unpack context
        symbol = context.get('symbol')
        latest_bar = context.get('latest_bar')
        latest_emas = context.get('latest_emas')
        level_broken = context.get('level_broken')

        if symbol is None or latest_bar is None or latest_emas is None or level_broken is None:
            return False, "Missing context for pattern validation."

        signal_direction = signal

        # 1. 200 EMA Bias Check
        current_price = latest_bar['close']
        ema_200 = latest_emas.get('ema_200')
        if not ema_200:
            return False, f"200 EMA not available for {symbol}."

        tolerance_amount = ema_200 * self.ema_tolerance
        upper_band = ema_200 + tolerance_amount
        lower_band = ema_200 - tolerance_amount

        if signal_direction == 'BUY' and current_price < lower_band:
            reason = f"BUY signal below 200 EMA tolerance band ({current_price:.2f} < {lower_band:.2f}). Bias is BEARISH."
            return False, reason
        
        if signal_direction == 'SELL' and current_price > upper_band:
            reason = f"SELL signal above 200 EMA tolerance band ({current_price:.2f} > {upper_band:.2f}). Bias is BULLISH."
            return False, reason

        # 2. Confirmation Check (New Simplified Rule)
        entry_candle = latest_bar
        if signal_direction == 'BUY':
            if entry_candle['close'] <= entry_candle['open']:
                return False, f"Confirmation failed: Entry candle was not bullish (Close: {entry_candle['close']:.2f} <= Open: {entry_candle['open']:.2f})."

        elif signal_direction == 'SELL':
            if entry_candle['close'] >= entry_candle['open']:
                return False, f"Confirmation failed: Entry candle was not bearish (Close: {entry_candle['close']:.2f} >= Open: {entry_candle['open']:.2f})."

        return True, "Validation successful."
