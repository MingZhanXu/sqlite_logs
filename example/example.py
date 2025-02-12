import os
import time
from src.sqlite_log import SQLiteLog, ReadLog, LoggerField
from tqdm import tqdm

if __name__ == "__main__":
    db_folder = os.path.join("logs", "test")
    logger_field = LoggerField(is_thread_info=False)
    logger = SQLiteLog(db_folder=db_folder, logger_table_info=logger_field.info())

    # 範例：如何傳入 except 執行函數，也可傳入參數
    def error():
        return "error"

    @logger.try_except(error_return=error())
    def delay():
        time.sleep(1)
        raise

    print(delay())

    # 範例：如何使用裝飾器
    @logger.try_except()
    def tag_division(a, b, c=3):
        """#tag:try #gpu:false #cpu:false #memory:false #extra_info:hello"""
        return {"a": (a / b), "b": c}

    tag_division(99, 99)

    @logger.try_except
    def division(a, b, c=3):
        return {"a": (a / b), "b": c}

    division(1, 2, c=4)
    # 執行多次 division 函數，並捕獲異常
    for _ in tqdm(range(50)):
        division(1, 0)
        division(1, 2)

    # 範例：如何讀取數據庫中的 log 及 error 訊息 (格式化版本)
    read_log = ReadLog(db_folder=db_folder)
    data = read_log.get_logs()
    error_data = read_log.get_error()
    info = read_log.get_info()
    info = [name[1] for name in info]
    data = [{item: d[i] for i, item in enumerate(info)} for d in data]
    error_data = [{item: d[i] for i, item in enumerate(info)} for d in error_data]
    # for d in data:
    #     print(d)
    #
    # for d in error_data:
    #     print(d)

    print(f"sucess:{len(data)}, error:{len(error_data)}")
    for key, value in error_data[0].items():
        if key == "traceback":
            value = value.replace("\\\\", "\\")
        print(f"{key}: {value}")
    print()
    for key, value in data[0].items():
        print(f"{key}: {value}")
