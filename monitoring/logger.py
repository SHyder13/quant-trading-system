from loguru import logger

class Logger:
    def __init__(self, log_file='trading_system.log'):
        logger.add(log_file, rotation="10 MB")
        self.logger = logger

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)
