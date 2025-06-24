class ExecutionTracker:
    def __init__(self):
        pass

    def track_slippage(self, expected_price, actual_price):
        slippage = actual_price - expected_price
        print(f"Slippage: {slippage}")
        return slippage

    def track_latency(self, order_time, fill_time):
        latency = fill_time - order_time
        print(f"Latency: {latency}")
        return latency
