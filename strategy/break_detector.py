class BreakDetector:
    def __init__(self, strategy_config, symbol, logger=None):
        self.strategy_config = strategy_config
        self.symbol = symbol
        self.logger = logger
        self.confirmation_candles = strategy_config.BREAK_CONFIRMATION_CANDLES
        self.ema_confluence_tolerance = self.strategy_config.EMA_CONFLUENCE_TOLERANCE_POINTS.get(self.symbol)
        if self.ema_confluence_tolerance is None:
            raise ValueError(f"EMA confluence tolerance not configured for symbol: {self.symbol}")

        # State tracking
        self.break_above_confirmations = 0
        self.break_below_confirmations = 0
        self.last_break_type = None
        self.previous_bar = None
        self.previous_emas = None
        self.last_pivot_candle = None

    def get_last_pivot_candle(self):
        """Returns the last identified pivot candle."""
        return self.last_pivot_candle

    def check_for_break(self, latest_bar, levels, latest_emas, session_ema_period=13):
        """Checks for a break of a key level with consecutive candle confirmation."""
        if latest_bar is None:
            return None

        close_price = latest_bar['close']
        
        # Define the trading range by finding the highest support and lowest resistance
        support_levels = {k: v for k, v in levels.items() if k in ['pdl', 'pml'] and v is not None}
        resistance_levels = {k: v for k, v in levels.items() if k in ['pdh', 'pmh'] and v is not None}
        
        highest_support = max(support_levels.values()) if support_levels else float('-inf')
        lowest_resistance = min(resistance_levels.values()) if resistance_levels else float('inf')

        if self.logger:
            self.logger.info(f"[{self.symbol}] Break Check: Close={close_price:.2f}, Range=[{highest_support:.2f}, {lowest_resistance:.2f}], Confirmations(Up/Down): {self.break_above_confirmations}/{self.break_below_confirmations}")

        # Determine the current bar's position relative to the range
        is_breaking_above = close_price > lowest_resistance and lowest_resistance != float('inf')
        is_breaking_below = close_price < highest_support and highest_support != float('-inf')

        # Update confirmation counters based on the bar's position
        if is_breaking_above:
            if self.last_break_type != 'up':
                self.reset()
            self.last_break_type = 'up'
            self.break_above_confirmations += 1
            if self.logger:
                self.logger.info(f"[{self.symbol}] Breaking ABOVE. Confirmations: {self.break_above_confirmations}")
        elif is_breaking_below:
            if self.last_break_type != 'down':
                self.reset()
            self.last_break_type = 'down'
            self.break_below_confirmations += 1
            if self.logger:
                self.logger.info(f"[{self.symbol}] Breaking BELOW. Confirmations: {self.break_below_confirmations}")
        else:
            if self.break_above_confirmations > 0 or self.break_below_confirmations > 0:
                if self.logger:
                    self.logger.info(f"[{self.symbol}] Price back in range. Resetting confirmations.")
                self.reset()

        # Check if a breakout is confirmed and return the event
        ema_200 = latest_emas.get('ema_200')
        if self.break_above_confirmations >= self.confirmation_candles and ema_200 and close_price > ema_200:
            broken_level_name = min(resistance_levels, key=resistance_levels.get)
            self.logger.info(f"[{self.symbol}] Breakout UP confirmed above {broken_level_name} at {resistance_levels[broken_level_name]}")
            event = {'type': 'up', 'level_name': broken_level_name, 'level_value': resistance_levels[broken_level_name], 'candle': latest_bar}
            self.reset() # Reset after confirmation
            return event

        if self.break_below_confirmations >= self.confirmation_candles and ema_200 and close_price < ema_200:
            broken_level_name = max(support_levels, key=support_levels.get)
            self.logger.info(f"[{self.symbol}] Breakout DOWN confirmed below {broken_level_name} at {support_levels[broken_level_name]}")
            event = {'type': 'down', 'level_name': broken_level_name, 'level_value': support_levels[broken_level_name], 'candle': latest_bar}
            self.reset() # Reset after confirmation
            return event

        self.previous_bar = latest_bar
        self.previous_emas = latest_emas
        return None

    def _check_confluence_break(self, latest_bar, levels, previous_emas, session_ema_period):
        """Checks for a break that occurs immediately after a bounce from the session-specific EMA."""
        if not previous_emas:
            return None

        ema_name = f'ema_{session_ema_period}'
        session_ema = previous_emas.get(ema_name)
        if not session_ema:
            print(f"Warning: {ema_name} not found in EMA data for confluence check.")
            return None

        # Check if the *previous* bar's low/high touched its own session EMA. The color of this "bounce" candle is irrelevant.
        is_touching_ema_for_long = self.previous_bar['low'] <= session_ema + self.ema_confluence_tolerance
        is_touching_ema_for_short = self.previous_bar['high'] >= session_ema - self.ema_confluence_tolerance

        # Check if the *latest* bar is a strong break of a level
        for level_name, level_value in levels.items():
            if level_value is None: continue

            # Bullish scenario: Previous bar touched EMA, current bar is a strong green candle breaking resistance
            if is_touching_ema_for_long and level_name in ['pdh', 'pmh'] and latest_bar['close'] > level_value:
                if latest_bar['close'] > latest_bar['open']: # Check for strength (green candle)
                    return {'type': 'confluence_break_up', 'level': level_value, 'candle': self.previous_bar}

            # Bearish scenario: Previous bar touched EMA, current bar is a strong red candle breaking support
            if is_touching_ema_for_short and level_name in ['pdl', 'pml'] and latest_bar['close'] < level_value:
                if latest_bar['close'] < latest_bar['open']: # Check for strength (red candle)
                    return {'type': 'confluence_break_down', 'level': level_value, 'candle': self.previous_bar}

        return None

    def reset(self):
        """Resets the confirmation state."""
        # Only print reset message if there was something to reset
        if self.break_above_confirmations > 0 or self.break_below_confirmations > 0:
            print("BreakDetector state has been reset.")

        self.break_above_confirmations = 0
        self.break_below_confirmations = 0
        self.last_break_type = None
        self.last_pivot_candle = None
        self.previous_bar = None
