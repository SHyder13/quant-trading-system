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
from data.market_data_fetcher import MarketDataFetcher
from data.level_calculator import LevelCalculator
from data.ema_guides import EMAGuides

from strategy.break_detector import BreakDetector
from strategy.retest_detector import RetestDetector
from strategy.signal_generator import SignalGenerator
from strategy.pattern_validator import PatternValidator

from risk.position_sizer import PositionSizer
from risk.stop_loss_manager import StopLossManager
from risk.take_profit_manager import TakeProfitManager

from shared_components import SYSTEM_LOGGER
from execution.broker_interface import BrokerInterface

class Backtester:
    def __init__(self, start_date, end_date, symbols, initial_balance):
        self.start_date = start_date
        self.end_date = end_date
        self.symbols = symbols
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.logger = SYSTEM_LOGGER

        # Initialize components
        self.broker = BrokerInterface(main_config.USERNAME, main_config.API_KEY, main_config.ACCOUNT_NAME)
        self.market_fetcher = MarketDataFetcher(self.broker.session_token)
        self.level_calculator = LevelCalculator()
        self.ema_calculator = EMAGuides()
        self.stop_loss_manager = StopLossManager(risk_config)
        self.take_profit_manager = TakeProfitManager(risk_config)
        self.position_sizer = PositionSizer(risk_config)

        # Trading session times
        self.morning_start = datetime.strptime(strategy_config.MORNING_SESSION_START, '%H:%M').time()
        self.morning_end = datetime.strptime(strategy_config.MORNING_SESSION_END, '%H:%M').time()
        self.afternoon_start = datetime.strptime(strategy_config.AFTERNOON_SESSION_START, '%H:%M').time()
        self.afternoon_end = datetime.strptime(strategy_config.AFTERNOON_SESSION_END, '%H:%M').time()

        # Per-symbol components
        self.symbol_states = {}
        for symbol in self.symbols:
            break_detector = BreakDetector(strategy_config, symbol, self.logger)
            retest_detector = RetestDetector(strategy_config, symbol)
            self.symbol_states[symbol] = {
                'break_detector': break_detector,
                'retest_detector': retest_detector,
                'signal_generator': SignalGenerator(break_detector, retest_detector),
                'pattern_validator': PatternValidator(),
                'stop_loss_manager': StopLossManager(risk_config),
                'active_trade': None,
                'levels': {},
            }

        self.trades = []
        self.all_data = {}

    def run(self):
        """Main method to run the backtest."""
        print(f"--- Starting Backtest for {self.symbols} from {self.start_date} to {self.end_date} ---")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")

        # Fetch all historical data for the period
        for symbol in self.symbols:
            fetch_start_date = self.start_date - timedelta(days=5)
            start_date_str = fetch_start_date.isoformat() + 'Z'
            end_date_str = self.end_date.isoformat() + 'Z'
            data = self.market_fetcher.fetch_historical_data(
                symbol,
                start_date_str=start_date_str,
                end_date_str=end_date_str,
                timeframe=main_config.TIMEFRAME
            )
            if data is None or data.empty:
                print(f"Could not fetch data for {symbol}. Aborting.")
                return
            self.all_data[symbol] = data

        # Loop through each day in the specified date range
        for current_date in pd.date_range(self.start_date, self.end_date):
            self.run_day_simulation(current_date)



    def run_day_simulation(self, current_date):
        """Simulates trading for a single day for all symbols."""
        print(f"\n--- Simulating Day: {current_date.strftime('%Y-%m-%d')} ---")

        # 1. Calculate Levels and get combined data for the day
        daily_data_frames = []
        for symbol in self.symbols:
            # Ensure we only use data prior to the current simulation day for level calculation
            historical_data_for_levels = self.all_data[symbol][self.all_data[symbol].index.date < current_date.date()]
            if historical_data_for_levels.empty:
                print(f"Not enough historical data to calculate levels for {symbol} on {current_date.date()}. Skipping day.")
                continue

            # Pass the current simulation date to the level calculator
            levels = self.level_calculator.calculate_all_levels(historical_data_for_levels, current_date)
            if not all(levels.values()):
                print(f"Could not calculate all key levels for {symbol} on {current_date.date()}. Skipping day.")
                continue
            self.symbol_states[symbol]['levels'] = levels

            day_data = self.all_data[symbol][self.all_data[symbol].index.date == current_date.date()].copy()
            day_data['symbol'] = symbol
            daily_data_frames.append(day_data)

            # Reset strategy state at the start of each day
            self.symbol_states[symbol]['signal_generator'].reset()
            self.symbol_states[symbol]['active_trade'] = None

        if not daily_data_frames:
            print("No data for any symbol on this day.")
            return

        # Combine and sort all data for the day by time
        combined_day_data = pd.concat(daily_data_frames).sort_index()

        # 3. Loop through each bar of the day
        for timestamp, bar_data in combined_day_data.iterrows():
            symbol = bar_data['symbol']
            state = self.symbol_states[symbol]

            historical_view = self.all_data[symbol][self.all_data[symbol].index <= timestamp]
            latest_bar = historical_view.iloc[-1]
            latest_emas = self.ema_calculator.get_latest_ema_values(historical_view)

            if not latest_emas:
                continue

            # If not in a trade, check for entry signals
            if not state['active_trade']:
                # Check if we are within trading hours to look for a new trade
                current_time = timestamp.time()
                is_morning_session = self.morning_start <= current_time <= self.morning_end
                is_afternoon_session = self.afternoon_start <= current_time <= self.afternoon_end

                if not (is_morning_session or is_afternoon_session):
                    continue # Skip signal processing if outside trading hours

                signal_info, pivot_candle, rejection_candle, breakout_candle, confluence_type = state['signal_generator'].process_bar(
                    latest_bar, state['levels'], latest_emas
                )

                # If a signal is generated, proceed with validation and trade execution
                if signal_info['side'] != 'NONE':
                    # Context for validation and execution
                    validation_context = {
                        'symbol': symbol,
                        'breakout_candle': breakout_candle,
                        'rejection_candle': rejection_candle, # The candle that confirms the rejection
                        'latest_bar': latest_bar,
                        'latest_emas': latest_emas
                    }

                    # Validate the signal before proceeding
                    is_valid_signal = state['pattern_validator'].validate_signal(signal_info['side'], validation_context)
                    if not is_valid_signal:
                        print(f"Signal for {symbol} was invalidated by PatternValidator.")
                        continue

                    # Determine if this is a high-conviction trade
                    is_high_conviction = (confluence_type == '13_EMA')

                    # Calculate Stop Loss using the PIVOT candle, which represents the true extreme of the pullback
                    stop_loss_price = state['stop_loss_manager'].calculate_stop_from_candle(
                        signal_info['side'], pivot_candle, symbol
                    )
                    if stop_loss_price is None:
                        continue

                    # Determine if the trade has EMA confluence, making it high-conviction
                    entry_price = latest_bar['close']
                    take_profit_price = self.take_profit_manager.set_profit_target(entry_price, stop_loss_price, signal_info['side'])
                    
                    quantity = self.position_sizer.calculate_size(
                        self.balance, entry_price, stop_loss_price, symbol, is_high_conviction=is_high_conviction
                    )
                    if quantity == 0:
                        print(f"     - [{timestamp.time()}] Skipping trade for {symbol}: Position size is zero.")
                        continue

                    state['active_trade'] = {
                        'symbol': symbol, 'entry_time': latest_bar.name, 'entry_price': entry_price,
                        'side': signal_info['side'], 'stop_loss': stop_loss_price, 'take_profit': take_profit_price,
                        'quantity': quantity, 'status': 'OPEN'
                    }
                    print(f"  -> [{timestamp.time()}] {symbol} TRADE OPEN: {signal_info['side']} {quantity} @ {entry_price:.2f}")

            # If in a trade, check for exit conditions
            else:
                active_trade = state['active_trade']
                if active_trade['side'] == 'BUY':
                    if latest_bar['high'] >= active_trade['take_profit']:
                        self.close_trade(active_trade, latest_bar, 'TP')
                        state['active_trade'] = None
                    elif latest_bar['low'] <= active_trade['stop_loss']:
                        self.close_trade(active_trade, latest_bar, 'SL')
                        state['active_trade'] = None
                elif active_trade['side'] == 'SELL':
                    if latest_bar['low'] <= active_trade['take_profit']:
                        self.close_trade(active_trade, latest_bar, 'TP')
                        state['active_trade'] = None
                    elif latest_bar['high'] >= active_trade['stop_loss']:
                        self.close_trade(active_trade, latest_bar, 'SL')
                        state['active_trade'] = None

    def close_trade(self, trade, exit_bar, exit_reason):
        """Records the result of a closed trade and updates balance."""
        exit_price = trade['take_profit'] if exit_reason == 'TP' else trade['stop_loss']
        pnl_points = exit_price - trade['entry_price'] if trade['side'] == 'BUY' else trade['entry_price'] - exit_price
        
        dollar_per_point = market_config.DOLLAR_PER_POINT[trade['symbol']]
        pnl_dollars = pnl_points * dollar_per_point * trade['quantity']

        self.balance += pnl_dollars
        trade.update({
            'exit_time': exit_bar.name, 'exit_price': exit_price, 'exit_reason': exit_reason,
            'status': 'CLOSED', 'pnl_points': pnl_points, 'pnl_dollars': pnl_dollars,
            'result': 'WIN' if pnl_dollars > 0 else 'LOSS'
        })
        self.trades.append(trade)
        print(f"     - [{exit_bar.name.time()}] {trade['symbol']} Trade Closed: {trade['result']} by {exit_reason}. P/L: ${pnl_dollars:,.2f}. New Balance: ${self.balance:,.2f}")

    def shutdown(self):
        """Gracefully shuts down the backtester, prints results, and closes the logger."""
        print("--- Shutting down backtester --- ")
        SYSTEM_LOGGER.remove() # Ensure all logs are written
        self.print_results()

    def print_results(self):
        """Prints the final backtest results."""
        print("\n--- Backtest Results ---")
        if not self.trades:
            print("No trades were executed.")
            return

        total_trades = len(self.trades)
        wins = len([t for t in self.trades if t['result'] == 'WIN'])
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        total_pnl_dollars = sum(t['pnl_dollars'] for t in self.trades)
        total_pnl_points = sum(t['pnl_points'] for t in self.trades)

        print(f"Starting Balance:   ${self.initial_balance:,.2f}")
        print(f"Ending Balance:     ${self.balance:,.2f}")
        print(f"Total P/L:          ${total_pnl_dollars:,.2f}")
        print(f"Total Trades:       {total_trades}")
        print(f"Wins:               {wins}")
        print(f"Losses:             {losses}")
        print(f"Win Rate:           {win_rate:.2f}%")
        print(f"Total P/L (Points): {total_pnl_points:.2f}")

if __name__ == '__main__':
    backtest_start_date = datetime(2025, 6, 1)
    backtest_end_date = datetime(2025, 6, 30)
    symbols_to_test = ['MNQ', 'MES']
    account_balance = 2000.0

    backtester = Backtester(
        start_date=backtest_start_date,
        end_date=backtest_end_date,
        symbols=symbols_to_test,
        initial_balance=account_balance
    )
    backtester.run()
    backtester.shutdown()
