import functools
import datetime
import traceback
import sqlite3
import os
import atexit
import threading
import platform
import getpass
import socket
import subprocess

from typing import Type
from dataclasses import dataclass

# 設定單個資料庫大小上限為 100 MB
MAX_DB_SIZE = 100 * 1024 * 1024


def get_computer_name():
    system_name = platform.system()

    # Windows
    if system_name == "Windows":
        return os.environ.get("COMPUTERNAME", socket.gethostname())

    # macOS
    elif system_name == "Darwin":
        try:
            return (
                subprocess.check_output(["scutil", "--get", "ComputerName"])
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            return socket.gethostname()

    # Linux
    elif system_name == "Linux":
        try:
            return (
                subprocess.check_output(["hostnamectl", "--static"])
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            return socket.gethostname()

    # 其他系統（預設使用 socket.gethostname()）
    return socket.gethostname()


@dataclass
class SQLType:
    """SQLite 與 Python 資料型態對應表"""

    sql_type: str
    py_type: Type


@dataclass
class LoggerType:
    """Logger 資料庫表格欄位名稱與資料型態對應表"""

    field_name: str
    sql_type: SQLType


# log 資料庫表格欄位名稱與資料型態
LOGER_TABE_INFO = [
    LoggerType("host_inof", SQLType("TEXT", str)),
    LoggerType("timestamp", SQLType("TEXT", str)),
    LoggerType("type", SQLType("TEXT", str)),
    LoggerType("function_file_name", SQLType("TEXT", str)),
    LoggerType("function_line_number", SQLType("INTEGER", int)),
    LoggerType("function_name", SQLType("TEXT", str)),
    LoggerType("args", SQLType("TEXT", str)),
    LoggerType("kwargs", SQLType("TEXT", str)),
    LoggerType("thread_name", SQLType("TEXT", str)),
    LoggerType("thread_id", SQLType("INTEGER", int)),
    LoggerType("pid", SQLType("INTEGER", int)),
    LoggerType("message", SQLType("TEXT", str)),
    LoggerType("extra_info", SQLType("TEXT", str)),
    LoggerType("function_time", SQLType("REAL", float)),
    LoggerType("traceback", SQLType("TEXT", str)),
]


class Logger:
    def __init__(
        self,
        log_type,
        function_file_name,
        function_line_number,
        function_name,
        args,
        kwargs,
        message,
        function_time,
        traceback,
    ):
        self.timestamp = datetime.datetime.now().isoformat()
        self.log_type = log_type
        self.function_file_name = function_file_name
        self.function_line_number = function_line_number
        self.function_name = function_name
        self.args = args
        self.kwargs = kwargs
        self.message = message
        self.function_time = function_time
        self.traceback = traceback


class SQLiteLog:
    def __init__(
        self,
        db_folder="log",
        wal=True,
        max_db_size=MAX_DB_SIZE,
    ):
        self.computer_name = get_computer_name()
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
        self.field_name = [field.field_name for field in LOGER_TABE_INFO]
        self.field_type = [field.sql_type.sql_type for field in LOGER_TABE_INFO]
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {", ".join([f"{field} {field_type}" for field, field_type in zip(self.field_name, self.field_type)])}
            )
            """
        )
        if self.wal:
            self.cursor.execute("PRAGMA journal_mode=WAL")
            self.conn.commit()
        self.conn.commit()
        self.check_and_switch_db()

    def log_to_db(self, messages):
        self.check_and_switch_db()
        field_str = f"{', '.join(self.field_name)}"
        input_datas = f"{', '.join(['?' for _ in range(len(self.field_name))])}"
        self.cursor.execute(
            f"""
            INSERT INTO logs ({field_str}) VALUES ({input_datas})
            """,
            messages,
        )
        self.conn.commit()
        self.db_size += len(str(messages)) + 100

    def try_except(
        self, func=None, *, success_type="LOG", extra_info="", error_return=None
    ):
        """
        tre_except 裝飾器，用於捕獲函數執行過程中的異常，並將異常信息記錄到數據庫中
        error_return: 當函數執行出現異常時，返回的默認值，可使用此參數來自定義異常時的返回值
        """
        if func is None:
            return functools.partial(self.try_except, error_return=error_return)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.datetime.now()
            start_time_timestamp = start_time.timestamp()
            start_time = start_time.isoformat()

            host_info = platform.uname()
            host_info = (
                f"Computer  : {self.computer_name}\n"
                f"User      : {getpass.getuser()}\n"
                f"System    : {host_info.system}\n"
                f"Node      : {host_info.node}\n"
                f"Release   : {host_info.release}\n"
                f"Version   : {host_info.version}\n"
                f"Machine   : {host_info.machine}"
            )

            stack = traceback.extract_stack()[-2]
            line_number = stack.lineno
            file_name = stack.filename
            name = func.__name__
            args_str = str(args)
            kwargs_str = str(kwargs)

            current_thread = threading.current_thread()
            thread_name = current_thread.name
            thread_id = current_thread.ident
            pid = os.getpid()
            messages = [
                file_name,
                line_number,
                name,
                args_str,
                kwargs_str,
                thread_name,
                thread_id,
                pid,
            ]
            try:
                result = func(*args, **kwargs)
                log_type = success_type
                end_time_timestamp = datetime.datetime.now().timestamp()
                function_time = end_time_timestamp - start_time_timestamp
                message = f"result: {repr(result)}"
                messages = (
                    [host_info, start_time, log_type]
                    + messages
                    + [message, extra_info, function_time, None]
                )
                self.log_to_db(messages)
                return result
            except Exception as e:
                log_type = "ERROR"
                end_time_timestamp = datetime.datetime.now().timestamp()
                function_time = end_time_timestamp - start_time_timestamp
                error_msg = f"{e.__class__.__name__}: {str(e)}"
                messages = (
                    [host_info, start_time, log_type]
                    + messages
                    + [error_msg, extra_info, function_time, traceback.format_exc()]
                )
                self.log_to_db(messages)
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

    def get_data(self, type):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM logs where type = ?
                """,
                (type,),
            )
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"get_data from {self.db_name}_{self.db_index}.db failed")
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
        """
        獲取 logs 表格的資訊
        """
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
        """
        獲取下一個 log 檔案
        """
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
