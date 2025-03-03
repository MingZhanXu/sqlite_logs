import os
import sqlite3

from typing import Any, Dict, List, Optional, Union
from src.logger.logger_type import (
    FIELD_DEFAULT_VALUE,
    LoggerField,
    LoggerInfo,
    LoggerOutput,
)


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
        db_max_size: int = __MAX_SIZE,
        wal: bool = True,
        auto_close: bool = False,
    ) -> None:
        # ==============================
        # 設定基礎資訊
        # ==============================
        self.__db_folder = db_folder
        self.__db_name = db_name
        self.__db_max_size = db_max_size
        self.__wal = wal
        self.__auto_close = auto_close

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

    def init(self, logger_info: Optional[LoggerInfo]) -> bool:
        """logger output 初始化"""
        self.__logger_info = logger_info if logger_info else LoggerInfo()
        self.__init_db()
        return True

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
        self.__db_size = os.path.getsize(self.__db_file)
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
        data = data.get_field_value().copy()
        field = ", ".join(data.keys())
        placeholder = ", ".join("?" for _ in data.keys())
        value = tuple(data.values())
        sql = f"INSERT INTO logs ({field}) VALUES ({placeholder})"
        self.__conn_db()
        self.__cursor.execute(sql, value)
        self.__conn.commit()
        self.__auto_close_db()
        len_value = len(str(value))
        return len_value

    def output(self, data: LoggerInfo):
        """資料輸出"""
        len_value = self.__insert_data(data)
        # 更新資料庫大小(預估)
        self.__db_size += len_value + 100
        self.__switch_db()

    def get(
        self,
        filter: Optional[List[LoggerField]] = None,
        rule: Optional[Dict[LoggerField, Dict[str, Union[str, int, float]]]] = None,
    ) -> Any:
        """
        根據條件獲取資料

        rule {field_name: {condition: value}}
        condition: "=", ">", "<", ">=", "<=", "!=", "LIKE"
        """
        if filter:
            field_name = ["id"] + filter
            sql_select = f"SELECT {', '.join(filter)} FROM logs "
        else:
            field_name = ["id"] + [
                field_name for field_name, _ in self.__field_info.items()
            ]
            sql_select = f"SELECT {', '.join(field_name)} FROM logs "
        if rule:
            sql_rule = " AND ".join(
                f"{field_name} {condition} {value}"
                for field_name, condition_value in rule.items()
                for condition, value in condition_value.items()
            )
            sql_select += f"WHERE {sql_rule}"
        else:
            sql_select += "WHERE 1"
        self.__conn_db()
        self.__cursor.execute(sql_select)
        data = self.__cursor.fetchall()
        self.__auto_close_db()
        return field_name, data
