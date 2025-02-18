import os
import sqlite3

from typing import Dict, Optional, List, Any, Union, Literal

LoggerField = List[
    Literal[
        # Base
        "level",
        "timestamp",
        "message",
        # Function
        "function_name",
        "args",
        "kwargs",
        "function_time",
        "function_return",
        "error_type",
        "traceback",
        # Thread
        "thread_name",
        "thread_id",
        "process_id",
        # System
        "computer",
        "cpu",
        "memory",
        "gpu",
        "host",
    ]
]
LoggerGroup = Literal["base", "function", "thread", "system"]
FIELD_GROUP: Dict[LoggerGroup, List[LoggerField]] = {
    "base": ["level", "timestamp", "message"],
    "function": ["function_name", "args", "kwargs", "function_time", "function_return"],
    "thread": ["thread_name", "thread_id", "process_id"],
    "system": ["computer", "cpu", "memory", "gpu", "host"],
}
FIELD_DEFAULT_VALUE: Dict[str, Optional[Union[str, float, int]]] = {
    "level": "LOG",
    "timestamp": 0.0,
    "message": "",
    "tag": "",
    "function_name": "",
    "args": "",
    "kwargs": "",
    "function_time": 0.0,
    "function_return": "",
    "error_type": "",
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

# 設訂標記的值
LoggerMark = Literal[
    "level",
    "tag",
    "message",
]
# True: 記錄, False: 不記錄
LoggerRecord = Literal[
    "function",
    "thread",
    "computer",
    "cpu",
    "memory",
    "gpu",
    "host",
]
LoggerTag = Union[LoggerMark, LoggerRecord]
LoggerTagValue = Dict[LoggerTag, str]

DEFAULT_LOGGER_TAG: LoggerTagValue = {
    "level": "LOG",
    "tag": "",
    "message": "",
    "function": "true",
    "thread": "true",
    "computer": "true",
    "cpu": "true",
    "memory": "true",
    "gpu": "true",
    "host": "true",
}

LoggerConfig = Literal[
    "level",
    "tag",
    "message",
]


class LoggerInfo:
    """
    用於傳遞所記錄的資料。

    Args:
        config (List[LoggerTagValue]):
            要設定的欄位。
    Methods:
        reset_data() -> None:
            重置資料，需在每次記錄完後呼叫。
        get_is_record() -> dict[str, bool]:
            獲取欄位是否應該被記錄。
        get_field_value() -> dict[str, Any]:
            獲取所有欄位的值。
        set_field_value(field: str, value: Any) -> None:
            設定特定欄位的值，用於 Logger 資料傳遞。
        set_is_record(field: str, is_record: bool) -> None:
            設定特定欄位是否記錄，用於傳遞給 Logger。
    """

    def __init__(self, config: Optional[LoggerTagValue] = None):
        self.__config = DEFAULT_LOGGER_TAG.copy()
        if config:
            self.__config.update(config)

        # 初始化欄位資訊
        self.__is_default_record = {
            k: v for k, v in self.__config.items() if k in LoggerRecord.__args__
        }
        self.__field_default_value: Dict[str, Union[float, str]] = (
            FIELD_DEFAULT_VALUE.copy()
        )
        # 根據config設定欄位資訊
        self.__set_config()

        self.reset_data()

    def __set_config(self):
        for k, v in self.__config.items():
            if k in LoggerMark.__args__:
                self.__field_default_value[k] = v
            elif k in LoggerRecord.__args__ and v.lower() == "false":
                if k in FIELD_GROUP["system"]:
                    del self.__field_default_value[k]
                elif k == "function" or k == "thread":
                    for field in FIELD_GROUP[k]:
                        del self.__field_default_value[field]

    def reset_data(self) -> None:
        """重置資料"""
        self.__field_value = self.__field_default_value.copy()
        self.__is_record = self.__is_default_record.copy()

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

    def set_is_record(self, key: str, is_record: bool) -> bool:
        """設定是否記錄"""
        if key in self.__field_default_value:
            self.__is_record[key] = is_record
            return True
        return False

    def update_record(self, config: LoggerTagValue) -> None:
        """更新記錄"""
        for k, v in config.items():
            if k in LoggerMark.__args__:
                self.__field_default_value[k] = v
            elif k in LoggerRecord.__args__ and v.lower() == "false":
                if k in FIELD_GROUP["system"]:
                    self.__field_default_value.pop(k)
                elif k == "function" or k == "thread":
                    for field in FIELD_GROUP[k]:
                        self.__field_default_value.pop(field)
        self.reset_data()

    def print_data(self) -> None:
        """
        顯示當前資料，用作異常排除。
        """
        print(f"field_value: {self.__field_value}")
        print(f"is_record: {self.__is_record}")
        print(f"field_default_value: {self.__field_default_value}")
        print(f"is_default_record: {self.__is_default_record}")
        print(f"config: {self.__config}")


class LoggerOutput:
    """
    LoggerOutput 負責處裡日誌的輸出。
    Methods:
        output(data: LoggerInfo) -> None:
            定義繼承該類別所輸出日誌的方式。
        get(*args, **kwargs) -> Any:
            根據*args、**kwargs來決定如何獲取存入日誌的資訊。
    """

    def __init__(self, data: LoggerInfo):
        pass

    def output(self, data: LoggerInfo):
        pass

    def get(self, *args, **kwargs):
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
            field_name for field_name in self.__logger_info.get_field_value().keys()
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

    def __auto_close_db(self) -> None:
        """使自動關閉資料庫"""
        if self.__auto_close:
            self.__conn.close()

    def __create_db(self) -> None:
        """建立資料庫"""
        self.__conn_db()
        self.__create_table()
        self.__auto_close_db()

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
        self.__auto_close_db()

    def __switch_db(self) -> None:
        """判斷DB當前的大小，是否切換資料庫"""
        if self.__check_db_size():
            self.__db_size = 0
            self.__db_index += 1
            self.__db_file_update()
            self.__create_db()
            self.__auto_close_db()

    def __insert_data(self, data: LoggerInfo) -> int:
        """插入資料"""
        data = {key: value for key, value in data.get_field_value().items()}
        field = ", ".join(data.keys())
        placeholder = ", ".join("?" for _ in data.keys())
        value = tuple(data.values())
        sql = f"INSERT INTO logs ({field}) VALUES ({placeholder})"
        self.__conn_db()
        self.__cursor.execute(sql, value)
        self.__conn.commit()
        self.__auto_close_db()
        len_value = len(value)
        return len_value

    def output(self, data: LoggerInfo):
        """資料輸出"""
        len_value = self.__insert_data(data)
        # 更新資料庫大小(預估)
        self.__db_size += len_value + 100
        self.__switch_db()
