import config.strategy_config as strategy_config

class PatternValidator:
    def __init__(self):
        self.min_volume_map = strategy_config.MIN_BREAKOUT_VOLUME
        self.conviction_ratio_map = strategy_config.CONVICTION_CANDLE_BODY_RATIO

    def validate_signal(self, signal, context):
        """
        Validates the quality of a generated signal based on market bias and a simplified confirmation rule.
        Returns a tuple: (is_valid: bool, reason: str)
        """
        # Unpack context
        symbol = context.get('symbol')
        latest_bar = context.get('latest_bar')
        level_broken = context.get('level_broken')

        if symbol is None or latest_bar is None or level_broken is None:
            return False, "Missing context for pattern validation."

        signal_direction = signal

        # Confirmation Check (Simplified Rule)
        entry_candle = latest_bar
        if signal_direction == 'BUY':
            if entry_candle['close'] <= entry_candle['open']:
                return False, f"Confirmation failed: Entry candle was not bullish (Close: {entry_candle['close']:.2f} <= Open: {entry_candle['open']:.2f})."

        elif signal_direction == 'SELL':
            if entry_candle['close'] >= entry_candle['open']:
                return False, f"Confirmation failed: Entry candle was not bearish (Close: {entry_candle['close']:.2f} >= Open: {entry_candle['open']:.2f})."

        return True, "Validation successful."
