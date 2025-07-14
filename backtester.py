# backtester.py - A script to test the trading strategy on historical data.

import pandas as pd
from datetime import datetime, timedelta
import pytz

# Import configurations
import config.strategy_config as strategy_config
import config.risk_config as risk_config
import config.market_config as market_config
from config import main_config

# Import system components
# Switching to Databento for historical data
from data.databento_loader import DatabentoLoader
from data.level_calculator import LevelCalculator

from strategy.break_detector import BreakDetector
from strategy.retest_detector import RetestDetector
from strategy.pattern_validator import PatternValidator
from strategy.trading_logic import TradingLogic

from risk.position_sizer import PositionSizer
from risk.stop_loss_manager import StopLossManager
from risk.take_profit_manager import TakeProfitManager

import logging
# from execution.broker_interface import BrokerInterface # No longer needed for backtesting

class Backtester:
    def __init__(self, start_date, end_date, symbols, initial_balance):
        self.original_start_date = start_date  # Store the original start date for reporting
        self.start_date = start_date
        self.end_date = end_date
        self.symbols = symbols
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.logger = logging.getLogger(__name__)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        # self.broker = BrokerInterface(...) # No longer needed for backtesting

        # ------------------------------------------------------------------
        # Databento integration (NEW)
        # ------------------------------------------------------------------
        self.data_loader = DatabentoLoader(
            api_key=main_config.DATABENTO_API_KEY,
            file_paths=main_config.DATABENTO_FILE_PATHS,
        )
        self.level_calculator = LevelCalculator()
        self.stop_loss_manager = StopLossManager(risk_config)
        self.take_profit_manager = TakeProfitManager(risk_config)
        self.position_sizer = PositionSizer(risk_config)


        # Trading session times
        self.morning_start = datetime.strptime(strategy_config.MORNING_SESSION_START, '%H:%M').time()
        self.morning_end = datetime.strptime(strategy_config.MORNING_SESSION_END, '%H:%M').time()
        self.afternoon_start = None  # Afternoon trading disabled
        self.afternoon_end = None

        # Per-symbol components - Aligned with main.py
        self.symbol_states = {}
        pattern_validator = PatternValidator() # Stateless, so one instance is fine
        for symbol in self.symbols:
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
                'levels': {},
                'daily_trade_status': {'trade_taken': False, 'last_trade_outcome': None}
            }

        self.trades = []
        self.all_data = {}

    def run(self):
        """Main method to run the backtest."""
        logging.info(f"--- Starting Backtest for {self.symbols} from {self.start_date} to {self.end_date} ---")
        logging.info(f"Initial Balance: ${self.initial_balance:,.2f}")

        # Fetch all historical data for the period
        for symbol in self.symbols:
            fetch_start_date = self.start_date - timedelta(days=5)
            start_date_str = fetch_start_date.isoformat() + 'Z'
            end_date_str = self.end_date.isoformat() + 'Z'
            data = self.data_loader.load_data(
                symbol,
                start_date=fetch_start_date,
                end_date=self.end_date,
                timeframe=main_config.TIMEFRAME,
            )
            if data is None or data.empty:
                logging.info(f"Could not fetch data for {symbol}. Aborting.")
                return
            self.all_data[symbol] = data

        # Loop through each day in the specified date range
        for current_date in pd.date_range(self.start_date, self.end_date):
            self.run_day_simulation(current_date)

    def run_day_simulation(self, current_date):
        """Simulates trading for a single day, mirroring main.py's logic."""
        logging.info(f"\n--- Simulating Day: {current_date.strftime('%Y-%m-%d')} ---")

        # 1. Daily Reset and Level Calculation
        daily_data_frames = []
        for symbol in self.symbols:
            self.symbol_states[symbol]['daily_trade_status'] = {'trade_taken': False, 'last_trade_outcome': None}
            self.symbol_states[symbol]['logic'].reset_state() # Reset state daily
            self.symbol_states[symbol]['active_trade'] = None

            # The backtest loop provides a timezone-naive date (at midnight UTC).
            # We must first define this as a specific day in the exchange's timezone (ET)
            # to avoid timezone conversion errors that shift the date.
            et_tz = pytz.timezone('America/New_York')
            simulation_day_in_et = pd.Timestamp(current_date.date(), tz=et_tz)

            # Define the cutoff for the data slice: 09:30 ET on the current simulation day.
            # This ensures the calculator has data for the previous day and the current pre-market.
            cutoff_time_et = simulation_day_in_et + pd.Timedelta(hours=9, minutes=30)
            cutoff_time_utc = cutoff_time_et.tz_convert('UTC')

            # Slice from a few days back to ensure we capture the previous trading day, even after weekends/holidays.
            start_slice_date = current_date - timedelta(days=4)

            # Filter the main dataframe to create the slice for the calculator.
            data_for_levels = self.all_data[symbol][
                (self.all_data[symbol].index.date >= start_slice_date.date()) &
                (self.all_data[symbol].index < cutoff_time_utc)
            ]

            if data_for_levels.empty:
                logging.info(f"Warning: No historical data available before {cutoff_time_et.strftime('%Y-%m-%d %H:%M')} ET for level calculation.")
                continue

            # Pass the correctly defined timezone-aware date to the calculator.
            levels = self.level_calculator.calculate_all_levels(data_for_levels, simulation_day_in_et)
            if not all(val is not None for val in levels.values()):
                # It's possible for some levels not to form (e.g., no pre-market data), but we need PDH/PDL at a minimum.
                if levels.get('pdh') is None or levels.get('pdl') is None:
                    logging.info(f"CRITICAL: Could not calculate PDH/PDL for {symbol} on {current_date.strftime('%Y-%m-%d')}. Skipping day.")
                    continue
            
            self.symbol_states[symbol]['levels'] = levels

            day_data = self.all_data[symbol][self.all_data[symbol].index.date == current_date.date()].copy()
            day_data['symbol'] = symbol
            daily_data_frames.append(day_data)

        if not daily_data_frames: return
        combined_day_data = pd.concat(daily_data_frames).sort_index()

        # 2. Loop through each bar of the day
        for timestamp, bar_data in combined_day_data.iterrows():
            symbol = bar_data['symbol']
            state = self.symbol_states[symbol]
            logic_instance = state['logic']
            # Convert timestamp to ET to correctly identify trading sessions.
            et_tz = pytz.timezone('America/New_York')
            current_time_et = timestamp.astimezone(et_tz).time()

            # Session check
            is_morning = self.morning_start <= current_time_et <= self.morning_end
            if not is_morning and logic_instance.state != 'IN_TRADE':
                continue
            
            latest_bar = bar_data

            # --- UNIFIED STRATEGY LOGIC --- #
            if logic_instance.state != 'IN_TRADE':
                key_levels = {k: v for k, v in state['levels'].items() if v is not None}
                current_price = latest_bar['close']
                
                active_levels = {}
                pmh = key_levels.get('pmh')
                pml = key_levels.get('pml')

                if is_morning and pmh and pml:
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
                if not active_levels: continue

                trade_signal = logic_instance.process_bar(latest_bar, active_levels)

                if trade_signal:
                    trade_details = trade_signal.get('trade_details', {})
                    level_broken = trade_details.get('level_broken')

                    if level_broken:
                        slippage = abs(trade_signal['entry_price'] - level_broken)
                        if slippage > strategy_config.MAX_ENTRY_SLIPPAGE_POINTS:
                            logging.info(f"Trade for {symbol} rejected due to high slippage: {slippage:.2f}")
                            logic_instance.reset_state()
                            continue

                    quantity = self.position_sizer.calculate_size(
                        self.balance,
                        trade_signal['entry_price'],
                        trade_signal['stop_loss'],
                        symbol,
                        is_high_conviction=('A+' in trade_details.get('signal_type', ''))
                    )

                    if quantity > 0:
                        daily_levels = state['levels']
                        levels_str = f"PDH:{daily_levels.get('pdh', 'N/A')}, PDL:{daily_levels.get('pdl', 'N/A')}, PMH:{daily_levels.get('pmh', 'N/A')}, PML:{daily_levels.get('pml', 'N/A')}"

                        state['active_trade'] = {
                            'symbol': symbol, 'entry_time': timestamp, 'entry_price': trade_signal['entry_price'],
                            'side': trade_signal['trade_direction'], 'stop_loss': trade_signal['stop_loss'],
                            'take_profit': trade_signal['take_profit'], # Use TP from the signal
                            'quantity': quantity, 'status': 'ACTIVE',
                            'levels_info': levels_str,
                            'level_broken': level_broken,
                            'time_at_break': trade_details.get('break_bar', {}).name,
                            'time_at_retest': trade_details.get('entry_bar', {}).name
                        }
                        state['daily_trade_status']['trade_taken'] = True
                        logging.info(f"  -> [{timestamp.time()}] TRADE OPEN: {trade_signal['trade_direction']} {quantity} {symbol} @ {trade_signal['entry_price']:.2f}")
                    else:
                        logging.info(f"Trade for {symbol} aborted due to zero position size. Resetting.")
                        logic_instance.reset_state()

            # --- STATE: IN_TRADE ---
            elif logic_instance.state == 'IN_TRADE':
                trade = state['active_trade']
                # Check for hard SL/TP first
                if (trade['side'] == 'BUY' and latest_bar['low'] <= trade['stop_loss']) or (trade['side'] == 'SELL' and latest_bar['high'] >= trade['stop_loss']):
                    self.close_trade(state, latest_bar, 'SL')
                    continue
                if (trade['side'] == 'BUY' and latest_bar['high'] >= trade['take_profit']) or (trade['side'] == 'SELL' and latest_bar['low'] <= trade['take_profit']):
                    self.close_trade(state, latest_bar, 'TP')
                    continue



    def close_trade(self, state, exit_bar, exit_reason):
        """Records the result of a closed trade and updates balance."""
        trade = state['active_trade']
        exit_price = 0
        if exit_reason == 'TP': exit_price = trade['take_profit']
        elif exit_reason == 'SL': exit_price = trade['stop_loss']

        pnl = (exit_price - trade['entry_price']) if trade['side'] == 'BUY' else (trade['entry_price'] - exit_price)
        pnl_dollars = pnl * market_config.DOLLAR_PER_POINT[trade['symbol']] * trade['quantity']
        self.balance += pnl_dollars

        result = 'WIN' if pnl_dollars > 0 else 'LOSS'
        trade.update({'exit_time': exit_bar.name, 'exit_price': exit_price, 'exit_reason': exit_reason, 'status': 'CLOSED', 'pnl_dollars': pnl_dollars, 'result': result})
        self.trades.append(trade)
        state['daily_trade_status']['last_trade_outcome'] = result.lower()
        state['active_trade'] = None
        state['logic'].reset_state()
        logging.info(f"     - [{exit_bar.name.time()}] Trade Closed: {result} by {exit_reason}. P/L: ${pnl_dollars:,.2f}. New Balance: ${self.balance:,.2f}")

    def shutdown(self):
        """Gracefully shuts down the backtester and prints results."""
        logging.info("--- Shutting down backtester --- ")
        self.print_results()

    def print_results(self):
        """Prints the final backtest results and saves them to a CSV file."""
        logging.info("\n--- Backtest Results ---")
        if not self.trades:
            logging.info("No trades were executed.")
            return

        trades_df = pd.DataFrame(self.trades)
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['result'] == 'WIN'])
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = trades_df['pnl_dollars'].sum()

        # --- CSV Generation ---
        csv_data = []
        for trade in self.trades:
            entry_time = trade.get('entry_time')
            exit_time = trade.get('exit_time')
            break_time = trade.get('time_at_break')
            retest_time = trade.get('time_at_retest')

            entry_info = f"{trade.get('entry_price', 0):.2f} @ {entry_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(entry_time, pd.Timestamp) else 'N/A'}"
            et_tz = pytz.timezone('America/New_York')
            entry_time_et = entry_time.astimezone(et_tz).strftime('%Y-%m-%d %H:%M:%S') if isinstance(entry_time, pd.Timestamp) else 'N/A'
            exit_time_et = exit_time.astimezone(et_tz).strftime('%Y-%m-%d %H:%M:%S') if isinstance(exit_time, pd.Timestamp) else 'N/A'
            break_time_et = break_time.astimezone(et_tz).strftime('%Y-%m-%d %H:%M:%S') if isinstance(break_time, pd.Timestamp) else 'N/A'
            retest_time_et = retest_time.astimezone(et_tz).strftime('%Y-%m-%d %H:%M:%S') if isinstance(retest_time, pd.Timestamp) else 'N/A'

            exit_info = f"{trade.get('exit_reason', 'N/A')} @ {exit_time_et}"
            break_time_str = break_time_et
            retest_time_str = retest_time_et

            csv_data.append({
                'Ticker': trade['symbol'],
                'Levels (PDH, PDL, PMH, PML)': trade['levels_info'],
                'Level Broken': trade['level_broken'],
                'Retested Level': trade.get('retested_level', 'N/A'),
                'Time At Level Break': break_time_str,
                'Time at Level Retest': retest_time_str,
                'Entry Price & Time': entry_info,
                'Exit Reason & Time': exit_info,
                'Result': trade.get('result', 'N/A')
            })

        if csv_data:
            csv_df = pd.DataFrame(csv_data)
            # Use the original start date for the filename to fix the naming bug
            start_str = self.original_start_date.strftime('%Y%m%d')
            end_str = self.end_date.strftime('%Y%m%d')
            csv_filename = f"backtest_results_{start_str}_to_{end_str}.csv"
            csv_df.to_csv(csv_filename, index=False)
            logging.info(f"\nBacktest results saved to {csv_filename}")
        # --- End CSV Generation ---

        logging.info(f"\nStarting Balance:   ${self.initial_balance:,.2f}")
        logging.info(f"Ending Balance:     ${self.balance:,.2f}")
        logging.info(f"Total P/L:          ${total_pnl:,.2f}")
        logging.info(f"Total Trades:       {total_trades}")
        logging.info(f"Wins:               {wins}")
        logging.info(f"Losses:             {losses}")
        logging.info(f"Win Rate:           {win_rate:.2f}%")
import logging
from datetime import datetime

if __name__ == '__main__':
    # ==================================================================
    # --- Logging Config --- 
    # ==================================================================
    log_filename = f"backtest_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    # ==================================================================
    # ==================================================================
    # --- User Config ---
    # ==================================================================
    # Define the symbols to test from the available data
    symbols_to_test = ['MNQ', 'MES']

    # Define the date range for the backtest.
    # The backtester will run on the data available within this range.
    # Adjusted to match the available Databento data file.
    #Earliest date is 2020-06-28
    #Latest date is 2025-06-27
    backtest_start_date = datetime(2022, 1, 1)
    backtest_end_date = datetime(2022, 12, 31)

    # Define the initial account balance for the simulation.
    # Increased for a longer-term test.
    account_balance = 50000.0
    # ==================================================================

    logging.info("--- Backtester Configuration ---")
    logging.info(f"Symbols: {symbols_to_test}")
    logging.info(f"Period: {backtest_start_date.strftime('%Y-%m-%d')} to {backtest_end_date.strftime('%Y-%m-%d')}")
    logging.info(f"Initial Balance: ${account_balance:,.2f}")
    logging.info("---------------------------------")

    # Initialize and run the backtester
    backtester = Backtester(
        start_date=backtest_start_date,
        end_date=backtest_end_date,
        symbols=symbols_to_test,
        initial_balance=account_balance
    )
    backtester.run()
    backtester.shutdown() # Call shutdown to print final results
