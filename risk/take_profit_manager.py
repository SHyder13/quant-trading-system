class TakeProfitManager:
    def __init__(self, risk_config):
        self.risk_config = risk_config

    def set_profit_target(self, entry_price, stop_loss_price, signal_direction):
        print("Setting profit target...")
        # Example: 2:1 risk/reward ratio
        risk_amount = abs(entry_price - stop_loss_price)
        if signal_direction == 'BUY':
            return entry_price + (risk_amount * 2)
        else:
            return entry_price - (risk_amount * 2)

    def check_ema_trail_stop(self, latest_bar, position_side, latest_emas):
        """
        Checks if the price has closed across the 48 EMA, triggering a trailing stop exit.

        Args:
            latest_bar (pd.Series): The most recent data bar.
            position_side (str): 'BUY' or 'SELL'.
            latest_emas (dict): A dictionary with the latest EMA values.

        Returns:
            bool: True if the position should be exited, False otherwise.
        """
        ema_48 = latest_emas.get('ema_48')
        if not ema_48:
            return False # Not enough data

        close_price = latest_bar['close']
        should_exit = False

        if position_side == 'BUY' and close_price < ema_48:
            print(f"!!! EMA TRAIL STOP HIT for LONG: Price {close_price:.2f} closed below 48 EMA {ema_48:.2f} !!!")
            should_exit = True
        elif position_side == 'SELL' and close_price > ema_48:
            print(f"!!! EMA TRAIL STOP HIT for SHORT: Price {close_price:.2f} closed above 48 EMA {ema_48:.2f} !!!")
            should_exit = True

        return should_exit
