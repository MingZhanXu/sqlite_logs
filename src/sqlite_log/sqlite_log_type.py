from typing import Type
from dataclasses import dataclass


@dataclass
class SQLType:
    """
    SQLite 與 Python 資料型態對應表
    example:
        sql_type: 'TEXT'
        python_type: str
    """

    sql_type: str
    py_type: Type


@dataclass
class LoggerType:
    """
    Logger 資料庫表格欄位名稱與資料型態對應表
    example:
        field_name: 'name'
        sql_type: SQLType('TEXT', str)
    """

    field_name: str
    sql_type: SQLType


SQL_TEXT = SQLType("TEXT", str)
SQL_INTEGER = SQLType("INTEGER", int)
SQL_REAL = SQLType("REAL", float)
