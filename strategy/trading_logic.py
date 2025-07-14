from loguru import logger

class TradingLogic:
    """
    Encapsulates the core trading strategy logic and state management.

    This class implements a streamlined hybrid trading model:
    1.  It checks for high-momentum "A+" setups for immediate trade entry upon breakout.
    2.  For standard breakouts, it follows a simple 3-state machine:
        AWAITING_BREAK -> AWAITING_RETEST -> IN_TRADE.

    It is designed to be used by the live trading engine and both backtesters to ensure
    perfect consistency between tested and executed strategies.
    """
    def __init__(self, symbol: str, break_detector, retest_detector, pattern_validator, stop_loss_manager, take_profit_manager):
        """
        Initializes the TradingLogic for a specific symbol.

        Args:
            symbol (str): The trading symbol (e.g., 'MES').
            break_detector: An instance of BreakDetector.
            retest_detector: An instance of RetestDetector.
            pattern_validator: An instance of PatternValidator.
            stop_loss_manager: An instance of StopLossManager.
            take_profit_manager: An instance of TakeProfitManager.
        """
        self.symbol = symbol
        self.logger = logger.bind(symbol=symbol)

        # Strategy components
        self.break_detector = break_detector
        self.retest_detector = retest_detector
        self.pattern_validator = pattern_validator
        self.stop_loss_manager = stop_loss_manager
        self.take_profit_manager = take_profit_manager

        # State management
        self.state = 'AWAITING_BREAK'
        self.break_event_details = None

    def reset_state(self):
        """Resets the state machine to its initial state."""
        self.logger.info("Resetting trading state to AWAITING_BREAK.")
        self.state = 'AWAITING_BREAK'
        self.break_event_details = None

    def process_bar(self, bar: dict, active_levels: dict):
        """
        Processes a new bar and returns a trade signal if entry conditions are met.

        Args:
            bar (dict): The latest OHLC bar.
            active_levels (dict): The currently active support/resistance levels.

        Returns:
            dict or None: A trade signal dictionary if a trade should be executed,
                          otherwise None.
        """
        if self.state == 'AWAITING_BREAK':
            break_event = self.break_detector.check_for_break(bar, active_levels)
            if not break_event:
                return None

            self.logger.info(f"Break detected: {break_event}")
            # A+ Setups: Allow for immediate entry without a retest.
            if break_event.get('immediate_entry'):
                self.logger.info("A+ setup identified. Validating pattern for immediate entry.")
                trade_direction = 'BUY' if break_event['type'] == 'up' else 'SELL'
                context = {
                    'symbol': self.symbol,
                    'breakout_candle': break_event['candle'],
                    'latest_bar': bar,
                    'levels': active_levels
                }
                is_valid, reason = self.pattern_validator.validate_signal(trade_direction, context)

                if is_valid:
                    self.logger.success(f"A+ pattern validated for {self.symbol}. Proceeding to trade entry.")
                    self.state = 'IN_TRADE'
                    entry_price = bar['close']
                    stop_loss = self.stop_loss_manager.calculate_stop_from_candle(trade_direction, break_event['candle'], self.symbol)
                    tp_price = self.take_profit_manager.set_profit_target(entry_price, stop_loss, trade_direction)
                    trade_signal = {
                        'trade_direction': trade_direction,
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': tp_price,
                        'trade_details': {
                            'signal_type': 'A+ Breakout',
                            'level_broken': break_event['level_value'],
                            'break_bar': break_event['candle'],
                            'entry_bar': bar
                        }
                    }
                    return trade_signal
                else:
                    self.logger.warning(f"A+ pattern validation failed for {self.symbol}: {reason}. Resetting.")
                    self.reset_state()
            else:
                # Standard Break: Move to wait for a retest.
                self.state = 'AWAITING_RETEST'
                self.break_event_details = break_event

        elif self.state == 'AWAITING_RETEST':
            pivot_candle, rejection_candle, _ = self.retest_detector.check_for_retest(
                latest_bar=bar,
                broken_level_price=self.break_event_details['level_value'],
                break_direction=self.break_event_details['type']
            )
            valid_retest = pivot_candle is not None
            if valid_retest:
                retest_event = {'pivot_candle': pivot_candle, 'rejection_candle': rejection_candle}
            if valid_retest:
                self.logger.info(f"Retest confirmed: {retest_event}. Validating pattern.")
                trade_direction = 'BUY' if self.break_event_details['type'] == 'up' else 'SELL'
                context = {
                    'symbol': self.symbol,
                    'breakout_candle': self.break_event_details['candle'],
                    'pivot_candle': retest_event['pivot_candle'],
                    'rejection_candle': retest_event['rejection_candle'],
                    'latest_bar': bar,
                    'levels': active_levels
                }
                is_valid, reason = self.pattern_validator.validate_signal(trade_direction, context)

                if is_valid:
                    self.logger.success(f"Retest pattern validated for {self.symbol}. Proceeding to trade entry.")
                    self.state = 'IN_TRADE'
                    entry_price = bar['close']
                    stop_loss = self.stop_loss_manager.calculate_stop_from_candle(trade_direction, retest_event['pivot_candle'], self.symbol)
                    tp_price = self.take_profit_manager.set_profit_target(entry_price, stop_loss, trade_direction)
                    trade_signal = {
                        'trade_direction': trade_direction,
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': tp_price,
                        'trade_details': {
                            'signal_type': 'Retest Confirmation',
                            'level_broken': self.break_event_details['level_value'],
                            'break_bar': self.break_event_details['candle'],
                            'entry_bar': bar,
                            'retest_details': retest_event
                        }
                    }
                    return trade_signal
                else:
                    self.logger.warning(f"Retest pattern validation failed for {self.symbol}: {reason}. Resetting.")
                    self.reset_state()

        return None
