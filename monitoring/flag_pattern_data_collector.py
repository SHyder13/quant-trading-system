import pandas as pd
from config import main_config
from execution.broker_interface import BrokerInterface
from data.market_data_fetcher import MarketDataFetcher

def run_test():
    """Tests the new fetch_historical_range function."""
    print("--- Starting Data Fetch Test ---")

    # 1. Authenticate to get a session token
    broker = BrokerInterface(
        username=main_config.USERNAME,
        api_key=main_config.API_KEY,
        account_name=main_config.ACCOUNT_NAME
    )
    if not broker.session_token:
        print("Authentication failed. Cannot proceed with test.")
        return

    # 2. Initialize the fetcher
    fetcher = MarketDataFetcher(session_token=broker.session_token)

    # 3. Define parameters for the fetch
    symbol = 'MNQ'
    timeframe = '2m'
    start_time = '2025-06-24T11:06:00'
    end_time = '2025-06-24T11:24:00'

    # 4. Fetch the data using the new function
    fetched_df = fetcher.fetch_historical_range(symbol, timeframe, start_time, end_time)

    # 5. Create a DataFrame from the user-provided data for comparison
    user_data = {
        'timestamp': [
            '2025-06-24 11:06:00', '2025-06-24 11:08:00', '2025-06-24 11:10:00',
            '2025-06-24 11:12:00', '2025-06-24 11:14:00', '2025-06-24 11:16:00',
            '2025-06-24 11:18:00', '2025-06-24 11:20:00', '2025-06-24 11:22:00',
            '2025-06-24 11:24:00'
        ],
        'open': [22341.25, 22344, 22342.25, 22351, 22354, 22354.5, 22354, 22349.5, 22351.5, 22369.5],
        'high': [22360, 22349.25, 22355.75, 22356.75, 22358, 22356.5, 22355.75, 22356, 22372, 22370.25],
        'low': [22319.5, 22335.25, 22341.25, 22350.75, 22352, 22347.75, 22348.75, 22346.75, 22351, 22362.5],
        'close': [22343.25, 22342, 22351, 22354, 22354.5, 22354.25, 22350, 22351.25, 22369.25, 22367.5]
    }
    user_df = pd.DataFrame(user_data)
    user_df['timestamp'] = pd.to_datetime(user_df['timestamp'])
    # FIX: Localize the timestamp to ET to match the fetched data's index
    user_df['timestamp'] = user_df['timestamp'].dt.tz_localize('America/New_York')
    user_df.set_index('timestamp', inplace=True)

    # 6. Print both DataFrames for verification
    print("\n--- Fetched Data from API ---")
    if fetched_df is not None:
        print(fetched_df[['open', 'high', 'low', 'close']])
    else:
        print("No data was fetched.")

    print("\n--- Your Provided Data (Timezone Corrected) ---")
    print(user_df)

    # 7. Compare the dataframes
    if fetched_df is not None:
        # Comparing specific columns as volume might differ
        cols_to_compare = ['open', 'high', 'low', 'close']
        # Round to 2 decimal places to avoid floating point issues
        fetched_comp = fetched_df[cols_to_compare].round(2)
        user_comp = user_df[cols_to_compare].round(2)

        if fetched_comp.equals(user_comp):
            print("\n[SUCCESS] The fetched data perfectly matches your provided data.")
        else:
            print("\n[FAILURE] The fetched data does not match your provided data.")
            # Show the difference
            diff = fetched_comp.compare(user_comp)
            print("\n--- Differences ---")
            print(diff)

if __name__ == '__main__':
    run_test()