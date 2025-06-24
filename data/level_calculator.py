import pandas as pd
import pytz

class LevelCalculator:
    def __init__(self):
        pass

    def calculate_all_levels(self, intraday_data: pd.DataFrame):
        """
        Calculates key levels from intraday data.
        - PDH/PDL are from the previous day's Regular Trading Hours (9:30 AM - 4:00 PM ET).
        - PMH/PML are from the current day's pre-market session (4:00 AM - 9:29 AM ET).
        """
        levels = {'pdh': None, 'pdl': None, 'pmh': None, 'pml': None}

        if intraday_data is None or intraday_data.empty:
            print("Error: Intraday data is empty. Cannot calculate levels.")
            return levels

        # Ensure index is a timezone-aware DatetimeIndex (UTC)
        if not isinstance(intraday_data.index, pd.DatetimeIndex):
            try:
                intraday_data.index = pd.to_datetime(intraday_data.index, utc=True)
            except Exception as e:
                print(f"Error converting index to datetime: {e}")
                return levels
        
        if intraday_data.index.tz is None:
            intraday_data.index = intraday_data.index.tz_localize('UTC')

        # Convert to Eastern Time for all filtering
        et_tz = pytz.timezone('America/New_York')
        intraday_data_et = intraday_data.copy()
        intraday_data_et.index = intraday_data_et.index.tz_convert(et_tz)

        # Determine the most recent date in the data and the previous business day
        latest_date = intraday_data_et.index.normalize().max()
        # Use pandas business day offset to correctly handle weekends/holidays
        previous_trading_day_date = latest_date - pd.tseries.offsets.BDay(1)

        # --- Calculate PDH/PDL from Previous Day's RTH ---
        previous_day_data = intraday_data_et[intraday_data_et.index.date == previous_trading_day_date.date()]
        if not previous_day_data.empty:
            rth_data = previous_day_data.between_time('09:30', '16:00')
            if not rth_data.empty:
                levels['pdh'] = rth_data['high'].max()
                levels['pdl'] = rth_data['low'].min()
                print(f"Calculated RTH PDH/PDL from {previous_trading_day_date.date()}: PDH={levels.get('pdh', 0):.2f}, PDL={levels.get('pdl', 0):.2f}")
            else:
                print(f"Warning: No data found in RTH (09:30-16:00 ET) for {previous_trading_day_date.date()}.")
        else:
            print(f"Warning: No data found for the previous trading day ({previous_trading_day_date.date()}).")

        # --- Calculate PMH/PML from Current Day's Premarket ---
        current_day_data = intraday_data_et[intraday_data_et.index.date == latest_date.date()]
        if not current_day_data.empty:
            premarket_data = current_day_data.between_time('04:00', '09:29')
            if not premarket_data.empty:
                levels['pmh'] = premarket_data['high'].max()
                levels['pml'] = premarket_data['low'].min()
                print(f"Calculated Premarket Levels from {latest_date.date()}: PMH={levels.get('pmh', 0):.2f}, PML={levels.get('pml', 0):.2f}")
            else:
                print(f"Warning: No data found in premarket time range (04:00-09:29 ET) for {latest_date.date()}.")
        else:
             print(f"Warning: No data found for the current day ({latest_date.date()}).")
            
        return levels
