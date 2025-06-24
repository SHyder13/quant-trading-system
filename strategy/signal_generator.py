from datetime import timedelta
from config import strategy_config

class SignalGenerator:
    def __init__(self, break_detector, retest_detector):
        self.break_detector = break_detector
        self.retest_detector = retest_detector
        self.timeout = timedelta(minutes=strategy_config.RETEST_TIMEOUT_MINUTES)
        self.reset()

    def process_bar(self, bar, levels, latest_emas):
        """
        Processes a new data bar through the state machine to generate a signal.
        Returns a tuple of (signal, pivot_candle, rejection_candle, breakout_candle).
        """
        if self.state == 'WAITING_FOR_BREAK':
            break_event, broken_level, pivot_candle = self.break_detector.check_for_break(bar, levels, latest_emas)
            if break_event:
                # Handle the new, immediate confluence break signal
                if 'confluence_break' in break_event:
                    signal = 'BUY' if break_event == 'confluence_break_up' else 'SELL'
                    print(f"$$$ [{bar.name}] EMA Confluence Break & SIGNAL GENERATED: {signal} $$$")
                    # For this signal type, pivot_candle is the bounce candle, and there's no retest/rejection candle.
                    signal_to_return = (signal, pivot_candle, None, bar)
                    self.reset()
                    return signal_to_return
                
                # Handle the standard break that requires a retest
                else:
                    print(f"[{bar.name}] Break detected: {break_event}. Moving to WAITING_FOR_RETEST.")
                    self.state = 'WAITING_FOR_RETEST'
                    self.break_event = break_event
                    self.broken_level = broken_level
                    self.breakout_candle = pivot_candle # In a standard break, this is the breakout candle
                    self.breakout_time = bar.name
                    self.retest_detector.reset()

        elif self.state == 'WAITING_FOR_RETEST':
            # Check for timeout first
            if bar.name > self.breakout_time + self.timeout:
                print(f"[{bar.name}] Retest timed out after {self.timeout}. Resetting.")
                self.reset()
                return 'NONE', None, None, None # Exit processing for this bar after timeout.

            break_direction = 'up' if self.break_event == 'resistance_break_up' else 'down'
            pivot_candle, rejection_candle = self.retest_detector.check_for_retest(bar, self.broken_level, break_direction, latest_emas)
            if pivot_candle is not None:
                signal = 'BUY' if self.break_event == 'resistance_break_up' else 'SELL'
                print(f"$$$ [{bar.name}] Retest Confirmed & SIGNAL GENERATED: {signal} $$$")
                signal_to_return = (signal, pivot_candle, rejection_candle, self.breakout_candle)
                self.reset()
                return signal_to_return

        return 'NONE', None, None, None

    def reset(self):
        """Resets the state machine to its initial state."""
        self.state = 'WAITING_FOR_BREAK'
        self.break_event = None
        self.breakout_candle = None
        self.broken_level = None
        self.breakout_time = None
        self.retest_detector.reset()

    def get_last_pivot_candle(self):
        """Delegates to the break detector to get the last pivot candle."""
        return self.break_detector.get_last_pivot_candle()
