from typing import Dict, Optional, List, Any, Union, Literal

LoggerField = List[
    Literal[
        # Base
        "level",
        "tag",
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
    "base": ["level", "tag", "timestamp", "message"],
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
LoggerTagValue = Dict[LoggerTag, Union[str, bool]]

DEFAULT_LOGGER_TAG: LoggerTagValue = {
    "level": "LOG",
    "tag": "",
    "message": "",
    "function": True,
    "thread": True,
    "computer": True,
    "cpu": True,
    "memory": True,
    "gpu": True,
    "host": True,
}

LoggerConfig = Literal[
    "level",
    "tag",
    "message",
]

SQLCondition = Literal[
    "=",
    ">",
    "<",
    ">=",
    "<=",
    "!=",
    "LIKE",
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
            獲取欄位群組是否應該被記錄。
        get_field_value() -> dict[str, Any]:
            獲取欄位的名稱與欄位的值。
        set_field_value(field: str, value: Any) -> bool:
            設定特定欄位的值，用於 Logger 資料傳遞。
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
            elif k in LoggerRecord.__args__ and v == False:
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
                self.__config[k] = v
                self.__field_default_value[k] = v
            elif k in LoggerRecord.__args__ and v == False:
                self.__config[k] = False
                self.__is_default_record[k] = False
                if k in FIELD_GROUP["system"]:
                    self.__field_default_value.pop(k)
                elif k == "function" or k == "thread":
                    for field in FIELD_GROUP[k]:
                        self.__field_default_value.pop(field)
        self.reset_data()

    def print_data(self) -> None:
        """顯示當前資料，用作異常排除。"""
        print(f"field_value: {self.__field_value}")
        print(f"is_record: {self.__is_record}")
        print(f"field_default_value: {self.__field_default_value}")
        print(f"is_default_record: {self.__is_default_record}")
        print(f"config: {self.__config}")

    def copy(self) -> "LoggerInfo":
        """複製 LoggerInfo"""
        new_logger_info = LoggerInfo(self.__config)
        return new_logger_info


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
