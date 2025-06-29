import config.strategy_config as strategy_config

class PatternValidator:
    def __init__(self):
        self.min_volume_map = strategy_config.MIN_BREAKOUT_VOLUME
        self.conviction_ratio_map = strategy_config.CONVICTION_CANDLE_BODY_RATIO
        self.ema_tolerance = strategy_config.EMA_BIAS_TOLERANCE_PERCENT

    def validate_signal(self, signal, context):
        """
        Validates the quality of a generated signal based on market bias, volume, and candlestick patterns.
        """
        # Unpack context
        breakout_candle = context.get('breakout_candle')
        rejection_candle = context.get('rejection_candle')
        symbol = context.get('symbol')
        latest_bar = context.get('latest_bar')
        latest_emas = context.get('latest_emas')

        if breakout_candle is None or rejection_candle is None or symbol is None or latest_bar is None or latest_emas is None:
            print("Validation FAILED: Missing context for pattern validation.")
            return False

        signal_direction = signal

        # 1. 200 EMA Bias Check
        current_price = latest_bar['close']
        ema_200 = latest_emas.get('ema_200')
        if not ema_200:
            print(f"Validation FAILED ({symbol}): 200 EMA not available.")
            return False

        # Calculate tolerance band
        tolerance_amount = ema_200 * self.ema_tolerance
        upper_band = ema_200 + tolerance_amount
        lower_band = ema_200 - tolerance_amount

        if signal_direction == 'BUY' and current_price < lower_band:
            print(f"Validation FAILED ({symbol}): BUY signal is below 200 EMA tolerance band ({current_price:.2f} < {lower_band:.2f}). Bias is BEARISH.")
            return False
        
        if signal_direction == 'SELL' and current_price > upper_band:
            print(f"Validation FAILED ({symbol}): SELL signal is above 200 EMA tolerance band ({current_price:.2f} > {upper_band:.2f}). Bias is BULLISH.")
            return False
        
        print(f"- Validation PASSED ({symbol}): Signal direction ({signal_direction}) aligns with 200 EMA bias.")

        # 2. Volume Check
        min_volume = self.min_volume_map.get(symbol)
        if breakout_candle['volume'] < min_volume:
            print(f"Validation FAILED ({symbol}): Breakout volume ({breakout_candle['volume']}) is below minimum ({min_volume}).")
            return False
        print(f"- Validation PASSED ({symbol}): Breakout volume is sufficient.")
        
        # 3. Candlestick Pattern Check
        # The candle being checked is the one that triggers the trade (the confirmation candle)
        entry_candle = latest_bar

        # If the signal is already confirmed, we can relax the pattern rules.
        # The primary check is just that the entry candle moves in the right direction.
        if signal_direction == 'BUY':
            if entry_candle['close'] <= entry_candle['open']:
                print(f"Validation FAILED ({symbol}): Post-confirmation entry candle was not bullish.")
                return False
            print(f"- Validation PASSED ({symbol}): Post-confirmation entry candle is bullish.")

        elif signal_direction == 'SELL':
            if entry_candle['close'] >= entry_candle['open']:
                print(f"Validation FAILED ({symbol}): Post-confirmation entry candle was not bearish.")
                return False
            print(f"- Validation PASSED ({symbol}): Post-confirmation entry candle is bearish.")

        return True
