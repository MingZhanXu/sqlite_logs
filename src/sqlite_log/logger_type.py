import os
import sqlite3

from typing import Dict, Optional, List, Any, Union

FIELD_GROUP: Dict[str, List[str]] = {
    "Base": ["level", "timestamp", "message"],
    "Function": [
        "function_name",
        "args",
        "kwargs",
        "function_time",
        "return",
        "traceback",
    ],
    "Thread": ["thread_name", "thread_id", "process_id"],
    "System": ["computer", "cpu", "memory", "gpu", "host"],
}
FIELD_IS_RECORD = {
    value: True for key in FIELD_GROUP.keys() for value in FIELD_GROUP[key]
}
FIELD_DEFAULT_VALUE: Dict[str, Union[float, str]] = {
    "level": "LOG",
    "timestamp": 0.0,
    "message": "",
    "function_name": "",
    "args": "",
    "kwargs": "",
    "function_time": 0.0,
    "return": "",
    "traceback": "",
    "thread_name": "",
    "thread_id": 0,
    "process_id": 0,
    "computer": "",
    "cpu": "",
    "memory": "",
    "gpu": "",
    "host": "",
}


class LoggerInfo:
    def __init__(self, remove_record: Optional[List[str]] = None):

        self.__field_group: Dict[str, List[str]] = FIELD_GROUP.copy()
        self.__is_default_record = FIELD_IS_RECORD.copy()
        self.__field_default_value: Dict[str, Union[float, str]] = (
            FIELD_DEFAULT_VALUE.copy()
        )
        if remove_record:
            for key in remove_record:
                self.__is_record[key] = False
                self.__field_default_value.pop(key, None)
            self.__field_group = {
                key: [v for v in values if v not in remove_record]
                for key, values in self.__field_group.items()
            }
            self.__field_group = {k: v for k, v in self.__field_group.items() if v}
        self.__field_value = self.__field_default_value.copy()
        self.__is_record = self.__is_default_record.copy()

    def get_field_group(self) -> Dict[str, List[str]]:
        """獲取欄位分組"""
        return self.__field_group

    def get_is_record(self) -> Dict[str, bool]:
        """獲取是否記錄"""
        return self.__is_record

    def get_field_value(self) -> Dict[str, Union[float, str, int]]:
        """獲取欄位值"""
        return self.__field_value

    def set_field_value(self, key: str, value: Union[float, str, int]) -> bool:
        """設定欄位值"""
        if key in self.__field_value:
            self.__field_value[key] = value
            return True
        return False

    def reset_value(self) -> None:
        """重置欄位值"""
        self.__field_value = self.__field_default_value.copy()
        self.__is_record = self.__is_default_record.copy()


class LoggerOutput:
    def __init__(self, data: LoggerInfo):
        pass

    def output(self, data: LoggerInfo):
        pass


class SQLiteLog(LoggerOutput):
    __MAX_SIZE: int = 100 * 1024 * 1024  # 100MB
    __DEFAULT_FOLDER = "logs"
    __SQL_TYPE = {
        "float": "REAL",
        "str": "TEXT",
        "int": "INTEGER",
    }
    __CREATE_TABLE_SQL = (
        "CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, "
    )
    __CHECK_TABLE_SQL = (
        "SELECT name FROM sqlite_master WHERE type='table' AND name='logs'"
    )
    __SET_WAL = "PRAGMA journal_mode=WAL"
    __SET_SYNC = "PRAGMA synchronous=NORMAL"

    def __init__(
        self,
        db_folder: str = __DEFAULT_FOLDER,
        db_name: str = "log",
        logger_info: Optional[LoggerInfo] = None,
        db_max_size: int = __MAX_SIZE,
        wal: bool = True,
        auto_close: bool = False,
    ) -> None:
        # ==============================
        # 設定基礎資訊
        # ==============================
        self.__db_folder = db_folder
        self.__db_name = db_name
        self.__logger_info = logger_info if logger_info else LoggerInfo()
        self.__db_max_size = db_max_size
        self.__wal = wal
        self.__auto_close = auto_close

        self.__init_db()

    def __db_file_update(self) -> None:
        """更新資料庫名稱"""
        db_file = f"{self.__db_name}_{self.__db_index}.sqlite"
        self.__db_file = os.path.join(self.__db_folder, db_file)

    def __check_db_size(self) -> bool:
        """檢查資料庫大小是否超過max_size"""
        if self.__db_size >= self.__db_max_size:
            self.__db_size = os.path.getsize(self.__db_file)
            if self.__db_size >= self.__db_max_size:
                return True
        return False

    def __get_sql_type(self, value: Union[float, str, int]) -> str:
        """獲取資料庫資料型態"""
        return SQLiteLog.__SQL_TYPE[type(value).__name__]

    def __get_field_info(self) -> None:
        """
        獲取欄位資訊
        self__field_info: Dict[欄位名稱, SQL資料型態]
        """
        field_name = [
            field_name
            for group in self.__logger_info.get_field_group().values()
            for field_name in group
        ]
        self.__field_info = {
            field_name: self.__get_sql_type(FIELD_DEFAULT_VALUE[field_name])
            for field_name in field_name
        }

    def __get_last_db(self) -> None:
        """獲取最新的資料庫"""
        while os.path.exists(self.__db_file):
            if self.__check_db_size():
                self.__db_index += 1
                self.__db_file_update()
            else:
                break

    def __create_table(self) -> None:
        """建立資料表"""
        sql_table_info = ", ".join(
            f"{field_name} {field_type}"
            for field_name, field_type in self.__field_info.items()
        )

        sql = f"{SQLiteLog.__CREATE_TABLE_SQL}{sql_table_info})"
        self.__cursor.execute(sql)

        if self.__wal:
            self.__cursor.execute(SQLiteLog.__SET_WAL)
            self.__cursor.execute(SQLiteLog.__SET_SYNC)
            self.__conn.commit()

        self.__conn.commit()

    def __conn_db(self) -> None:
        """連線資料庫"""
        self.__conn = sqlite3.connect(self.__db_file)
        self.__cursor = self.__conn.cursor()

    def __create_db(self) -> None:
        """建立資料庫"""
        self.__conn_db()
        self.__create_table()
        if self.__auto_close:
            self.__conn.close()

    def __init_db(self) -> None:
        """初始化資料庫"""
        # 判斷是否有資料庫資料夾
        if not os.path.exists(self.__db_folder):
            os.makedirs(self.__db_folder)
        # 初始化資料庫資訊
        self.__db_size = 0
        self.__db_index = 0
        self.__get_field_info()
        self.__db_file_update()
        # 切換至最新資料庫
        self.__get_last_db()
        # 初始化資料庫連線
        self.__conn_db()
        # 檢查資料表是否存在
        self.__cursor.execute(SQLiteLog.__CHECK_TABLE_SQL)
        if not self.__cursor.fetchone():
            self.__create_table()
        if self.__auto_close:
            self.__conn.close()

    def output(self, data: LoggerInfo):
        data = {
            key: value
            for key, value in data.get_field_value().items()
            if data.get_is_record()[key]
        }
        field = ", ".join(data.keys())
        value = ", ".join(f"'{value}'" for value in data.values())
        sql = f"INSERT INTO logs ({field}) VALUES ({value})"
        self.__conn_db()
        self.__cursor.execute(sql)
        self.__conn.commit()
        if self.__auto_close:
            self.__conn.close()
