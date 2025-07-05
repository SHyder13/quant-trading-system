import pandas as pd
import pytz
import logging

class LevelCalculator:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def calculate_all_levels(self, intraday_data: pd.DataFrame, current_simulation_date: pd.Timestamp = None):
        """
        Calculates key levels from intraday data relative to a specific simulation date.
        - PDH/PDL are from the previous day's Regular Trading Hours (9:30 AM - 4:00 PM ET).
        - PMH/PML are from the current day's pre-market session (4:00 AM - 9:29 AM ET).
        """
        levels = {'pdh': None, 'pdl': None, 'pmh': None, 'pml': None}

        if intraday_data is None or intraday_data.empty:
            self.logger.error("Intraday data is empty. Cannot calculate levels.")
            return levels

        # Ensure index is a timezone-aware DatetimeIndex (UTC)
        if not isinstance(intraday_data.index, pd.DatetimeIndex):
            try:
                intraday_data.index = pd.to_datetime(intraday_data.index, utc=True)
            except Exception as e:
                self.logger.error(f"Error converting index to datetime: {e}")
                return levels
        
        if intraday_data.index.tz is None:
            intraday_data.index = intraday_data.index.tz_localize('UTC')

        # Convert to Eastern Time for all filtering
        et_tz = pytz.timezone('America/New_York')
        intraday_data_et = intraday_data.copy()
        intraday_data_et.index = intraday_data_et.index.tz_convert(et_tz)

        # Use the provided simulation date or default to now()
        if current_simulation_date is None:
            current_simulation_date = pd.Timestamp.now(tz='UTC')
        elif current_simulation_date.tz is None:
            current_simulation_date = current_simulation_date.tz_localize('UTC')
        simulation_date_et = current_simulation_date.tz_convert(et_tz).normalize()

        # --- Find the True Previous Trading Day and Calculate PDH/PDL ---
        available_past_dates = sorted(
            [d for d in intraday_data_et.index.date if d < simulation_date_et.date()], 
            reverse=True
        )
        
        previous_trading_day_date = None
        if not available_past_dates:
            self.logger.warning(f"No past dates available in data before {simulation_date_et.date()}. Cannot calculate PDH/PDL.")
        else:
            for date_candidate in available_past_dates:
                day_data = intraday_data_et[intraday_data_et.index.date == date_candidate]
                if day_data.empty:
                    continue

                rth_start = pd.Timestamp(date_candidate, tz=et_tz).replace(hour=9, minute=30, second=0)
                rth_end = pd.Timestamp(date_candidate, tz=et_tz).replace(hour=16, minute=0, second=0)
                rth_data = day_data[(day_data.index >= rth_start) & (day_data.index <= rth_end)]
                
                if not rth_data.empty:
                    valid_rth_data = rth_data[rth_data['low'] > 0]
                    if not valid_rth_data.empty:
                        levels['pdh'] = valid_rth_data['high'].max()
                        levels['pdl'] = valid_rth_data['low'].min()
                        previous_trading_day_date = date_candidate
                        self.logger.info(f"Calculated RTH PDH/PDL from {previous_trading_day_date}: PDH={levels.get('pdh', 0):.2f}, PDL={levels.get('pdl', 0):.2f}")
                        break
            
            if not previous_trading_day_date:
                self.logger.warning(f"No previous trading day with RTH data found before {simulation_date_et.date()}. Searched {len(available_past_dates)} past dates.")

        # --- Calculate PMH/PML from Current Day's Premarket ---
        current_day_data = intraday_data_et[intraday_data_et.index.date == simulation_date_et.date()]
        if not current_day_data.empty:
            pm_start = simulation_date_et.replace(hour=4, minute=0, second=0)
            pm_end = simulation_date_et.replace(hour=9, minute=29, second=59)
            premarket_data = current_day_data[(current_day_data.index >= pm_start) & (current_day_data.index <= pm_end)]
            
            if not premarket_data.empty:
                valid_premarket_data = premarket_data[premarket_data['low'] > 0]
                if not valid_premarket_data.empty:
                    levels['pmh'] = valid_premarket_data['high'].max()
                    levels['pml'] = valid_premarket_data['low'].min()
                    self.logger.info(f"Calculated Premarket Levels from {simulation_date_et.date()}: PMH={levels.get('pmh', 0):.2f}, PML={levels.get('pml', 0):.2f}")
                else:
                    self.logger.warning(f"No valid data (price > 0) in premarket time range for {simulation_date_et.date()}.")
            else:
                self.logger.warning(f"No data found in premarket time range (04:00-09:29 ET) for {simulation_date_et.date()}.")
        else:
             self.logger.warning(f"No data found for the current day ({simulation_date_et.date()}).")
            
        return levels
