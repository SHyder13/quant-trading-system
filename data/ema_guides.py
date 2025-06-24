# data/ema_guides.py

import pandas as pd
import pandas_ta as ta

class EMAGuides:
    """
    Calculates key Exponential Moving Averages (EMAs) for a given dataset.
    This class is stateless and performs calculations on the data provided to it,
    ensuring that backtests remain free of look-ahead bias.
    """
    def __init__(self):
        """
        Initializes the EMAGuides class. It is stateless.
        """
        pass

    def get_latest_ema_values(self, ohlc_data):
        """
        Calculates EMAs on the provided historical data window and returns only the latest values.
        This method is designed to be called iteratively in a backtest to prevent look-ahead bias.

        Args:
            ohlc_data (pd.DataFrame): A DataFrame with 'open', 'high', 'low', 'close' columns
                                      and a DatetimeIndex. The data should be for a single symbol.

        Returns:
            dict: A dictionary with the latest 13, 48, and 200 EMA values, or an empty dict if
                  the data is insufficient or contains NaNs.
        """
        # A minimum number of bars are required to calculate a stable 200 EMA.
        if len(ohlc_data) < 200:
            return {}

        # Calculate the OHLC4 price, which gives a balanced view of the bar's price action
        ohlc4 = (ohlc_data['open'] + ohlc_data['high'] + ohlc_data['low'] + ohlc_data['close']) / 4

        # Calculate the 13, 48, and 200-period EMAs using the OHLC4 price
        ema_13 = ta.ema(ohlc4, length=13)
        ema_48 = ta.ema(ohlc4, length=48)
        ema_200 = ta.ema(ohlc4, length=200)

        # Check if the calculation returned valid pandas Series objects
        if ema_13 is None or ema_13.empty or ema_48 is None or ema_48.empty or ema_200 is None or ema_200.empty:
            return {}

        latest_values = {
            'ema_13': ema_13.iloc[-1],
            'ema_48': ema_48.iloc[-1],
            'ema_200': ema_200.iloc[-1]
        }

        # The initial values of an EMA calculation can be NaN. Ensure we only return valid numbers.
        if pd.isna(latest_values['ema_13']) or pd.isna(latest_values['ema_48']) or pd.isna(latest_values['ema_200']):
            return {}

        return latest_values
