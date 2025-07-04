# backtester_projectx.py - A script to test the trading strategy on historical data using the ProjectX API.

import pandas as pd
from datetime import datetime, timedelta
import pytz

# Helper to format timestamps in UTC and ET for logging clarity
def fmt_ts(ts):
    et_tz = pytz.timezone('America/New_York')
    return f"{ts.strftime('%Y-%m-%d %H:%M:%S')} UTC / {ts.astimezone(et_tz).strftime('%H:%M:%S')} ET"
import logging

# Import configurations
import config.strategy_config as strategy_config
import config.risk_config as risk_config
import config.market_config as market_config
from config import main_config

# Import system components
from execution.broker_interface import BrokerInterface
from data.level_calculator import LevelCalculator

from strategy.break_detector import BreakDetector
from strategy.retest_detector import RetestDetector
from strategy.pattern_validator import PatternValidator

from risk.position_sizer import PositionSizer
from risk.stop_loss_manager import StopLossManager
from risk.take_profit_manager import TakeProfitManager

class BacktesterProjectX:
    def __init__(self, start_date, end_date, symbols, initial_balance):
        self.start_date = start_date
        self.end_date = end_date
        self.symbols = symbols
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.broker = BrokerInterface(
            username=main_config.USERNAME,
            api_key=main_config.API_KEY,
            account_name=main_config.ACCOUNT_NAME
        )
        self.level_calculator = LevelCalculator(logger=self.logger)
        self.stop_loss_manager = StopLossManager(risk_config)
        self.take_profit_manager = TakeProfitManager(risk_config)
        self.position_sizer = PositionSizer(risk_config)

        # Trading session times
        self.morning_start = datetime.strptime(strategy_config.MORNING_SESSION_START, '%H:%M').time()
        self.morning_end = datetime.strptime(strategy_config.MORNING_SESSION_END, '%H:%M').time()
        self.regular_end = datetime.strptime('16:00', '%H:%M').time() # Regular session ends at 4 PM ET
        self.afternoon_start = None  # Afternoon session disabled
        self.afternoon_end = None

        # Per-symbol components
        self.symbol_states = {}
        for symbol in self.symbols:
            self.symbol_states[symbol] = {
                'state': 'AWAITING_BREAK',
                'break_detector': BreakDetector(strategy_config, symbol),
                'retest_detector': RetestDetector(strategy_config, symbol),
                'pattern_validator': PatternValidator(),
                'last_break_event': None,
                'retest_context': None,
                'active_trade': None,
                'levels': {},
                'daily_trade_status': {'trade_taken': False, 'last_trade_outcome': None}
            }

        self.trades = []
        self.all_data = {}

    def run(self):
        """Main method to run the backtest."""
        self.logger.info(f"--- Starting ProjectX Backtest for {self.symbols} from {self.start_date} to {self.end_date} ---")
        self.logger.info(f"Initial Balance: ${self.initial_balance:,.2f}")

        # Fetch all historical data for the period using the broker interface
        for symbol in self.symbols:
            # Fetch data from one day prior to calculate levels correctly
            fetch_start_date = self.start_date - timedelta(days=1)
            
            data = self.broker.get_historical_bars(
                symbol,
                start_time=fetch_start_date,
                end_time=self.end_date + timedelta(days=1), # Fetch until the end of the target day
                timeframe_minutes=int(main_config.TIMEFRAME.replace('m', ''))
            )
            if data is None or data.empty:
                self.logger.info(f"Could not fetch data for {symbol} from ProjectX API. Aborting.")
                return
            self.all_data[symbol] = data

        # Loop through each day in the specified date range
        for current_date in pd.date_range(self.start_date, self.end_date):
            self.run_day_simulation(current_date)

    def run_day_simulation(self, current_date):
        """Simulates trading for a single day, mirroring main.py's logic."""
        self.logger.info(f"\n--- Simulating Day: {current_date.strftime('%Y-%m-%d')} ---")

        # 1. Daily Reset and Level Calculation
        daily_data_frames = []
        for symbol in self.symbols:
            self.symbol_states[symbol]['daily_trade_status'] = {'trade_taken': False, 'last_trade_outcome': None}
            self.symbol_states[symbol]['state'] = 'AWAITING_BREAK'
            self.symbol_states[symbol]['active_trade'] = None
            self.symbol_states[symbol]['break_detector'].reset()

            et_tz = pytz.timezone('America/New_York')
            simulation_day_in_et = pd.Timestamp(current_date.date(), tz=et_tz)
            
            cutoff_time_et = simulation_day_in_et + pd.Timedelta(hours=9, minutes=30)
            cutoff_time_utc = cutoff_time_et.tz_convert('UTC')

            start_slice_date = current_date - timedelta(days=4)

            data_for_levels = self.all_data[symbol][
                (self.all_data[symbol].index.date >= start_slice_date.date()) &
                (self.all_data[symbol].index < cutoff_time_utc)
            ]

            if data_for_levels.empty:
                self.logger.info(f"Warning: No historical data available before {cutoff_time_et.strftime('%Y-%m-%d %H:%M')} ET for level calculation.")
                continue

            levels = self.level_calculator.calculate_all_levels(data_for_levels, simulation_day_in_et)
            if not all(val is not None for val in levels.values()):
                if levels.get('pdh') is None or levels.get('pdl') is None:
                    self.logger.info(f"CRITICAL: Could not calculate PDH/PDL for {symbol} on {current_date.strftime('%Y-%m-%d')}. Skipping day.")
                    continue
            
            self.symbol_states[symbol]['levels'] = levels

            # Correctly slice the data for the simulation day, respecting timezones.
            day_start_et = pd.Timestamp(current_date.date(), tz='America/New_York')
            day_end_et = day_start_et + pd.Timedelta(days=1)

            # Filter the data for the current day using the timezone-aware range.
            day_data = self.all_data[symbol][(self.all_data[symbol].index >= day_start_et) & (self.all_data[symbol].index < day_end_et)].copy()
            if day_data.empty:
                self.logger.warning(f"No data found for {symbol} on {current_date.strftime('%Y-%m-%d')}. Skipping day.")
                continue
            day_data['symbol'] = symbol
            daily_data_frames.append(day_data)

        if not daily_data_frames:
            self.logger.warning(f"No data for any symbol on {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            return
        combined_day_data = pd.concat(daily_data_frames).sort_index()

        # --- FIX: Create a full time range and reindex to fill gaps, preventing crashes ---
        et_tz = pytz.timezone('America/New_York')
        day_start_dt = et_tz.localize(datetime.combine(current_date, self.morning_start))
        day_end_dt = et_tz.localize(datetime.combine(current_date, self.regular_end))
        
        # Create a complete minute-by-minute index for the trading session.
        full_time_range = pd.date_range(start=day_start_dt, end=day_end_dt, freq='T')
        
        reindexed_frames = []
        # Group data by symbol, reindex each group to the full time range, and forward-fill gaps.
        for symbol, group in combined_day_data.groupby('symbol'):
            # Reindex to the complete time range, filling missing candles with the last known data.
            # This ensures that the trade monitoring loop runs for every minute of the session.
            reindexed_group = group.reindex(full_time_range, method='ffill')
            
            # Forward-filling can introduce NaNs at the beginning if the first data point is after the range starts.
            # We also need to make sure the symbol column is correctly filled.
            reindexed_group['symbol'].fillna(symbol, inplace=True)
            reindexed_group.dropna(inplace=True) # Drop any rows that couldn't be filled (i.e., at the start)
            
            if not reindexed_group.empty:
                reindexed_frames.append(reindexed_group)

        if not reindexed_frames:
            self.logger.warning(f"No valid data after reindexing for {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            return
            
        combined_day_data_filled = pd.concat(reindexed_frames).sort_index()
        # --- End of FIX ---

        # 2. Loop through each bar of the day using the filled data
        self.logger.info("--- Starting Minute-by-Minute Simulation ---")
        for timestamp, latest_bar in combined_day_data_filled.iterrows():
            symbol = latest_bar['symbol']
            state = self.symbol_states[symbol]
            current_state = state['state']

            # Log the current state and time for each minute
            price_for_log = latest_bar['close']
            self.logger.info(f"[{fmt_ts(timestamp)}] Symbol: {symbol}, State: {current_state}, Price: {price_for_log:.2f}")

            # Check if within trading sessions. New trades are only opened during the morning session,
            # but existing trades are managed until the end of the day.
            current_time_et = timestamp.astimezone(pytz.timezone('America/New_York')).time()
            is_morning_session = self.morning_start <= current_time_et <= self.morning_end

            # If we are not in a trade, we can only look for new setups during the morning session.
            # If we are already in a trade, we continue processing to manage the position.
            if current_state != 'IN_TRADE' and not is_morning_session:
                continue
            
            # This variable is used for logic that might be session-specific in the future.
            current_session = 'morning' if is_morning_session else 'afternoon'

            # --- STATE MACHINE LOGIC ---
            if current_state == 'AWAITING_BREAK':
                key_levels = {k: v for k, v in state['levels'].items() if v is not None}
                current_price = latest_bar['close']
                active_levels = {}
                pmh = key_levels.get('pmh')
                pml = key_levels.get('pml')

                if is_morning_session and pmh and pml:
                    if current_price < pmh and current_price > pml:
                        active_levels['pmh'] = pmh
                        active_levels['pml'] = pml
                    elif current_price > pmh:
                        active_levels['pmh'] = pmh
                    elif current_price < pml:
                        active_levels['pml'] = pml
                
                if not active_levels:
                    support = {k: v for k, v in key_levels.items() if v < current_price}
                    resist = {k: v for k, v in key_levels.items() if v > current_price}
                    if support: active_levels[[k for k, v in key_levels.items() if v == max(support.values())][0]] = max(support.values())
                    if resist: active_levels[[k for k, v in key_levels.items() if v == min(resist.values())][0]] = min(resist.values())
                if not active_levels: 
                    continue

                break_event = state['break_detector'].check_for_break(latest_bar, active_levels)
                if break_event:
                    # --- Immediate Entry for A+ Setups ---
                    if break_event.get('immediate_entry'):
                        self.logger.info(f"  -> [{fmt_ts(timestamp)}] SINGLE-CANDLE A+ SETUP DETECTED. Proceeding directly to trade validation.")
                        trade_side = 'BUY' if break_event['type'] == 'up' else 'SELL'
                        pivot_candle = break_event['candle']
                        stop_loss_price = self.stop_loss_manager.calculate_stop_from_candle(trade_side, pivot_candle, symbol)
                        
                        if stop_loss_price:
                            entry_price = latest_bar['close']
                            quantity = self.position_sizer.calculate_size(
                                self.balance, entry_price, stop_loss_price, symbol, is_high_conviction=break_event.get('high_conviction', False)
                            )
                            if quantity > 0:
                                self._open_trade(symbol, state, trade_side, entry_price, stop_loss_price, quantity, latest_bar, pivot_candle, break_event)
                                continue # Skip to next bar
                            else:
                                self.logger.info(f"  -> [{fmt_ts(timestamp)}] A+ setup trade aborted due to zero position size. Resetting.")
                        else:
                            self.logger.info(f"  -> [{fmt_ts(timestamp)}] A+ setup trade aborted due to stop-loss calculation error. Resetting.")
                        
                        state['state'] = 'AWAITING_BREAK' # Reset whether trade was taken or not
                        state['retest_detector'].reset()
                        state['break_detector'].reset()
                        continue # Move to the next bar

                    # --- Standard Multi-Candle Break Logic ---
                    self.logger.info(f"  >>> BREAK_EVENT {symbol} {fmt_ts(timestamp)}: O={latest_bar['open']:.2f} H={latest_bar['high']:.2f} L={latest_bar['low']:.2f} C={latest_bar['close']:.2f} vs {break_event['level_name'].upper()} {break_event['level_value']:.2f}")
                    name = break_event['level_name'].upper()
                    level_price = break_event['level_value']
                    state['state'] = 'AWAITING_RETEST'
                    state['last_break_event'] = {**break_event, 'level': level_price, 'name': name}
                    state['retest_timeout_stamp'] = timestamp + timedelta(minutes=strategy_config.RETEST_TIMEOUT_MINUTES)
                    continue

            elif current_state == 'AWAITING_RETEST':
                if timestamp > state['retest_timeout_stamp']:
                    self.logger.info(f"  -> [{timestamp.time()}] TIMEOUT: Retest for {symbol} timed out. Resetting.")
                    state['state'] = 'AWAITING_BREAK'
                    continue

                break_event = state['last_break_event']
                break_dir = 'up' if 'up' in break_event['type'] else 'down'
                pivot, reject, conf_type = state['retest_detector'].check_for_retest(latest_bar, break_event['level'], break_dir)

                if pivot is not None and reject is not None:
                    self.logger.info(f"  -> [{fmt_ts(timestamp)}] RETEST DETECTED on {symbol} at {break_event['level']:.2f}. Waiting for confirmation candle.")
                    state['state'] = 'AWAITING_CONFIRMATION'
                    state['retest_context'] = {
                        'break_event': break_event,
                        'pivot_candle': pivot,
                        'rejection_candle': reject,
                        'confluence_type': conf_type
                    }
                    continue

            elif current_state == 'AWAITING_CONFIRMATION':
                if not state.get('retest_context'):
                    self.logger.info(f"  -> [{timestamp.time()}] CRITICAL ERROR: In AWAITING_CONFIRMATION with no context. Resetting.")
                    state['state'] = 'AWAITING_BREAK'
                    continue

                retest_context = state['retest_context']
                break_event = retest_context['break_event']
                break_dir = 'up' if 'up' in break_event['type'] else 'down'

                is_confirmed = False
                if break_dir == 'up' and latest_bar['close'] > latest_bar['open']:
                    is_confirmed = True
                elif break_dir == 'down' and latest_bar['close'] < latest_bar['open']:
                    is_confirmed = True

                if is_confirmed:
                    self.logger.info(f"  -> [{fmt_ts(timestamp)}] CONFIRMATION PASSED for {symbol}. Validating trade.")
                    trade_side = 'BUY' if break_dir == 'up' else 'SELL'
                    context = {
                        'breakout_candle': break_event['candle'],
                        'pivot_candle': retest_context['pivot_candle'],
                        'rejection_candle': retest_context['rejection_candle'],
                        'symbol': symbol,
                        'latest_bar': latest_bar,
                        'level_broken': break_event['level']
                    }

                    is_valid, reason = state['pattern_validator'].validate_signal(trade_side, context)
                    if not is_valid:
                        self.logger.info(f"  -> [{timestamp.time()}] Post-confirmation validation failed: {reason}. Resetting.")
                        state['state'] = 'AWAITING_BREAK'
                        state['retest_context'] = None
                        continue

                    sl_price = self.stop_loss_manager.calculate_stop_from_candle(trade_side, retest_context['pivot_candle'], symbol)
                    if not sl_price: 
                        state['state'] = 'AWAITING_BREAK'; state['retest_context'] = None; continue

                    entry_price = latest_bar['close']
                    is_high_conviction = retest_context['confluence_type'] is not None
                    quantity = self.position_sizer.calculate_size(self.balance, entry_price, sl_price, symbol, is_high_conviction)
                    if quantity == 0: 
                        state['state'] = 'AWAITING_BREAK'; state['retest_context'] = None; continue

                    tp_price = self.take_profit_manager.set_profit_target(entry_price, sl_price, trade_side)
                    daily_levels = state['levels']
                    levels_str = f"PDH:{daily_levels.get('pdh', 'N/A')}, PDL:{daily_levels.get('pdl', 'N/A')}, PMH:{daily_levels.get('pmh', 'N/A')}, PML:{daily_levels.get('pml', 'N/A')}"

                    state['active_trade'] = {
                        'symbol': symbol, 'entry_time': timestamp, 'entry_price': entry_price,
                        'side': trade_side, 'stop_loss': sl_price, 'take_profit': tp_price,
                        'quantity': quantity, 'status': 'ACTIVE',
                        'levels_info': levels_str,
                        'level_broken': break_event['name'],
                        'time_at_break': break_event['candle'].name,
                        'time_at_retest': retest_context['rejection_candle'].name
                    }
                    state['state'] = 'IN_TRADE'
                    state['daily_trade_status']['trade_taken'] = True
                    self.logger.info(f"  -> [{fmt_ts(timestamp)}] TRADE OPEN: {trade_side} {quantity} {symbol} @ {entry_price:.2f}")
                    continue
                else:
                    self.logger.info(f"  -> [{timestamp.time()}] Confirmation FAILED for {symbol}. Resetting.")
                    state['state'] = 'AWAITING_BREAK'
                    continue
                
                state['retest_context'] = None

            elif current_state == 'IN_TRADE':
                trade = state['active_trade']
                if not trade: continue

                # --- Stop-Loss and Take-Profit Check ---
                # self.logger.info(f"DEBUG IN_TRADE | Time={fmt_ts(timestamp)} | Side={trade['side']} | H={latest_bar['high']:.2f}, L={latest_bar['low']:.2f}, C={latest_bar['close']:.2f} | SL={trade['stop_loss']:.2f}, TP={trade['take_profit']:.2f}")

                exit_price = None
                exit_reason = None
                
                if trade['side'] == 'BUY':
                    if latest_bar['low'] <= trade['stop_loss']:
                        exit_price = trade['stop_loss']
                        exit_reason = 'STOP_LOSS'
                    elif latest_bar['high'] >= trade['take_profit']:
                        exit_price = trade['take_profit']
                        exit_reason = 'TAKE_PROFIT'
                elif trade['side'] == 'SELL':
                    if latest_bar['high'] >= trade['stop_loss']:
                        exit_price = trade['stop_loss']
                        exit_reason = 'STOP_LOSS'
                    elif latest_bar['low'] <= trade['take_profit']:
                        exit_price = trade['take_profit']
                        exit_reason = 'TAKE_PROFIT'

                if exit_price:
                    pnl = (exit_price - trade['entry_price']) * trade['quantity'] if trade['side'] == 'BUY' else (trade['entry_price'] - exit_price) * trade['quantity']
                    self.balance += pnl
                    trade['exit_time'] = timestamp
                    trade['exit_price'] = exit_price
                    trade['pnl'] = pnl
                    trade['status'] = 'CLOSED'
                    trade['exit_reason'] = exit_reason
                    self.trades.append(trade)
                    self.logger.info(f"  -> [{fmt_ts(timestamp)}] TRADE CLOSED: {exit_reason} for {symbol}. PnL: ${pnl:,.2f}. New Balance: ${self.balance:,.2f}")
                    state['active_trade'] = None
                    state['state'] = 'AWAITING_BREAK'
                    state['daily_trade_status']['last_trade_outcome'] = 'win' if pnl > 0 else 'loss'
                    continue

    def _open_trade(self, symbol, state, trade_side, entry_price, stop_loss_price, quantity, latest_bar, pivot_candle, break_event):
        """
        Opens a new trade, sets state to IN_TRADE, and logs the entry.
        """
        take_profit_price = self.take_profit_manager.set_profit_target(entry_price, stop_loss_price, trade_side)
        
        daily_levels = state['levels']
        levels_str = f"PDH:{daily_levels.get('pdh', 'N/A')}, PDL:{daily_levels.get('pdl', 'N/A')}, PMH:{daily_levels.get('pmh', 'N/A')}, PML:{daily_levels.get('pml', 'N/A')}"

        state['active_trade'] = {
            'symbol': symbol,
            'entry_time': latest_bar.name,
            'entry_price': entry_price,
            'side': trade_side,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'quantity': quantity,
            'status': 'ACTIVE',
            'levels_info': levels_str,
            'level_broken': break_event['level_name'].upper(),
            'time_at_break': break_event['candle'].name,
            'pivot_candle': pivot_candle,
            'is_immediate_entry': break_event.get('immediate_entry', False)
        }
        
        state['state'] = 'IN_TRADE'
        state['daily_trade_status']['trade_taken'] = True
        
        self.logger.info(f"  -> [{fmt_ts(latest_bar.name)}] TRADE OPEN: {trade_side} {quantity} {symbol} @ {entry_price:.2f}")
        self.logger.info(f"     - SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}, Risk: ${risk_config.RISK_PER_TRADE:.2f}")

    def close_trade(self, state, exit_bar, exit_reason):
        """Records the result of a closed trade and updates balance."""
        trade = state['active_trade']
        exit_price = 0
        if exit_reason == 'Take Profit':
            exit_price = trade['take_profit']
        elif exit_reason == 'Stop Loss':
            exit_price = trade['stop_loss']
        elif exit_reason == 'EOD':
            exit_price = exit_bar['close']

        pnl = (exit_price - trade['entry_price']) if trade['side'] == 'BUY' else (trade['entry_price'] - exit_price)
        pnl_dollars = pnl * market_config.DOLLAR_PER_POINT[trade['symbol']] * trade['quantity']
        self.balance += pnl_dollars

        result = 'WIN' if pnl_dollars > 0 else 'LOSS'
        trade.update({'exit_time': exit_bar.name, 'exit_price': exit_price, 'exit_reason': exit_reason, 'status': 'CLOSED', 'pnl_dollars': pnl_dollars, 'result': result})
        self.trades.append(trade)
        state['daily_trade_status']['last_trade_outcome'] = result.lower()
        state['active_trade'] = None
        state['state'] = 'AWAITING_BREAK'
        self.logger.info(f"     - [{fmt_ts(exit_bar.name)}] Trade Closed: {result} by {exit_reason}. P/L: ${pnl_dollars:,.2f}. New Balance: ${self.balance:,.2f}")

    def shutdown(self):
        """Gracefully shuts down the backtester and prints results."""
        self.logger.info("--- Shutting down ProjectX backtester --- ")
        # --- Close any open positions at the end of the day
        for symbol, state in self.symbol_states.items():
            if state['active_trade']:
                self.logger.info(f"     - Closing EOD open position for {symbol}...")
                # Filter data for the last simulated day to get the correct closing bar
                last_day_data = self.all_data[symbol][self.all_data[symbol].index.date == self.end_date.date()]
                if not last_day_data.empty:
                    last_bar = last_day_data.iloc[-1]
                    self.close_trade(state, last_bar, 'EOD')
                else:
                    self.logger.warning(f"Could not find data for last simulated day {self.end_date.date()} for symbol {symbol} to close EOD position.")

        self.print_results()

    def print_results(self):
        """Prints the final backtest results and saves them to a CSV file."""
        self.logger.info("\n--- Backtest Results ---")
        if not self.trades:
            self.logger.info("No trades were executed.")
            return

        trades_df = pd.DataFrame(self.trades)

        # Save trades to CSV for debugging regardless of outcome
        trades_df.to_csv("backtest_projectx_results.csv", index=False)
        self.logger.info("Full trade log saved to backtest_projectx_results.csv")

        if 'result' not in trades_df.columns or trades_df.empty:
            self.logger.info("No trades were completed to calculate statistics.")
            self.logger.info(f"Final Balance: ${self.balance:,.2f}")
            return

        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['result'] == 'WIN'])
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = trades_df['pnl_dollars'].sum()

        self.logger.info(f"Total Trades: {total_trades}")
        self.logger.info(f"Wins: {wins}")
        self.logger.info(f"Losses: {losses}")
        self.logger.info(f"Win Rate: {win_rate:.2f}%")
        self.logger.info(f"Total P/L: ${total_pnl:,.2f}")
        self.logger.info(f"Final Balance: ${self.balance:,.2f}")


if __name__ == '__main__':
    # Configure logging
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # Add file handler
    file_handler = logging.FileHandler('backtest_projectx_output.txt', mode='w')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    # --- Configuration for the backtest ---
    # We want to analyze the trade from July 1st, 2025
    start_date = datetime(2025, 6, 30)
    end_date = datetime(2025, 7, 3)
    symbols_to_test = ['MNQ']
    initial_capital = 2000.0

    # --- Run the backtest ---
    backtester = BacktesterProjectX(
        start_date=start_date,
        end_date=end_date,
        symbols=symbols_to_test,
        initial_balance=initial_capital
    )
    backtester.run()
    backtester.shutdown()
