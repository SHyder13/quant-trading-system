import datetime
import pytz
from config import strategy_config, market_config

class SessionManager:
    def __init__(self, market_config, strategy_config):
        self.market_config = market_config
        self.strategy_config = strategy_config
        self.timezone = pytz.timezone('America/New_York')
        self.morning_start_time = datetime.datetime.strptime(self.strategy_config.MORNING_SESSION_START, '%H:%M').time()
        self.morning_end_time = datetime.datetime.strptime(self.strategy_config.MORNING_SESSION_END, '%H:%M').time()
        self.afternoon_start_time = datetime.datetime.strptime(self.strategy_config.AFTERNOON_SESSION_START, '%H:%M').time()
        self.afternoon_end_time = datetime.datetime.strptime(self.strategy_config.AFTERNOON_SESSION_END, '%H:%M').time()

    def get_current_time_et(self):
        """Returns the current time in the America/New_York timezone."""
        return datetime.datetime.now(self.timezone).time()

    def is_market_open(self, now_et=None):
        """Checks if the market is open: not a weekend/holiday and within ANY defined session."""
        if now_et is None:
            now_et = datetime.datetime.now(self.timezone)

        # Check for weekends
        if now_et.weekday() >= 5:
            return False

        # Check for market holidays
        if now_et.date() in self.market_config.MARKET_HOLIDAYS:
            return False

        # Check if within any trading session
        current_time = now_et.time()
        morning_start = datetime.datetime.strptime(self.strategy_config.MORNING_SESSION_START, '%H:%M').time()
        morning_end = datetime.datetime.strptime(self.strategy_config.MORNING_SESSION_END, '%H:%M').time()
        afternoon_start = datetime.datetime.strptime(self.strategy_config.AFTERNOON_SESSION_START, '%H:%M').time()
        afternoon_end = datetime.datetime.strptime(self.strategy_config.AFTERNOON_SESSION_END, '%H:%M').time()

        is_in_morning = morning_start <= current_time <= morning_end
        is_in_afternoon = afternoon_start <= current_time <= afternoon_end

        return is_in_morning or is_in_afternoon

    def get_current_session(self, current_time_et):
        """
        Determines the current trading session (morning or afternoon) based on the provided timestamp.

        Args:
            current_time_et (datetime): A timezone-aware datetime object (in America/New_York).

        Returns:
            str: 'morning', 'afternoon', or None if outside of defined sessions.
        """
        current_time = current_time_et.time()

        if self.morning_start_time <= current_time < self.morning_end_time:
            return 'morning'
        
        if self.afternoon_start_time <= current_time < self.afternoon_end_time:
            return 'afternoon'
            
        return None

    def is_within_trading_hours(self, now_et=None):
        """
        Checks if the current time is within any allowed strategy trading window.

        Args:
            now_et (datetime.datetime, optional): The time to check. 
                                                  If None, uses the current system time.
        """
        if now_et is None:
            now_et = datetime.datetime.now(self.timezone)

        # First, check if the general market is open (handles holidays/weekends)
        if not self.is_market_open(now_et):
            return False
        
        # Then, check if it's within one of the specific strategy sessions
        return self.get_current_session(now_et) is not None
