# --- Main System Configuration ---

# --- API Credentials ---
# IMPORTANT: Replace these placeholder values with your actual credentials.
USERNAME = "shazaibhyder"
API_KEY = "ok2SzGzmgTEr0cgqjGAEgLlCfNvF3Ct4w0P6yjYFp/s="

# Databento credentials / file locations
# --------------------------------------
# `DATABENTO_API_KEY` is optional when reading from local .dbn files but will be
# required if you decide to fetch data directly from Databento's servers in the
# future.
DATABENTO_API_KEY = "Ydb-xHkAcaAf6wGSMtRLWrtdcF4uKktmK"

# Map each traded symbol to the absolute path of its Databento *.dbn* file.
# Example:
#   {
#       "MES": "/path/to/mes_ohlcv_1m.dbn",
#       "MNQ": "/path/to/mnq_ohlcv_1m.dbn",
#   }
DATABENTO_FILE_PATHS = {
    "MES": "/Users/shazaibhyder/CascadeProjects/quant_trading_system/data/glbx-mdp3-20200628-20250627.ohlcv-1m.dbn",
    "MNQ": "/Users/shazaibhyder/CascadeProjects/quant_trading_system/data/glbx-mdp3-20200628-20250627.ohlcv-1m.dbn",
}

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


