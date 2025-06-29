import loguru

def setup_logger(log_file='trading_system.log'):
    """Configures and returns the Loguru logger."""
    loguru.logger.remove()
    loguru.logger.add(log_file, rotation="10 MB", enqueue=True, format="{time} {level} {message}")
    return loguru.logger

# Initialize the logger once and make it available for import
SYSTEM_LOGGER = setup_logger()

