class BreakDetector:
    def __init__(self, strategy_config, symbol):
        self.strategy_config = strategy_config
        self.symbol = symbol
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
        """Checks for a break, prioritizing an EMA-supported confluence break."""
        if latest_bar is None or self.previous_bar is None:
            self.previous_bar = latest_bar
            self.previous_emas = latest_emas
            return None

        # --- Priority 1: Check for EMA-Supported Confluence Break ---
        confluence_break_event = self._check_confluence_break(latest_bar, levels, self.previous_emas, session_ema_period)
        if confluence_break_event:
            print(f"*** CONFLUENCE BREAK DETECTED: {confluence_break_event['type']} ***")
            self.reset()
            self.last_pivot_candle = confluence_break_event['candle']
            return confluence_break_event

        # --- Priority 2: Check for standard break confirmation ---
        close_price = latest_bar['close']
        for level_name, level_value in levels.items():
            if level_value is None:
                continue

            # Check for break above resistance levels (PDH, PMH)
            if level_name in ['pdh', 'pmh'] and close_price > level_value:
                if self.last_break_type != 'up':  # Reset only when break direction changes
                    self.reset()
                self.break_above_confirmations += 1
                self.last_break_type = 'up'
                if self.break_above_confirmations >= self.confirmation_candles:
                    ema_200 = latest_emas.get('ema_200')
                    if ema_200 and close_price < ema_200:
                        print(f"Break above {level_value:.2f} ignored. Price {close_price:.2f} is below 200 EMA {ema_200:.2f}.")
                        return None
                    print(f"*** BREAK CONFIRMED: resistance_break_up at {close_price:.2f} (Level: {level_value:.2f}) ***")
                    self.last_pivot_candle = latest_bar
                    return {'type': 'resistance_break_up', 'level': level_value, 'candle': latest_bar}

            # Check for break below support levels (PDL, PML)
            elif level_name in ['pdl', 'pml'] and close_price < level_value:
                if self.last_break_type != 'down':  # Reset only when break direction changes
                    self.reset()
                self.break_below_confirmations += 1
                self.last_break_type = 'down'
                if self.break_below_confirmations >= self.confirmation_candles:
                    ema_200 = latest_emas.get('ema_200')
                    if ema_200 and close_price > ema_200:
                        print(f"Break below {level_value:.2f} ignored. Price {close_price:.2f} is above 200 EMA {ema_200:.2f}.")
                        return None
                    print(f"*** BREAK CONFIRMED: support_break_down at {close_price:.2f} (Level: {level_value:.2f}) ***")
                    self.last_pivot_candle = latest_bar
                    return {'type': 'support_break_down', 'level': level_value, 'candle': latest_bar}

        # If price is not breaking any level, check if it's within the main range, which implies a reset.
        resistance_levels = [lvl for lvl in [levels.get('pdh'), levels.get('pmh')] if lvl is not None]
        support_levels = [lvl for lvl in [levels.get('pdl'), levels.get('pml')] if lvl is not None]
        if resistance_levels and support_levels:
            if close_price < max(resistance_levels) and close_price > min(support_levels):
                self.reset()

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
