from src.sqlite_log import Logger
from src.sqlite_log import SQLiteLog, LoggerInfo, LoggerTagValue

if __name__ == "__main__":
    config = {"cpu": False, "level": "DEBUG"}
    logger_info = LoggerInfo(config)
    sqlite_log = SQLiteLog
    logger = Logger(logger_info=logger_info, logger_output=sqlite_log)

    @logger.try_except(error_return="error")
    def test(a, b):
        return a / b

    for i in range(10):
        test(i, i - 1)
