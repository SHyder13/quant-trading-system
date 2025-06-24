import unittest
from risk.position_sizer import PositionSizer
import config.risk_config as risk_config

class TestRiskLayer(unittest.TestCase):

    def test_position_sizer(self):
        sizer = PositionSizer(risk_config)
        # Test that position size does not exceed the max limit
        size = sizer.calculate_size(signal='BUY', account_balance=20000000)
        self.assertLessEqual(size, risk_config.MAX_POSITION_SIZE)

if __name__ == '__main__':
    unittest.main()
