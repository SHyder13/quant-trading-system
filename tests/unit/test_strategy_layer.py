import unittest
from strategy.signal_generator import SignalGenerator

class TestStrategyLayer(unittest.TestCase):

    def test_signal_generation(self):
        generator = SignalGenerator()
        # Test case: no signal should be generated if there's no break or retest
        signal = generator.generate_signal(break_event=None, retest_event=None)
        self.assertEqual(signal, 'NONE')

        # Test case: a signal should be generated when conditions are met
        signal = generator.generate_signal(break_event='pdh_break_up', retest_event=True)
        self.assertIn(signal, ['BUY', 'SELL'])

if __name__ == '__main__':
    unittest.main()
