from datetime import timedelta
from config import strategy_config

class SignalGenerator:
    def __init__(self, break_detector, retest_detector):
        self.break_detector = break_detector
        self.retest_detector = retest_detector
        self.timeout = timedelta(minutes=strategy_config.RETEST_TIMEOUT_MINUTES)
        self.active_break_info = None

    def process_bar(self, bar, levels):
        """
        Processes a new data bar to generate a trade signal.
        This is a stateless process that checks for a break, and if one is active, checks for a retest.
        Returns a tuple of (signal_info, pivot_candle, rejection_candle, breakout_candle).
        """
        # If we are not waiting for a retest, look for a new break.
        if self.active_break_info is None:
            break_info = self.break_detector.check_for_break(bar, levels)
            if break_info:
                print(f"[{bar.name}] Break detected: {break_info['type']}. Now watching for retest.")
                self.active_break_info = {
                    'break_event': break_info['type'],
                    'broken_level': break_info['level_value'],
                    'breakout_candle': break_info['candle'],
                    'breakout_time': bar.name
                }
            return {'side': 'NONE'}, None, None, None, None

        # If we are waiting for a retest, check for it.
        if self.active_break_info:
            # Check for timeout first
            if bar.name > self.active_break_info['breakout_time'] + self.timeout:
                timed_out_level = self.active_break_info['broken_level']
                print(f"[{bar.name}] Retest of level {timed_out_level} timed out after {self.timeout}. Resetting.")
                self.reset()
                # Return a special signal to indicate a timeout for a specific level
                return {'side': 'RETEST_TIMEOUT', 'timed_out_level': timed_out_level}, None, None, None, None

            # Determine the direction of the break to check for the correct retest.
            break_direction = 'up' if self.active_break_info['break_event'] == 'up' else 'down'
            
            # Check for the retest signal
            pivot_candle, rejection_candle, confluence_type = self.retest_detector.check_for_retest(
                bar, self.active_break_info['broken_level'], break_direction
            )

            if rejection_candle is not None:
                signal = 'BUY' if break_direction == 'up' else 'SELL'
                print(f"$$$ [{bar.name}] Retest Confirmed & SIGNAL GENERATED: {signal} $$$")
                signal_info = {'price': bar['close'], 'side': signal, 'broken_level': self.active_break_info['broken_level']}
                
                # The breakout_candle is from when the break was first detected.
                breakout_candle = self.active_break_info['breakout_candle']
                signal_to_return = (signal_info, pivot_candle, rejection_candle, breakout_candle, confluence_type)
                
                self.reset()
                return signal_to_return

        return {'side': 'NONE'}, None, None, None, None

    def reset(self):
        """Resets the generator by clearing any active break information."""
        self.active_break_info = None
        # The retest_detector is now stateless, but we call reset for compatibility.
        self.retest_detector.reset()

    def get_last_pivot_candle(self):
        """Delegates to the break detector to get the last pivot candle."""
        return self.break_detector.get_last_pivot_candle()
