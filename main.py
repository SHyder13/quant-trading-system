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

from data.level_calculator import LevelCalculator
from data.session_manager import SessionManager
from strategy.level_detector import LevelDetector
from strategy.break_detector import BreakDetector
from strategy.retest_detector import RetestDetector
from strategy.pattern_validator import PatternValidator
from strategy.trading_logic import TradingLogic
from risk.stop_loss_manager import StopLossManager
from execution.order_manager import OrderManager
from monitoring.logger import Logger

class TradingSystem:
    """ Encapsulates the entire trading system, running on an event-driven architecture. """
    def resolve_all_contracts(self):
        """Uses the broker interface to resolve contract IDs for all symbols in the trading universe."""
        self.logger.info("--- Resolving contracts for all symbols ---")
        pruned_symbols = []
        for symbol in self.trading_universe:
            self.logger.info(f"Resolving contract for {symbol}...")
            # The broker interface now handles fetching and caching contract details
            # We just need to call it to ensure the details are loaded.
            details = self.broker_interface.get_contract_details(symbol)
            if details and details.get('id'):
                # The broker interface caches the full details. We can update our local map if needed.
                market_config.SYMBOL_MAP[symbol]['contract_id'] = details.get('id')
                self.logger.info(f"Successfully resolved {symbol} to contract ID: {details.get('id')}")
            else:
                self.logger.error(f"Contract resolution failed for {symbol}. Removing from trading universe.")
                pruned_symbols.append(symbol)

        # Prune any symbols that failed to resolve
        for symbol in pruned_symbols:
            self.trading_universe.remove(symbol)
            del self.symbol_states[symbol]

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

        # --- 2. Initialize Core Components ---
        self.level_detector = LevelDetector(LevelCalculator())
        self.session_manager = SessionManager(market_config, strategy_config)
        self.stop_loss_manager = StopLossManager(risk_config)
        self.order_manager = OrderManager(self.broker_interface, self.broker_interface.get_account_balance())

        # --- 3. Per-Symbol State Initialization ---
        self.trading_universe = list(strategy_config.TRADABLE_SYMBOLS)
        self.symbol_states = {}
        self.levels_by_symbol = {}
        pattern_validator = PatternValidator() # Stateless, so one instance is fine

        for symbol in self.trading_universe:
            # Each symbol gets its own instance of the trading logic engine
            self.symbol_states[symbol] = {
                'logic': TradingLogic(
                    symbol=symbol,
                    break_detector=BreakDetector(strategy_config, symbol, self.logger),
                    retest_detector=RetestDetector(strategy_config, symbol),
                    pattern_validator=pattern_validator,
                    stop_loss_manager=self.stop_loss_manager,
                    take_profit_manager=self.take_profit_manager
                ),
                'active_trade': None,
                'daily_trade_status': {'trade_taken': False, 'last_trade_outcome': None}
            }
            self.logger.info(f"  - {symbol} initialized with its own logic engine.")

        # --- 4. Dynamic Contract Resolution & Validation ---
        self.resolve_all_contracts()

        # --- 5. Real-Time and Event-Driven Setup ---
        self.realtime_manager = RealtimeManager(self.broker_interface.session_token, self.broker_interface.account_id)
        self.bar_aggregator = BarAggregator(timeframe_minutes=main_config.TIMEFRAME_MINUTES)
        event_bus.subscribe("NEW_BAR_CLOSED", self._on_new_bar)
        event_bus.subscribe("GATEWAY_ORDER_UPDATE", self._on_order_update)
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

            # Use the broker interface directly, which handles caching and uses the correct contract ID internally
            historical_data = self.broker_interface.get_historical_bars(symbol, main_config.TIMEFRAME, 3000)
            if historical_data is not None and not historical_data.empty:
                levels = self.level_detector.update_levels(historical_data)
                self.levels_by_symbol[symbol] = levels
                # The TradingLogic instance initializes in 'AWAITING_BREAK' state by default.
                self.logger.info(f"Levels for {symbol} calculated. Logic engine is active and AWAITING_BREAK.")
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
            self.logger.info(f"Outside trading hours ({now_et.strftime('%H:%M:%S ET')}). Pausing strategy logic.")
            return

        current_session = self.session_manager.get_current_session(now_et)
        daily_status = self.symbol_states[symbol]['daily_trade_status']
        if current_session == 'afternoon':
            if daily_status['trade_taken'] and daily_status['last_trade_outcome'] != 'loss':
                return

        self.logger.info(f"--- New Bar for {symbol} in {current_session.upper()} session: O:{bar['open']} H:{bar['high']} L:{bar['low']} C:{bar['close']} V:{bar['volume']} ---")
        
        latest_bar = pd.Series(bar)
        current_price = latest_bar['close']
        logic_instance = self.symbol_states[symbol]['logic']
        key_levels = self.levels_by_symbol.get(symbol)

        if not key_levels or not any(key_levels.values()):
            return

        # Determine active levels to watch
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

        # --- Unified Strategy Logic ---
        trade_signal = logic_instance.process_bar(latest_bar, active_levels)

        if trade_signal and not self.symbol_states[symbol].get('active_trade'):
            self.logger.info(f"Trade signal received for {symbol}: {trade_signal['trade_direction']} at {trade_signal['entry_price']}")

            # Place the trade via the order manager
            order_result = self.order_manager.place_trade(
                symbol=symbol,
                trade_direction=trade_signal['trade_direction'],
                entry_price=trade_signal['entry_price'],
                stop_loss=trade_signal['stop_loss'],
                take_profit=trade_signal['take_profit'],
                trade_details=trade_signal['trade_details']
            )

            if order_result and order_result.get('status') == 'Filled':
                self.logger.info(f"Successfully placed and filled trade for {symbol}.")
                self.symbol_states[symbol]['active_trade'] = order_result
                self.symbol_states[symbol]['daily_trade_status']['trade_taken'] = True
            else:
                self.logger.error(f"Failed to place trade for {symbol}. Reason: {order_result.get('reason') if order_result else 'Unknown'}")
                logic_instance.reset() # Reset logic if trade fails

    def _on_order_update(self, order_update: dict):
        """ Handles updates for open orders (e.g., stop loss, take profit). """
        symbol = order_update.get('symbol')
        if not symbol or symbol not in self.symbol_states:
            return

        state = self.symbol_states[symbol]
        active_trade = state.get('active_trade')

        if not active_trade or active_trade['order_id'] != order_update.get('order_id'):
            return

        status = order_update.get('status')
        if status in ['Filled', 'Cancelled']:
            self.logger.info(f"Trade for {symbol} closed. Status: {status}")
            
            # Update daily trade outcome
            if status == 'Filled':
                # Assuming the update contains P/L info or we can derive it
                pnl = order_update.get('pnl', 0)
                outcome = 'win' if pnl > 0 else 'loss'
                state['daily_trade_status']['last_trade_outcome'] = outcome
                self.logger.info(f"Trade outcome for {symbol}: {outcome.upper()} (P/L: {pnl})")

            # Reset state for the next opportunity
            state['active_trade'] = None
            state['logic'].reset()
            self.logger.info(f"{symbol} state has been reset. Awaiting next break.")
            return

        # --- Delegate to the TradingLogic class ---
        trade_signal = logic_instance.process_bar(latest_bar, active_levels)

        if trade_signal:
            # --- Entry Slippage Filter ---
            slippage = abs(trade_signal['entry_price'] - trade_signal['level_broken'])
            if slippage > strategy_config.MAX_ENTRY_SLIPPAGE_POINTS:
                self.logger.info(f"Trade rejected due to high slippage: {slippage:.2f} > {strategy_config.MAX_ENTRY_SLIPPAGE_POINTS}")
                logic_instance.reset_state() # Reset state after slippage fail
                return

            order_id, quantity = self.order_manager.execute_trade(
                symbol=symbol,
                side=trade_signal['trade_direction'],
                entry_price=trade_signal['entry_price'],
                stop_loss_price=trade_signal['stop_loss'],
                is_high_conviction=False # TODO: Add conviction level to signal
            )

            if order_id:
                self.logger.success(f"Trade executed for {symbol}. Now monitoring.")
                self.symbol_states[symbol]['active_trade'] = {
                    'order_id': order_id,
                    'side': trade_signal['trade_direction'],
                    'quantity': quantity,
                    'entry_price': trade_signal['entry_price'],
                    'status': 'ACTIVE'
                }
                self.symbol_states[symbol]['daily_trade_status']['trade_taken'] = True
            else:
                self.logger.warning(f"Trade execution failed for {symbol}. Resetting logic state.")
                logic_instance.reset_state()

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
                    self.logger.info(f"Resetting logic state for {target_symbol}.")
                    self.symbol_states[target_symbol]['logic'].reset_state()
                    self.symbol_states[target_symbol]['active_trade'] = None

                elif status in ['CANCELLED', 'REJECTED']:
                    self.logger.warning(f"Order {order_id} for {target_symbol} was {status}. Resetting logic state.")
                    self.symbol_states[target_symbol]['logic'].reset_state()
                    self.symbol_states[target_symbol]['active_trade'] = None

        except Exception as e:
            self.logger.error(f"Error processing order update: {order_data}. Error: {e}")


def main():
    """Initializes and runs the trading system."""
    trading_system = TradingSystem()
    if trading_system.broker_interface.session_token:
        trading_system.start()

if __name__ == "__main__":
    main()
