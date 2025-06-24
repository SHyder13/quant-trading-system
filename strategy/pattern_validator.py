import config.strategy_config as strategy_config

class PatternValidator:
    def __init__(self):
        self.min_volume_map = strategy_config.MIN_BREAKOUT_VOLUME

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

        if signal_direction == 'BUY' and current_price < ema_200:
            print(f"Validation FAILED ({symbol}): BUY signal is below 200 EMA ({current_price:.2f} < {ema_200:.2f}). Bias is BEARISH.")
            return False
        
        if signal_direction == 'SELL' and current_price > ema_200:
            print(f"Validation FAILED ({symbol}): SELL signal is above 200 EMA ({current_price:.2f} > {ema_200:.2f}). Bias is BULLISH.")
            return False
        
        print(f"- Validation PASSED ({symbol}): Signal direction ({signal_direction}) aligns with 200 EMA bias.")

        # 2. Volume Check
        min_volume = self.min_volume_map.get(symbol)
        if breakout_candle['volume'] < min_volume:
            print(f"Validation FAILED ({symbol}): Breakout volume ({breakout_candle['volume']}) is below minimum ({min_volume}).")
            return False
        print(f"- Validation PASSED ({symbol}): Breakout volume is sufficient.")
        
        # 3. Candlestick Pattern Check: Validate rejection candle shows momentum.
        rej_open = rejection_candle['open']
        rej_close = rejection_candle['close']

        if signal_direction == 'BUY':
            if rej_close <= rej_open:
                print(f"Validation FAILED ({symbol}): Rejection candle did not close bullish.")
                return False

        elif signal_direction == 'SELL':
            if rej_close >= rej_open:
                print(f"Validation FAILED ({symbol}): Rejection candle did not close bearish.")
                return False

        print(f"- Validation PASSED ({symbol}): Rejection candle shows momentum.")
        return True
