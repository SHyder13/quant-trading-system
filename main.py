# main.py - The event-driven orchestrator of the trading system

import time
import datetime
import pytz
import pandas as pd

# Import configurations
import config.strategy_config as strategy_config
import config.risk_config as risk_config
import config.market_config as market_config
from config import main_config

# --- Import System Components ---
# Real-time and Event-Driven Components
from realtime.event_bus import event_bus
from realtime.realtime_manager import RealtimeManager
from data.bar_aggregator import BarAggregator

# Core Application Logic Components
from execution.broker_interface import BrokerInterface
from data.market_data_fetcher import MarketDataFetcher # Still needed for initial level calculation
from data.level_calculator import LevelCalculator
from data.session_manager import SessionManager
from strategy.level_detector import LevelDetector
from strategy.break_detector import BreakDetector
from strategy.retest_detector import RetestDetector
from strategy.pattern_validator import PatternValidator
from risk.stop_loss_manager import StopLossManager
from execution.order_manager import OrderManager
from monitoring.logger import Logger

class TradingSystem:
    """ Encapsulates the entire trading system, running on an event-driven architecture. """
    def __init__(self):
        self.logger = Logger()
        self.logger.info("Initializing trading system...")

        # --- 1. System-Wide Setup ---
        self.broker_interface = BrokerInterface(
            username=main_config.USERNAME,
            api_key=main_config.API_KEY,
            account_name=main_config.ACCOUNT_NAME
        )
        if not self.broker_interface.session_token:
            self.logger.error("Authentication failed. System shutdown.")
            return
        self.logger.info("--- System is Live: Authenticated with API ---")

        # --- Initialize Core Components ---
        self.market_fetcher = MarketDataFetcher(session_token=self.broker_interface.session_token)
        self.level_detector = LevelDetector(LevelCalculator())
        self.session_manager = SessionManager(market_config, strategy_config)
        self.pattern_validator = PatternValidator()
        self.stop_loss_manager = StopLossManager(risk_config)
        self.order_manager = OrderManager(self.broker_interface, self.broker_interface.get_account_balance())

        # --- 2. Real-Time and Event-Driven Setup ---
        self.realtime_manager = RealtimeManager(self.broker_interface.session_token, self.broker_interface.account_id)
        self.bar_aggregator = BarAggregator(timeframe_minutes=main_config.TIMEFRAME_MINUTES)
        event_bus.subscribe("NEW_BAR_CLOSED", self._on_new_bar)
        event_bus.subscribe("GATEWAY_ORDER_UPDATE", self._on_order_update)

        # --- 3. Per-Symbol State Initialization ---
        self.trading_universe = list(strategy_config.TRADABLE_SYMBOLS)
        self.symbol_states = {}
        self.levels_by_symbol = {}
        for symbol in self.trading_universe:
            self.symbol_states[symbol] = {
                'state': 'INITIALIZING',
                'break_detector': BreakDetector(strategy_config, symbol),
                'retest_detector': RetestDetector(strategy_config, symbol),
                'last_break_event': None,
                'active_trade': None,
                'daily_trade_status': {'trade_taken': False, 'last_trade_outcome': None}
            }
            self.logger.info(f"  - {symbol} initialized. State: INITIALIZING")
        self.last_reset_date = None

    def start(self):
        """ Starts the trading system. """
        self.logger.info("--- Starting Trading System ---")
        self.realtime_manager.start()
        self._calculate_initial_levels()
        
        self.logger.info(f"--- System Ready. Listening for market data for: {self.trading_universe} ---")
        try:
            while True:
                time.sleep(1) # Keep main thread alive
        except KeyboardInterrupt:
            self.logger.info("--- Trading bot stopped manually. ---")
        finally:
            self.stop()

    def stop(self):
        """ Gracefully stops all components. """
        self.logger.info("--- System shutting down. ---")
        self.realtime_manager.stop()

    def _calculate_initial_levels(self):
        """ Fetches historical data to calculate the initial set of key levels. """
        self.logger.info("--- Calculating Initial Key Levels ---")
        for symbol in self.trading_universe[:]: # Iterate on a copy
            contract_id = market_config.SYMBOL_MAP.get(symbol, {}).get('contract_id')
            if not contract_id:
                self.logger.warning(f"No contract ID found for {symbol}. Skipping.")
                self.trading_universe.remove(symbol)
                continue

            historical_data = self.market_fetcher.fetch_ohlcv(symbol, main_config.TIMEFRAME, limit=3000)
            if historical_data is not None and not historical_data.empty:
                levels = self.level_detector.update_levels(historical_data)
                self.levels_by_symbol[symbol] = levels
                self.symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                self.logger.info(f"Levels for {symbol} calculated. State -> AWAITING_BREAK")
                # Once levels are ready, subscribe to live data
                self.realtime_manager.subscribe_to_market_data(contract_id)
            else:
                self.logger.warning(f"Could not fetch historical data for {symbol}. It will be skipped.")
                self.trading_universe.remove(symbol)

    def _on_new_bar(self, contract_id: str, bar: dict):
        """ The core strategy logic, triggered when a new bar closes. """
        symbol = next((s for s, d in market_config.SYMBOL_MAP.items() if d.get('contract_id') == contract_id), None)
        if not symbol or symbol not in self.trading_universe:
            return

        # --- Session & Daily Reset Management ---
        now_et = datetime.datetime.now(pytz.timezone('US/Eastern'))
        today_date = now_et.date()

        if self.last_reset_date != today_date:
            self.logger.info(f"--- New Day ({today_date}). Resetting daily trade statuses. ---")
            for sym in self.trading_universe:
                self.symbol_states[sym]['daily_trade_status'] = {'trade_taken': False, 'last_trade_outcome': None}
            self.last_reset_date = today_date

        if not self.session_manager.is_within_trading_hours(now_et):
            return

        current_session = self.session_manager.get_current_session(now_et)
        daily_status = self.symbol_states[symbol]['daily_trade_status']
        if current_session == 'afternoon':
            if daily_status['trade_taken'] and daily_status['last_trade_outcome'] != 'loss':
                return

        self.logger.info(f"--- New Bar for {symbol} in {current_session.upper()} session: O:{bar['open']} H:{bar['high']} L:{bar['low']} C:{bar['close']} V:{bar['volume']} ---")
        
        latest_bar = pd.Series(bar)
        current_price = latest_bar['close']
        current_state = self.symbol_states[symbol]['state']
        key_levels = self.levels_by_symbol.get(symbol)

        if not key_levels or not any(key_levels.values()):
            return

        # --- STATE: AWAITING_BREAK ---
        if current_state == 'AWAITING_BREAK':
            support_levels = {k: v for k, v in key_levels.items() if v < current_price}
            resistance_levels = {k: v for k, v in key_levels.items() if v > current_price}
            closest_support = max(support_levels.values()) if support_levels else None
            closest_resistance = min(resistance_levels.values()) if resistance_levels else None
            
            active_levels = {}
            if closest_support:
                support_key = [k for k, v in key_levels.items() if v == closest_support][0]
                active_levels[support_key] = closest_support
            if closest_resistance:
                resistance_key = [k for k, v in key_levels.items() if v == closest_resistance][0]
                active_levels[resistance_key] = closest_resistance

            if not active_levels:
                return
            
            self.logger.info(f"[{symbol}] Watching active levels: {active_levels}")

            break_event = self.symbol_states[symbol]['break_detector'].check_for_break(latest_bar, active_levels)
            if break_event:
                broken_level_name = [name for name, price in active_levels.items() if price == break_event['level']][0].upper()
                self.logger.info(f"*** BREAK DETECTED: {symbol} broke {broken_level_name} at {break_event['level']:.2f} ***")
                self.logger.info(f"STATE CHANGE: {symbol} -> AWAITING_RETEST of {broken_level_name}")
                self.symbol_states[symbol]['state'] = 'AWAITING_RETEST'
                self.symbol_states[symbol]['last_break_event'] = {**break_event, 'name': broken_level_name}
                self.symbol_states[symbol]['retest_timeout_start'] = time.time()

        # --- STATE: AWAITING_RETEST ---
        elif current_state == 'AWAITING_RETEST':
            timeout_start = self.symbol_states[symbol].get('retest_timeout_start', 0)
            if time.time() - timeout_start > strategy_config.RETEST_TIMEOUT_MINUTES * 60:
                self.logger.info(f"Retest for {symbol} timed out. Resetting to AWAITING_BREAK.")
                self.symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                return

            break_event = self.symbol_states[symbol]['last_break_event']
            break_direction = 'up' if 'up' in break_event['type'] else 'down'
            
            pivot_candle, rejection_candle, confluence_type = self.symbol_states[symbol]['retest_detector'].check_for_retest(latest_bar, break_event['level'], break_direction)

            if pivot_candle is not None and rejection_candle is not None:
                level_name = break_event.get('name', 'level')
                level_price = break_event['level']
                self.logger.info(f"*** TRADE SIGNAL: Confirmed retest of {level_name} at {level_price:.2f} for {symbol}! ***")
                trade_side = 'BUY' if break_direction == 'up' else 'SELL'

                self.logger.info("--- Running Signal Validation ---")
                validation_context = {
                    'breakout_candle': break_event['candle'],
                    'pivot_candle': pivot_candle,
                    'rejection_candle': rejection_candle,
                    'symbol': symbol,
                    'latest_bar': latest_bar,
                    'levels': self.daily_levels[symbol]
                }

                is_valid_signal = self.pattern_validator.validate_signal(trade_side, validation_context)
                if not is_valid_signal:
                    self.symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                    return
        
                is_high_conviction = confluence_type is not None

                stop_loss_price = self.stop_loss_manager.calculate_stop_from_candle(trade_side, pivot_candle, symbol)
                if not stop_loss_price:
                    self.logger.warning("Could not calculate stop loss. Aborting trade.")
                    self.symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                    return

                order_id, quantity = self.order_manager.execute_trade(
                    symbol=symbol,
                    side=trade_side,
                    entry_price=current_price,
                    stop_loss_price=stop_loss_price,
                    is_high_conviction=is_high_conviction
                )

                if order_id:
                    self.logger.info(f"Trade executed for {symbol}. Now monitoring.")
                    self.symbol_states[symbol]['state'] = 'IN_TRADE'
                    self.symbol_states[symbol]['active_trade'] = {
                        'order_id': order_id,
                        'side': trade_side,
                        'quantity': quantity,
                        'entry_price': current_price,
                        'status': 'ACTIVE'
                    }
                    self.symbol_states[symbol]['daily_trade_status']['trade_taken'] = True
                else:
                    self.logger.warning(f"Trade execution failed for {symbol}. Resetting state.")
                    self.symbol_states[symbol]['state'] = 'AWAITING_BREAK'

    def _on_order_update(self, order_data: dict):
        """ Handles real-time updates about orders from the gateway. """
        try:
            # The gateway sends updates as a list of order objects
            for update in order_data:
                order_id = update.get('orderId')
                status = update.get('status')

                if not order_id or not status:
                    self.logger.warning(f"Malformed order update received: {update}")
                    continue

                # Find which symbol this order belongs to
                target_symbol = None
                active_trade = None
                for symbol, state in self.symbol_states.items():
                    if state.get('active_trade') and state['active_trade'].get('order_id') == order_id:
                        target_symbol = symbol
                        active_trade = state['active_trade']
                        break
                
                if not target_symbol or not active_trade:
                    self.logger.info(f"Received update for an untracked or old order ID: {order_id}")
                    continue

                self.logger.info(f"--- Order Update for {target_symbol} (ID: {order_id}): Status -> {status} ---")

                # If the order is filled, the trade is closed (either by SL or TP)
                if status == 'FILLED':
                    filled_price = update.get('avgFillPrice', 0)
                    side = active_trade['side']
                    entry_price = active_trade['entry_price']
                    
                    # Determine outcome
                    outcome = 'win' if (side == 'BUY' and filled_price > entry_price) or \
                                       (side == 'SELL' and filled_price < entry_price) else 'loss'
                    
                    self.logger.info(f"*** TRADE CLOSED for {target_symbol}: Side={side}, Entry={entry_price}, Fill={filled_price}, Outcome={outcome.upper()} ***")

                    # Update daily stats
                    self.symbol_states[target_symbol]['daily_trade_status']['last_trade_outcome'] = outcome
                    
                    # Reset state for the symbol
                    self.logger.info(f"Resetting state for {target_symbol} to AWAITING_BREAK.")
                    self.symbol_states[target_symbol]['state'] = 'AWAITING_BREAK'
                    self.symbol_states[target_symbol]['active_trade'] = None

                elif status in ['CANCELLED', 'REJECTED']:
                    self.logger.warning(f"Order {order_id} for {target_symbol} was {status}. Resetting state.")
                    self.symbol_states[target_symbol]['state'] = 'AWAITING_BREAK'
                    self.symbol_states[target_symbol]['active_trade'] = None

        except Exception as e:
            self.logger.error(f"Error processing order update: {order_data}. Error: {e}")


def main():
    system = TradingSystem()
    if system.broker_interface.session_token:
        system.start()

if __name__ == "__main__":
    main()
