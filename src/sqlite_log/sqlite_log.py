import functools
import datetime
import traceback
import sqlite3
import os
import atexit
import threading
import getpass
import json
import re

from typing import List

from .sqlite_log_type import (
    LoggerType,
    SQL_TEXT,
    SQL_INTEGER,
    SQL_REAL,
)
from .get_system_info import get_computer_name, get_system_info_json, get_host_info

# 設定單個資料庫大小上限為 100 MB
MAX_DB_SIZE = 100 * 1024 * 1024

# 正則表達式"#*:* "
TAG_REGULAR = r"#\S+?:\S+"


# log 資料庫表格欄位名稱與資料型態
"""
LoggerType(field_name, SQLTyep)
SQLType(SQL_type, python_type)

base info: 基本資訊
    level: log 類型
        LOG: 正常 log
        NOTSET: 無設定
        TRACE: 追蹤
        DEBUG: 除錯
        INFO: 資訊
        WARNING: 警告
        ERROR: 錯誤
        CRITICAL: 致命錯誤
    timestamp: 時間戳
    message: log 訊息
system info: 系統資訊
    system_info: 系統資訊
        {
        "Computer_info":{
            computer_name: 電腦名稱,
            user_name: 使用者名稱,
            system_name: 系統名稱,
            system_version: 系統版本,
            system_release: 系統發行版本,
            system_machine: 系統機器,
            system_processor: 系統處理器
            }
        "CPU_info":{
            usage: CPU 使用率,
            physical_cores: CPU 實體核心數,
            logical_cores: CPU 邏輯核心數,
            current_frequency: 頻率,
            min_frequency: 最小頻率,
            max_frequency: 最大頻率,
            }
        "RAM_info":{
            total: 總記憶體,
            used: 使用記憶體,
            free: 空閒記憶體,
            percent: 記憶體使用率
            }
        "GPU_info":{
            id: GPU ID,
            name: GPU 名稱,
            memory_total: 總記憶體,
            memory_used: 使用記憶體,
            memory_free: 空閒記憶體,
            memory_percent: 記憶體使用率,
            temperature: 溫度,
            power: 功率,
            utilization: 使用率
            }
        }
    host_info: 主機資訊
function info: 函數資訊
    function_file_name: 函數所在檔案名稱
    function_line_number: 函數所在行數
    function_name: 函數名稱
    args: 函數參數
    kwargs: 函數關鍵字參數
    return_value: 函數返回值
    function_time: 函數執行時間
thread info: 執行緒資訊
    thread_name: 執行緒名稱
    thread_id: 執行緒 ID
    process_id: 行程的 PID
extra info: 額外資訊
    tag: log 標籤
    extra_info: 額外資訊
traceback: 追蹤錯誤
    exception_type: 錯誤類型
    traceback: 追蹤錯誤
"""
LOGGER_TABLE_INFO: List[LoggerType] = [
    LoggerType("system_info", SQL_TEXT),
    LoggerType("host_info", SQL_TEXT),
    LoggerType("timestamp", SQL_TEXT),
    LoggerType("level", SQL_TEXT),
    LoggerType("tag", SQL_TEXT),
    LoggerType("function_file_name", SQL_TEXT),
    LoggerType("function_line_number", SQL_INTEGER),
    LoggerType("function_name", SQL_TEXT),
    LoggerType("args", SQL_TEXT),
    LoggerType("kwargs", SQL_TEXT),
    LoggerType("thread_name", SQL_TEXT),
    LoggerType("thread_id", SQL_INTEGER),
    LoggerType("process_id", SQL_INTEGER),
    LoggerType("message", SQL_TEXT),
    LoggerType("extra_info", SQL_TEXT),
    LoggerType("function_time", SQL_REAL),
    LoggerType("traceback", SQL_TEXT),
]


class LoggerField:
    def __init__(
        self,
        is_system_info=True,
        is_host_info=True,
        is_tag=True,
        is_function_info=True,
        is_thread_info=True,
        is_traceback=True,
    ):
        self.__logger_table_info = LOGGER_TABLE_INFO.copy()
        remove_fields = set()
        if not is_system_info:
            remove_fields.add("system_info")
        if not is_host_info:
            remove_fields.add("host_info")
        if not is_tag:
            remove_fields.add("tag")
        if not is_function_info:
            remove_fields.add(
                (
                    "function_file_name",
                    "function_line_number",
                    "function_name",
                    "args",
                    "kwargs",
                )
            )
        if not is_thread_info:
            remove_fields.add(("thread_name", "thread_id", "process_id"))
        if not is_traceback:
            remove_fields.add("traceback")

        self.__logger_table_info = [
            field
            for field in self.__logger_table_info
            if field.field_name not in remove_fields
        ]

    def info(self):
        return self.__logger_table_info

    def field_name(self):
        field_name = [field.field_name for field in self.__logger_table_info]
        return field_name

    def value(self, default_info: dict):
        # base info
        log_type = default_info.get("log_type", "NO_TYPE")
        timestamp = default_info.get("timestamp", datetime.datetime.now().isoformat())
        log_message = default_info.get("log_message", None)
        # system info
        system_info = default_info.get("system_info", get_system_info_json())
        host_info = default_info.get("host_info", get_computer_name())
        # function info
        function_file_name = default_info.get("function_file_name", None)
        function_line_number = default_info.get("function_line_number", None)
        function_name = default_info.get("function_name", None)
        args = default_info.get("args", None)
        kwargs = default_info.get("kwargs", None)
        return_value = default_info.get("return_value", None)
        function_time = default_info.get("function_time", None)
        # thread info
        thread_name = default_info.get("thread_name", threading.current_thread().name)
        thread_id = default_info.get("thread_id", threading.current_thread().ident)
        process_id = default_info.get("process_id", os.getpid())
        # extra info
        tag = default_info.get("tag", None)
        extra_info = default_info.get("extra_info", None)
        # traceback
        exception_type = default_info.get("exception_type", None)
        traceback = default_info.get("traceback", None)
        values = {
            "base_info": [log_type, timestamp, log_message],
            "system_info": [system_info, host_info],
            "function_info": [
                function_file_name,
                function_line_number,
                function_name,
                args,
                kwargs,
                return_value,
                function_time,
            ],
            "thread_info": [thread_name, thread_id, process_id],
            "extra_info": [tag, extra_info],
            "traceback": [exception_type, traceback],
        }
        return values


class LoggerData:
    def __init__(
        self,
        logger_field: LoggerField,
        **kwargs,
    ):
        self.__logger_table_info = logger_field.info()

        for field in self.__logger_table_info:
            setattr(self, field.field_name, kwargs.get(field.field_name, None))

    def get_data(self):
        fields = {
            field.field_name: getattr(self, field.field_name)
            for field in self.__logger_table_info
        }
        return fields

    def __repr__(self):
        return f"LoggerData({self.get_data()})"


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
        logger_table_info=None,
    ):
        if logger_table_info is None:
            self.__LOGGER_TABLE_INFO = LOGGER_TABLE_INFO
        else:
            self.__LOGGER_TABLE_INFO = logger_table_info

        # 設定 logger 資料庫
        self.computer_name = get_computer_name()
        self.user_name = getpass.getuser()
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
        self.db_size = 0
        self.MAX_DB_SIZE = max_db_size
        self.db_name = os.path.join(db_folder, "log")
        self.wal = wal

        # 產生對應的 loggger 資料庫
        self.current_db = self.get_last_log()
        self.conn = sqlite3.connect(self.current_db)
        self.cursor = self.conn.cursor()
        self.create_table()

        # 註冊 python 退出時的函數
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
        """
        根據 Logger 資料庫表格欄位名稱與資料型態對應表建立 logs 表格
        """
        self.field_name = [field.field_name for field in self.__LOGGER_TABLE_INFO]
        self.field_type = [
            field.sql_type.sql_type for field in self.__LOGGER_TABLE_INFO
        ]
        sql_table_info = ", ".join(
            [
                f"{field_name} {field_type}"
                for field_name, field_type in zip(self.field_name, self.field_type)
            ]
        )
        sql = f"CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, {sql_table_info})"
        self.cursor.execute(sql)
        # 設定資料庫為可以同時讀寫
        if self.wal:
            self.cursor.execute("PRAGMA journal_mode=WAL")
            self.conn.commit()
        self.conn.commit()
        self.check_and_switch_db()

    def log_to_db(self):
        self.check_and_switch_db()
        field_str = f"{', '.join(self.field_name)}"
        input_datas = f"{', '.join(['?' for _ in range(len(self.field_name))])}"
        datas = [self.field_value.get(field, None) for field in self.field_name]
        sql = f"INSERT INTO logs ({field_str}) VALUES ({input_datas})"
        self.cursor.execute(sql, datas)
        self.conn.commit()
        self.db_size += len(str(datas)) + 100

    def try_except(
        self,
        func=None,
        *,
        error_return=None,
    ):
        """
        tre_except 裝飾器，用於捕獲函數執行過程中的異常，並將異常信息記錄到數據庫中
        error_return: 當函數執行出現異常時，返回的默認值，可使用此參數來自定義異常時的返回值

        使用func.__doc__傳遞參數：
            level:log等級
            error_level:錯誤等級
            tag:log標籤
            computer:是否記錄電腦資訊
            cpu:是否記錄CPU資訊
            memory:是否記錄記憶體資訊
            gpu:是否記錄GPU資訊
        """

        # 帶參數調用
        if func is None:
            return functools.partial(
                self.try_except,
                error_return=error_return,
            )

        func_doc = func.__doc__
        self.field_value = dict()
        func_tag = dict()
        if func_doc:
            func_tag = re.findall(TAG_REGULAR, func_doc)
            func_tag = {
                k.lstrip("#"): v for k, v in (item.split(":") for item in func_tag)
            }

        level = func_tag.get("level", "LOG")
        error_level = func_tag.get("error_level", "ERROR")
        self.field_value["tag"] = func_tag.get("tag", "")
        self.field_value["extra_info"] = func_tag.get("extra_info", "")
        is_computer = func_tag.get("computer", "True").lower() != "false"
        is_cpu = func_tag.get("cpu", "True").lower() != "false"
        is_memory = func_tag.get("memory", "True").lower() != "false"
        is_gpu = func_tag.get("gpu", "True").lower() != "false"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.datetime.now()
            start_time_timestamp = start_time.timestamp()
            start_time = start_time.isoformat()
            self.field_value["timestamp"] = start_time

            system_info = get_system_info_json(
                is_computer,
                is_cpu,
                is_memory,
                is_gpu,
            )
            self.field_value["system_info"] = system_info

            host_info = get_host_info(self.computer_name, self.user_name)
            host_info_json = json.dumps(host_info, indent=4, ensure_ascii=False)
            self.field_value["host_info"] = host_info_json

            stack = traceback.extract_stack()[-2]
            self.field_value["function_file_name"] = stack.filename
            self.field_value["function_line_number"] = stack.lineno
            self.field_value["function_name"] = func.__name__
            self.field_value["args"] = str(args)
            self.field_value["kwargs"] = str(kwargs)

            current_thread = threading.current_thread()
            self.field_value["thread_name"] = current_thread.name
            self.field_value["thread_id"] = current_thread.ident
            self.field_value["process_id"] = os.getpid()
            try:
                self.field_value["level"] = level
                result = func(*args, **kwargs)
                end_time_timestamp = datetime.datetime.now().timestamp()
                function_time = end_time_timestamp - start_time_timestamp
                message = f"result: {repr(result)}"
                self.field_value["message"] = message
                self.field_value["function_time"] = function_time
                self.log_to_db()
                return result
            except Exception as e:
                self.field_value["level"] = error_level
                end_time_timestamp = datetime.datetime.now().timestamp()
                function_time = end_time_timestamp - start_time_timestamp
                error_msg = f"{e.__class__.__name__}: {str(e)}"
                self.field_value["message"] = error_msg
                self.field_value["function_time"] = function_time
                self.field_value["traceback"] = traceback.format_exc()
                self.log_to_db()
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
                SELECT * FROM logs where level = ?
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
                SELECT * FROM logs WHERE level = 'LOG'
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
                SELECT * FROM logs WhERE level = 'ERROR'
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
            print(f"Error: {e}")
            exit(-1)
