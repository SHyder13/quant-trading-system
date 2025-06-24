# --- Main System Configuration ---

# --- API Credentials ---
# IMPORTANT: Replace these placeholder values with your actual credentials.
USERNAME = "shazaibhyder"
API_KEY = "ok2SzGzmgTEr0cgqjGAEgLlCfNvF3Ct4w0P6yjYFp/s="

# The specific account name to be used for trading.
ACCOUNT_NAME = "PRAC-V2-31472-54313480"

# List of symbols to be traded by the system.
# The system will initialize and run a separate strategy instance for each symbol.
SYMBOLS = ["MNQ", "MES"]

# The timeframe to be used for fetching market data and running the strategy.
# Examples: "1m", "2m", "5m", "1D"
TIMEFRAME = "2m"

# --- Operational Mode ---

# Set to True to use mock data and simulated brokerage interactions.
# Set to False for live trading with real market data and broker execution.
SIMULATION_MODE = False


