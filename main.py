# main.py - The orchestrator of the trading system

import time
import datetime
import pytz

# Import configurations
import config.strategy_config as strategy_config
import config.risk_config as risk_config
import config.market_config as market_config
from config import main_config

# Import all system components
import config.main_config as main_config

if main_config.SIMULATION_MODE:
    from mocks.mock_market_data_fetcher import MockMarketDataFetcher as MarketDataFetcher
    from mocks.mock_broker_interface import MockBrokerInterface as BrokerInterface
else:
    from data.market_data_fetcher import MarketDataFetcher
    from execution.broker_interface import BrokerInterface
from data.level_calculator import LevelCalculator
from data.session_manager import SessionManager
from data.ema_guides import EMAGuides

from strategy.level_detector import LevelDetector
from strategy.break_detector import BreakDetector
from strategy.retest_detector import RetestDetector
from strategy.signal_generator import SignalGenerator
from strategy.pattern_validator import PatternValidator

from risk.position_sizer import PositionSizer
from risk.stop_loss_manager import StopLossManager
from risk.take_profit_manager import TakeProfitManager
from risk.risk_calculator import RiskCalculator

from execution.authentication_manager import AuthenticationManager
from execution.order_manager import OrderManager
from execution.execution_tracker import ExecutionTracker
from execution.portfolio_manager import PortfolioManager
import config.secrets as secrets

from monitoring.logger import Logger
from monitoring.performance_tracker import PerformanceTracker
from monitoring.alert_system import AlertSystem
from monitoring.dashboard import Dashboard

# --- Mock/Simulated Price Function ---
def get_simulated_price(levels, state, broken_level_price):
    """Generates a simulated price for demonstration purposes."""
    import random
    pdh = levels.get('pdh', 155)
    pdl = levels.get('pdl', 145)

    if state == 'AWAITING_BREAK':
        if random.random() < 0.1:
            return pdh + random.uniform(0.1, 0.5)
        elif random.random() < 0.1:
            return pdl - random.uniform(0.1, 0.5)
        else:
            return random.uniform(pdl + 1, pdh - 1)
    elif state == 'AWAITING_RETEST':
        if random.random() < 0.3:
            return broken_level_price + random.uniform(-0.5, 0.5)
        else:
            if 'pdh' in last_break_event:
                return broken_level_price + random.uniform(1, 3)
            else:
                return broken_level_price - random.uniform(1, 3)
    return random.uniform(pdl, pdh)

def main():

    """The main function to run the trading bot."""

    # --- 1. Initialization ---
    print("Initializing trading system...")
    if main_config.SIMULATION_MODE:
        print("*** RUNNING IN SIMULATION MODE ***")

    # --- 1. System-Wide Setup ---
    logger = Logger()
    
    # Initialize the broker interface, which handles authentication
    broker_interface = BrokerInterface(
        username=main_config.USERNAME,
        api_key=main_config.API_KEY,
        account_name=main_config.ACCOUNT_NAME
    )

    # Check if authentication was successful before proceeding
    if not broker_interface.session_token:
        logger.error("Authentication failed. System shutdown.")
        return
    print("\n--- System is Live: Authenticated with API ---\n")

    # --- Initialize Singleton Components ---
    market_fetcher = MarketDataFetcher(session_token=broker_interface.session_token)
    level_calculator = LevelCalculator()
    level_detector = LevelDetector(level_calculator)
    ema_calculator = EMAGuides()
    session_manager = SessionManager(market_config, strategy_config)
    pattern_validator = PatternValidator()
    stop_loss_manager = StopLossManager(risk_config)

    # --- 2. Per-Symbol Setup ---
    print("Initializing strategy for each symbol...")
    trading_universe = strategy_config.TRADABLE_SYMBOLS
    symbol_states = {}
    for symbol in trading_universe:
        symbol_states[symbol] = {
            'state': 'AWAITING_BREAK',
            'break_detector': BreakDetector(strategy_config, symbol),
            'retest_detector': RetestDetector(strategy_config, symbol),
            'last_break_event': None,
            'active_trade': None,
            'daily_trade_status': {'trade_taken': False, 'last_trade_outcome': None} # NEW
        }
        print(f"  - {symbol} initialized. State: AWAITING_BREAK")

    # --- 3. Pre-Loop Level Calculation ---
    print("\n--- Calculating Initial Key Levels ---")
    levels_by_symbol = {}
    for symbol in list(trading_universe):

        historical_data = market_fetcher.fetch_ohlcv(symbol, main_config.TIMEFRAME, limit=3000)
        if historical_data is not None and not historical_data.empty:
            levels = level_detector.update_levels(historical_data)
            levels_by_symbol[symbol] = levels
        else:
            logger.warning(f"Could not fetch historical data for {symbol}. It will be skipped.")
            trading_universe.remove(symbol)

    # --- 4. Main Trading Loop ---
    print(f"\n--- Entering Main Trading Loop for symbols: {trading_universe} ---")
    last_reset_date = None
    try:
        while True:
            now_et = datetime.datetime.now(pytz.timezone('US/Eastern'))
            today_date = now_et.date()

            # Daily Reset Logic
            if last_reset_date != today_date:
                print(f"--- New Day ({today_date}). Resetting daily trade statuses. ---")
                for symbol in trading_universe:
                    symbol_states[symbol]['daily_trade_status'] = {'trade_taken': False, 'last_trade_outcome': None}
                last_reset_date = today_date

            if not session_manager.is_within_trading_hours(now_et):
                logger.info(f"Outside of defined trading sessions. Pausing...")
                time.sleep(60)
                continue

            current_session = session_manager.get_current_session(now_et)
            print(f"--- Active Session: {current_session.upper()} ---")

            for symbol in trading_universe:
                # --- Session-Specific Entry Logic ---
                daily_status = symbol_states[symbol]['daily_trade_status']
                if current_session == 'afternoon':
                    if daily_status['trade_taken'] and daily_status['last_trade_outcome'] != 'loss':
                        print(f"Skipping {symbol} for afternoon session: A winning trade was already taken today.")
                        continue

                key_levels = levels_by_symbol.get(symbol)
                if not key_levels or not any(key_levels.values()):
                    logger.info(f"Levels for {symbol} are not fully calculated yet. Skipping cycle.")
                    continue

                current_state = symbol_states[symbol]['state']
                print(f"\n--- Processing {symbol} | State: {current_state} ---")

                historical_data = market_fetcher.fetch_ohlcv(symbol, main_config.TIMEFRAME, limit=300)
                if historical_data is None or historical_data.empty:
                    print(f"Could not fetch historical data for {symbol}. Skipping cycle.")
                    continue

                latest_bar = historical_data.iloc[-1]
                latest_emas = ema_calculator.get_latest_ema_values(historical_data)
                if not latest_emas:
                    print(f"Could not calculate EMAs for {symbol}. Skipping cycle.")
                    continue
                
                current_price = latest_bar['close']
                ema_200 = latest_emas.get('ema_200', 0)
                bias = "BULLISH" if current_price > ema_200 and ema_200 > 0 else "BEARISH"
                print(f"Latest Data: Price={current_price:.2f} | Bias: {bias}")

                # --- STATE: AWAITING_BREAK ---
                if current_state == 'AWAITING_BREAK':
                    session_ema_period = 13 if current_session == 'morning' else 48
                    print(f"Using EMA_{session_ema_period} for confluence checks.")

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
                        logger.info(f"No active levels found for {symbol} near current price {current_price}. Waiting.")
                        continue
                    
                    logger.info(f"[{symbol}] Watching active levels: {active_levels}")

                    break_event = symbol_states[symbol]['break_detector'].check_for_break(latest_bar, active_levels, latest_emas, session_ema_period)
                    if break_event:
                        broken_level_name = [name for name, price in active_levels.items() if price == break_event['level']][0].upper()
                        print(f"*** BREAK DETECTED: {symbol} broke {broken_level_name} at {break_event['level']:.2f} ***")
                        print(f"STATE CHANGE: {symbol} -> AWAITING_RETEST of {broken_level_name}")
                        symbol_states[symbol]['state'] = 'AWAITING_RETEST'
                        symbol_states[symbol]['last_break_event'] = {**break_event, 'name': broken_level_name}
                        symbol_states[symbol]['retest_timeout_start'] = time.time()

                # --- STATE: AWAITING_RETEST ---
                elif current_state == 'AWAITING_RETEST':
                    # Check for retest timeout
                    timeout_start = symbol_states[symbol].get('retest_timeout_start', 0)
                    if time.time() - timeout_start > strategy_config.RETEST_TIMEOUT_MINUTES * 60:
                        logger.info(f"Retest for {symbol} timed out. Resetting to AWAITING_BREAK.")
                        symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                        continue # Restart the loop for this symbol with the new state

                    break_event = symbol_states[symbol]['last_break_event']
                    break_direction = 'up' if 'up' in break_event['type'] else 'down'
                    
                    pivot_candle, rejection_candle, confluence_type = symbol_states[symbol]['retest_detector'].check_for_retest(latest_bar, break_event['level'], break_direction, latest_emas)

                    if pivot_candle and rejection_candle:
                        level_name = break_event.get('name', 'level')
                        level_price = break_event['level']
                        print(f"*** TRADE SIGNAL: Confirmed retest of {level_name} at {level_price:.2f} for {symbol}! ***")
                        trade_side = 'BUY' if break_direction == 'up' else 'SELL'

                        # --- Signal Validation ---
                        print("--- Running Signal Validation ---")
                        validation_context = {
                            'breakout_candle': break_event['candle'],
                            'pivot_candle': pivot_candle,
                            'rejection_candle': rejection_candle,
                            'symbol': symbol,
                            'latest_bar': latest_bar,
                            'latest_emas': latest_emas
                        }

                        is_valid_signal = pattern_validator.validate_signal(trade_side, validation_context)
                        if not is_valid_signal:
                            symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                            continue
                
                        # Determine if it's a high-conviction trade based on the confluence type
                        is_high_conviction = confluence_type is not None

                        # Calculate Stop Loss
                        stop_loss_price = stop_loss_manager.calculate_stop_from_candle(trade_side, pivot_candle, symbol)
                        if not stop_loss_price:
                            print("Could not calculate stop loss. Aborting trade.")
                            symbol_states[symbol]['state'] = 'AWAITING_BREAK' # Reset state
                            continue

                        # Execute the trade via the OrderManager
                        order_manager = OrderManager(broker_interface, broker_interface.get_account_balance())
                        order_id, quantity = order_manager.execute_trade(
                            symbol=symbol,
                            side=trade_side,
                            entry_price=current_price, # Use current price as approximate entry
                            stop_loss_price=stop_loss_price,
                            is_high_conviction=is_high_conviction
                        )

                        if order_id:
                            print(f"Trade executed for {symbol}. Now monitoring.")
                            symbol_states[symbol]['state'] = 'IN_TRADE'
                            symbol_states[symbol]['active_trade'] = {
                                'order_id': order_id,
                                'side': trade_side,
                                'quantity': quantity,
                                'entry_price': current_price,
                                'status': 'ACTIVE'
                            }
                            # Update daily status: a trade has been taken
                            symbol_states[symbol]['daily_trade_status']['trade_taken'] = True
                        else:
                            print(f"Trade execution failed for {symbol}. Resetting state.")
                            symbol_states[symbol]['state'] = 'AWAITING_BREAK'

                # --- STATE: IN_TRADE ---
                elif current_state == 'IN_TRADE':
                    trade_details = symbol_states[symbol]['active_trade']
                    if not trade_details:
                        logger.error(f"In IN_TRADE state for {symbol} but no active trade details found. Resetting.")
                        symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                        continue

                    # NOTE: The current logic only handles an EMA-based trailing stop.
                    # A complete implementation would also need to poll the broker
                    # to check if the SL/TP bracket order has been filled.

                    # Instantiate the TakeProfitManager to check for EMA trail
                    tp_manager = TakeProfitManager(risk_config)

                    # Check if the position should be exited based on the 13 EMA rule
                    should_exit_on_ema = tp_manager.check_ema_trail_stop(
                        latest_bar=latest_bar,
                        position_side=trade_details['side'],
                        latest_emas=latest_emas
                    )

                    trade_status = trade_details.get('status', 'ACTIVE')

                    # --- ACTIVE STATUS ---
                    if trade_status == 'ACTIVE':
                        if should_exit_on_ema:
                            # Instead of exiting, go into probation
                            print(f"!!! 13 EMA PROBATION STARTED for {symbol} {trade_details['side']} trade. Waiting for next candle to confirm. !!!")
                            trade_details['status'] = 'EMA_PROBATION'
                            trade_details['probation_candle_timestamp'] = latest_bar.name
                        else:
                            print(f"Trade for {symbol} remains active. Monitoring...")

                    # --- PROBATION STATUS ---
                    elif trade_status == 'EMA_PROBATION':
                        # Check if we are on a new candle since probation started
                        if latest_bar.name > trade_details['probation_candle_timestamp']:
                            print(f"Confirming 13 EMA exit for {symbol} on new candle...")
                            if should_exit_on_ema:
                                # The next candle also failed to reclaim, so exit
                                print(f"!!! EXIT CONFIRMED: {symbol} failed to reclaim 13 EMA. Closing position. !!!")
                                order_manager = OrderManager(broker_interface, broker_interface.get_account_balance())
                                order_manager.close_position(
                                    symbol=symbol,
                                    side=trade_details['side'],
                                    quantity=trade_details['quantity'],
                                    original_order_id=trade_details['order_id']
                                )
                                # Update daily status assuming EMA trail is a loss for afternoon session purposes
                                symbol_states[symbol]['daily_trade_status']['last_trade_outcome'] = 'loss'
                                
                                # Reset state for the symbol
                                symbol_states[symbol]['state'] = 'AWAITING_BREAK'
                                symbol_states[symbol]['active_trade'] = None
                            else:
                                # Price reclaimed the 13 EMA, trade is safe
                                print(f"*** RECLAIMED: {symbol} has reclaimed the 13 EMA. Trade remains active. ***")
                                trade_details['status'] = 'ACTIVE'
                                trade_details.pop('probation_candle_timestamp', None) # Remove probation timestamp
                        else:
                            print(f"Awaiting next candle to confirm 13 EMA probation for {symbol}...")

            # Wait before the next cycle
            print("\nCycle complete. Waiting for next interval...")
            time.sleep(strategy_config.LOOP_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n--- Trading bot stopped manually. System shutdown. ---")
    except Exception as e:
        logger.exception("An unexpected error occurred in the main loop:")
        print(f"\n--- An unexpected error occurred. See logs. System shutdown. ---")




if __name__ == '__main__':
    main()
