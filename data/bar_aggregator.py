# data/bar_aggregator.py

import pandas as pd
from datetime import datetime, timedelta
import pytz

from realtime.event_bus import event_bus
from monitoring.logger import Logger

class BarAggregator:
    """
    Aggregates real-time trade ticks into time-based OHLCV bars.
    
    Subscribes to raw market trade events and, upon the close of each time interval
    (e.g., 1 minute), it publishes a consolidated bar for consumption by the strategy.
    """
    def __init__(self, timeframe_minutes: int = 1):
        self.logger = Logger()
        self.timeframe = timedelta(minutes=timeframe_minutes)
        self.current_bars = {}  # {contract_id: {bar_data}}
        
        # Subscribe to the raw trade data from the gateway
        event_bus.subscribe("GATEWAY_MARKET_TRADE", self._handle_trade_event)
        self.logger.info(f"BarAggregator initialized for a {timeframe_minutes}-minute timeframe.")

    def _handle_trade_event(self, event_data: dict):
        """Processes a single trade tick from the market data stream."""
        try:
            contract_id = event_data['contractId']
            trade = event_data['data'][0] # Data comes in a list
            price = trade['price']
            size = trade['size']
            # Assuming timestamp is in UTC and ISO 8601 format
            timestamp = pd.to_datetime(trade['timestamp']).tz_convert('UTC')
        except (KeyError, IndexError, TypeError) as e:
            self.logger.error(f"Malformed trade event received: {event_data}. Error: {e}")
            return

        # Determine the start time of the bar this trade belongs to
        bar_start_time = timestamp.replace(second=0, microsecond=0)
        if self.timeframe.total_seconds() > 60:
             minute_floor = (timestamp.minute // (self.timeframe.total_seconds() // 60)) * (self.timeframe.total_seconds() // 60)
             bar_start_time = timestamp.replace(minute=int(minute_floor), second=0, microsecond=0)

        current_bar = self.current_bars.get(contract_id)

        # If there's no current bar or this trade is for a new bar
        if not current_bar or bar_start_time > current_bar['timestamp']:
            # If a previous bar existed, it's now closed. Publish it.
            if current_bar:
                self.logger.info(f"New bar detected. Publishing closed bar for {contract_id}: {current_bar}")
                event_bus.publish("NEW_BAR_CLOSED", contract_id, current_bar)
            
            # Start a new bar
            self.current_bars[contract_id] = {
                'timestamp': bar_start_time,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': size
            }
        else:
            # Update the existing bar
            current_bar['high'] = max(current_bar['high'], price)
            current_bar['low'] = min(current_bar['low'], price)
            current_bar['close'] = price
            current_bar['volume'] += size
