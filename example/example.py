from src.logger import (
    Logger,
    LoggerInfo,
    LoggerTagValue,
    SQLiteLog,
)

if __name__ == "__main__":
    config: LoggerTagValue = {"cpu": False, "level": "DEBUG"}
    logger_info = LoggerInfo(config)
    sqlite_log = SQLiteLog(db_name="test")
    logger = Logger(logger_info=logger_info, logger_output=sqlite_log)

    @logger.try_except(error_return="error")
    def test(a, b):
        return a / b

    for i in range(10):
        test(i, i - 1)
