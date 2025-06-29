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
        
        # 3. Candlestick Pattern Check: Validate for high-quality rejection patterns (Hammer/Shooting Star).
        rej_open = rejection_candle['open']
        rej_close = rejection_candle['close']
        rej_high = rejection_candle['high']
        rej_low = rejection_candle['low']

        body_size = abs(rej_open - rej_close)
        # Handle Doji case where body is zero to avoid division by zero errors.
        if body_size < 0.01: 
            body_size = 0.01

        upper_wick = rej_high - max(rej_open, rej_close)
        lower_wick = min(rej_open, rej_close) - rej_low

        if signal_direction == 'BUY':
            # Must be a bullish Hammer: long lower wick, small upper wick, bullish close.
            is_valid_hammer = (lower_wick >= 2 * body_size) and (upper_wick < body_size) and (rej_close > rej_open)
            if not is_valid_hammer:
                print(f"Validation FAILED ({symbol}): Rejection candle is not a valid bullish Hammer pattern.")
                return False

        elif signal_direction == 'SELL':
            # Must be a bearish Shooting Star: long upper wick, small lower wick, bearish close.
            is_valid_shooting_star = (upper_wick >= 2 * body_size) and (lower_wick < body_size) and (rej_close < rej_open)
            if not is_valid_shooting_star:
                print(f"Validation FAILED ({symbol}): Rejection candle is not a valid bearish Shooting Star pattern.")
                return False

        print(f"- Validation PASSED ({symbol}): Rejection candle is a high-quality pattern.")
        return True
