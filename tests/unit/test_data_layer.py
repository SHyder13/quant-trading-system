import unittest
from data.level_calculator import LevelCalculator

class TestDataLayer(unittest.TestCase):

    def test_level_calculator(self):
        calculator = LevelCalculator()
        # This is a dummy test. In a real scenario, you'd provide sample historical data.
        levels = calculator.calculate_levels(historical_data=None)
        self.assertIn('pdh', levels)
        self.assertIn('pdl', levels)

if __name__ == '__main__':
    unittest.main()
