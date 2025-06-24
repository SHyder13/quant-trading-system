# The dollar value of a single-point move for each contract.
DOLLAR_PER_POINT = {
    'MNQ': 2,    # Micro E-mini Nasdaq-100
    'MES': 5,    # Micro E-mini S&P 500
    'M2K': 5     # Micro E-mini Russell 2000
}

# Trading session times in America/New_York timezone.
TRADING_SESSIONS = {
    'premarket': {'start': '04:00', 'end': '09:29'},
    'regular': {'start': '09:30', 'end': '16:00'}
}
MARKET_HOLIDAYS = ['2024-12-25', '2024-01-01']
