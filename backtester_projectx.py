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
from strategy.trading_logic import TradingLogic

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
                'logic': TradingLogic(
                    symbol=symbol,
                    break_detector=BreakDetector(strategy_config, symbol, self.logger),
                    retest_detector=RetestDetector(strategy_config, symbol),
                    pattern_validator=PatternValidator(logger=self.logger),
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
                timeframe=main_config.TIMEFRAME,
                limit=20000 # Increased limit for multi-day fetch
            )
            if data is None or data.empty:
                self.logger.info(f"Could not fetch data for {symbol} from ProjectX API. Aborting.")
                return
            self.all_data[symbol] = data

        self.logger.info(f"--- Running ProjectX Backtest from {self.start_date} to {self.end_date} ---")

        current_date = pd.to_datetime(self.start_date)
        while current_date <= pd.to_datetime(self.end_date):
            self.run_day_simulation(current_date.date())
            current_date += timedelta(days=1)

        self.shutdown()

    def run_day_simulation(self, current_date):
        """Simulates trading for a single day, mirroring main.py's logic."""
        self.logger.info(f"\n--- Simulating Day: {current_date.strftime('%Y-%m-%d')} ---")

        # 1. Daily Reset and Level Calculation
        daily_data_frames = []
        for symbol in self.symbols:
            self.symbol_states[symbol]['daily_trade_status'] = {'trade_taken': False, 'last_trade_outcome': None}
            self.symbol_states[symbol]['logic'].reset_state()
            self.symbol_states[symbol]['active_trade'] = None

            et_tz = pytz.timezone('America/New_York')
            simulation_day_in_et = pd.Timestamp(current_date, tz=et_tz)
            
            cutoff_time_et = simulation_day_in_et + pd.Timedelta(hours=9, minutes=30)
            cutoff_time_utc = cutoff_time_et.tz_convert('UTC')

            start_slice_date = current_date - timedelta(days=4)

            data_for_levels = self.all_data[symbol][
                (self.all_data[symbol].index.date >= start_slice_date) &
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
            day_start_et = pd.Timestamp(current_date, tz='America/New_York')
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

        # --- Resample data to 2-minute timeframe ---
        resampled_frames = []
        for symbol, group in combined_day_data.groupby('symbol'):
            # Resample to 2-minute timeframe, creating OHLC candles
            resampled_group = group.resample('2min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()  # Drop intervals with no data

            if not resampled_group.empty:
                resampled_group['symbol'] = symbol
                resampled_frames.append(resampled_group)

        if not resampled_frames:
            self.logger.warning(f"No valid data after resampling to 2-minute candles for {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            return
            
        combined_day_data_resampled = pd.concat(resampled_frames).sort_index()
        # --- End of Resampling ---

        # Filter data to only include relevant trading hours (e.g., 9:30 AM to 4:00 PM ET)
        et_tz = pytz.timezone('America/New_York')
        filter_start_time = self.morning_start
        filter_end_time = self.regular_end

        filter_start_dt_et = et_tz.localize(datetime.combine(current_date, filter_start_time))
        filter_end_dt_et = et_tz.localize(datetime.combine(current_date, filter_end_time))

        # Apply the filter
        initial_rows = len(combined_day_data_resampled)
        combined_day_data_resampled = combined_day_data_resampled[
            (combined_day_data_resampled.index >= filter_start_dt_et) &
            (combined_day_data_resampled.index < filter_end_dt_et)
        ]
        self.logger.info(f"Filtered daily bars from {initial_rows} to {len(combined_day_data_resampled)} to focus on trading hours ({filter_start_time.strftime('%H:%M')} - {filter_end_time.strftime('%H:%M')} ET).")

        if combined_day_data_resampled.empty:
            self.logger.warning(f"No data available within the specified trading hours for {current_date.strftime('%Y-%m-%d')}. Skipping day.")
            return

        # Prime the break detector with the last pre-market candle
        for symbol in self.symbols:
            all_symbol_data = self.all_data[symbol]
            trading_session_data = combined_day_data_resampled[combined_day_data_resampled['symbol'] == symbol]
            
            if not trading_session_data.empty:
                first_candle_timestamp = trading_session_data.index[0]
                pre_market_candles = all_symbol_data[all_symbol_data.index < first_candle_timestamp]
                if not pre_market_candles.empty:
                    last_pre_market_candle = pre_market_candles.iloc[-1]
                    self.symbol_states[symbol]['logic'].break_detector.previous_bar = last_pre_market_candle
                    self.logger.info(f"Priming BreakDetector for {symbol} with pre-market candle at {last_pre_market_candle.name.astimezone(et_tz).strftime('%H:%M:%S')} ET")

        # 2. Loop through each 2-minute bar of the day
        self.logger.info("--- Starting 2-Minute Bar Simulation ---")
        for timestamp, latest_bar in combined_day_data_resampled.iterrows():
            symbol = latest_bar['symbol']
            state = self.symbol_states[symbol]
            logic_instance = state['logic']

            # Log the current state and OHLC for each 2-minute candle
            ohlc_log = (f"O:{latest_bar['open']:.2f}, H:{latest_bar['high']:.2f}, "
                        f"L:{latest_bar['low']:.2f}, C:{latest_bar['close']:.2f}")
            self.logger.info(f"[{fmt_ts(timestamp)}] Symbol: {symbol}, State: {logic_instance.state}, OHLC: ({ohlc_log})")

            # Manage active trade (check for SL/TP)
            if logic_instance.state == 'IN_TRADE' and state['active_trade']:
                # (This logic is assumed to be present after the snippet and remains unchanged)
                pass

            # Check if within trading sessions for new trades
            current_time_et = timestamp.astimezone(pytz.timezone('America/New_York')).time()
            is_morning_session = self.morning_start <= current_time_et <= self.morning_end

            if logic_instance.state != 'IN_TRADE' and not is_morning_session:
                continue

            # --- UNIFIED STRATEGY LOGIC ---
            if logic_instance.state != 'IN_TRADE':
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
                    active_levels = key_levels
                
                if not active_levels: 
                    continue

                # Delegate to the TradingLogic class
                trade_signal = logic_instance.process_bar(latest_bar, active_levels)

                if trade_signal:
                    # --- Slippage Filter ---
                    slippage = abs(trade_signal['entry_price'] - trade_signal['level_broken'])
                    if slippage > strategy_config.MAX_ENTRY_SLIPPAGE_POINTS:
                        self.logger.info(f"Trade for {symbol} rejected due to high slippage: {slippage:.2f}")
                        logic_instance.reset_state()
                        continue

                    # --- Position Sizing ---
                    quantity = self.position_sizer.calculate_size(
                        self.balance, 
                        trade_signal['entry_price'], 
                        trade_signal['stop_loss'], 
                        symbol, 
                        is_high_conviction=False # TODO: Add conviction to signal
                    )

                    if quantity > 0:
                        tp_price = self.take_profit_manager.set_profit_target(
                            trade_signal['entry_price'], trade_signal['stop_loss'], trade_signal['trade_direction']
                        )
                        daily_levels = state['levels']
                        levels_str = f"PDH:{daily_levels.get('pdh', 'N/A')}, PDL:{daily_levels.get('pdl', 'N/A')}, PMH:{daily_levels.get('pmh', 'N/A')}, PML:{daily_levels.get('pml', 'N/A')}"

                        state['active_trade'] = {
                            'symbol': symbol, 'entry_time': timestamp, 'entry_price': trade_signal['entry_price'],
                            'side': trade_signal['trade_direction'], 'stop_loss': trade_signal['stop_loss'], 'take_profit': tp_price,
                            'quantity': quantity, 'status': 'ACTIVE',
                            'levels_info': levels_str,
                            'level_broken': trade_signal.get('level_broken', 'N/A'),
                            'time_at_break': trade_signal['break_bar'].name,
                            'time_at_retest': trade_signal['entry_bar'].name
                        }
                        state['daily_trade_status']['trade_taken'] = True
                        self.logger.info(f"  -> [{fmt_ts(timestamp)}] TRADE OPEN: {trade_signal['trade_direction']} {quantity} {symbol} @ {trade_signal['entry_price']:.2f}, SL: {trade_signal['stop_loss']:.2f}, TP: {tp_price:.2f}")
                    else:
                        self.logger.info(f"Trade for {symbol} aborted due to zero position size. Resetting.")
                        logic_instance.reset_state()
            elif logic_instance.state == 'IN_TRADE':
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
                    self._close_trade_and_reset_state(state, trade, latest_bar, exit_reason)
                    continue

        # --- End of Day Position Management ---
        for symbol in self.symbols:
            state = self.symbol_states[symbol]
            if state['logic'].state == 'IN_TRADE' and state['active_trade']:
                trade = state['active_trade']
                symbol_data = combined_day_data_resampled[combined_day_data_resampled['symbol'] == symbol]
                if not symbol_data.empty:
                    last_bar_of_day = symbol_data.iloc[-1]
                    self._close_trade_and_reset_state(state, trade, last_bar_of_day, 'EOD')
                    continue


    def _close_trade_and_reset_state(self, state, trade, exit_bar, exit_reason):
        """
        A unified method to close a trade, calculate PnL correctly, record the trade,
        log the details, and reset the symbol's state machine.
        """
        symbol = trade['symbol']
        
        # The exit price is determined by the trigger (SL/TP) or the close of the exit bar.
        if exit_reason == 'STOP_LOSS':
            exit_price = trade['stop_loss']
        elif exit_reason == 'TAKE_PROFIT':
            exit_price = trade['take_profit']
        else: # EOD or other reasons
            exit_price = exit_bar['close']

        # Correctly calculate PnL in points and then in dollars
        pnl_points = (exit_price - trade['entry_price']) if trade['side'] == 'BUY' else (trade['entry_price'] - exit_price)
        pnl_dollars = pnl_points * trade['quantity'] * market_config.DOLLAR_PER_POINT[symbol]
        
        # Update master balance
        self.balance += pnl_dollars

        # Update the trade dictionary with all exit details
        trade.update({
            'exit_time': exit_bar.name,
            'exit_price': exit_price,
            'pnl_points': pnl_points,
            'pnl_dollars': pnl_dollars,
            'status': 'CLOSED',
            'reason_for_exit': exit_reason,
            'result': 'WIN' if pnl_dollars > 0 else 'LOSS'
        })

        # Record the completed trade for final statistics
        self.trades.append(trade)

        # Log the closure with comprehensive details
        self.logger.info(
            f"  -> [{fmt_ts(exit_bar.name)}] TRADE CLOSED: {trade['side']} {trade['quantity']} {symbol} @ {exit_price:.2f} "
            f"for PnL ${pnl_dollars:,.2f}. Reason: {exit_reason}. New Balance: ${self.balance:,.2f}"
        )

        # Reset the state for the symbol to prepare for the next trade
        state['active_trade'] = None
        state['logic'].reset_state()

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
    symbols_to_test = ['MNQ', 'MES']
    initial_capital = 2000.0

    # --- Run the backtest ---
    backtester = BacktesterProjectX(
        start_date=start_date,
        end_date=end_date,
        symbols=symbols_to_test,
        initial_balance=initial_capital
    )
    backtester.run()
