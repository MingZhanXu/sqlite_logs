import functools
import datetime
import traceback
import sqlite3
import os
import atexit
import time

# 設定單個資料庫大小上限為 100 MB
MAX_DB_SIZE = 100 * 1024 * 1024


class SQLiteLog:
    def __init__(
        self,
        db_folder="log",
        wal=True,
        max_db_size=MAX_DB_SIZE,
    ):
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
        self.db_size = 0
        self.db_name = os.path.join(db_folder, "log")
        self.wal = wal
        self.MAX_DB_SIZE = max_db_size
        self.current_db = self.get_last_log()
        self.conn = sqlite3.connect(self.current_db)
        self.cursor = self.conn.cursor()
        self.create_table()

        atexit.register(self.close)

    def get_last_log(self):
        """
        獲取最新的 log 檔案
        """
        db_index = 1
        while os.path.exists(f"{self.db_name}_{db_index}.db"):
            db_index += 1
        return f"{self.db_name}_{db_index}.db"

    def check_and_switch_db(self):
        """
        檢查 log 檔案大小是否超過最大限制，如果超過，則切換至下一個 log 檔案
        """
        if self.db_size > self.MAX_DB_SIZE:
            db_file = self.current_db
            self.db_size = os.path.getsize(db_file)
            if self.db_size > self.MAX_DB_SIZE:
                self.current_db = self.get_last_log()
                self.conn.close()
                self.conn = sqlite3.connect(self.current_db)
                self.cursor = self.conn.cursor()
                self.create_table()

    def create_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                type TEXT,
                line_number INTEGER,
                function_name TEXT,
                args TEXT,
                kwargs TEXT,
                message TEXT,
                function_time REAL,
                traceback TEXT
            )
            """
        )
        if self.wal:
            self.cursor.execute("PRAGMA journal_mode=WAL")
            self.conn.commit()
        self.conn.commit()
        self.check_and_switch_db()

    def log_to_db(self, log_type, messages):
        self.check_and_switch_db()
        timestamp = datetime.datetime.now().isoformat()
        (
            line_number,
            function_name,
            args,
            kwargs,
            message,
            function_time,
            traceback_str,
        ) = messages
        self.cursor.execute(
            """
            INSERT INTO logs (timestamp, type, line_number, function_name, args, kwargs, message, function_time, traceback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                log_type,
                line_number,
                function_name,
                args,
                kwargs,
                message,
                function_time,
                traceback_str,
            ),
        )
        self.conn.commit()
        self.db_size += len(log_type) + len(str(messages)) + 100

    def try_except(self, func=None, *, error_return=None):
        """
        tre_except 裝飾器，用於捕獲函數執行過程中的異常，並將異常信息記錄到數據庫中
        error_return: 當函數執行出現異常時，返回的默認值，可使用此參數來自定義異常時的返回值
        """
        if func is None:
            return functools.partial(self.try_except, error_return=error_return)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            stack = traceback.extract_stack()[-2]
            line_number = stack.lineno
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                function_time = end_time - start_time
                message = f"result: {repr(result)}"
                messages = (
                    line_number,
                    func.__name__,
                    str(args),
                    str(kwargs),
                    message,
                    function_time,
                    None,
                )
                self.log_to_db("LOG", messages)
                return result
            except Exception as e:
                end_time = time.time()
                function_time = end_time - start_time
                messages = (
                    line_number,
                    func.__name__,
                    str(args),
                    str(kwargs),
                    str(e),
                    function_time,
                    traceback.format_exc(),
                )
                self.log_to_db("ERROR", messages)
                return error_return

        return wrapper

    def close(self):
        self.conn.commit()
        self.conn.close()


class ReadLog:
    def __init__(self, db_folder, db_index=1):
        self.db_name = os.path.join(db_folder, "log")
        self.db_index = db_index
        if not os.path.exists(f"{self.db_name}_{db_index}.db"):
            print(f"{self.db_name}_{db_index}.db not exists")
            exit(-1)

        try:
            self.conn = sqlite3.connect(f"{self.db_name}_{db_index}.db")
            atexit.register(self.close)
        except sqlite3.OperationalError as e:
            print(f"Connect to {self.db_name}_{db_index}.db failed")
            print(f"Error: {e}")
            exit(-1)

    def get_logs(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM logs WHERE type = 'LOG'
                """
            )
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"get_logs from {self.db_name}_{self.db_index}.db failed")
            print(f"Error: {e}")
            exit(-1)

    def get_error(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM logs WhERE type = 'ERROR'
                """
            )
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"get_error from {self.db_name}_{self.db_index}.db failed")
            print(f"Error: {e}")
            exit(-1)

    def get_info(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                PRAGMA table_info(logs)
                """
            )
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"get_info from {self.db_name}_{self.db_index}.db failed")
            print(f"Error: {e}")
            exit(-1)

    def next_db(self):
        try:
            self.conn.close()
            self.conn = sqlite3.connect(f"{self.db_name}_{self.db_index}.db")
        except sqlite3.OperationalError as e:
            print(f"Connect to {self.db_name}_{self.db_index}.db failed")
            print(f"Error: {e}")
            exit(-1)

    def close(self):
        try:
            self.conn.close()
        except sqlite3.OperationalError as e:
            print(f"Close {self.db_name}_{self.db_index}.db failed")


if __name__ == "__main__":
    from tqdm import tqdm

    db_folder = os.path.join("logs", "test")
    logger = SQLiteLog(db_folder=db_folder)

    # 範例：如何傳入 except 執行函數，也可傳入參數
    def error():
        return "error"

    @logger.try_except(error_return=error())
    def delay():
        time.sleep(1)
        raise

    print(delay())

    # 範例：如何使用裝飾器
    @logger.try_except
    def division(a, b):
        return a / b

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
    for d in data:
        print(d)

    for d in error_data:
        print(d)

    print()
    for key, value in error_data[0].items():
        if key == "traceback":
            value = value.replace("\\\\", "\\")
        print(f"{key}: {value}")
