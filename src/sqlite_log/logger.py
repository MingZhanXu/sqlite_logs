import functools
import datetime
import traceback
import os
import threading
import re

from typing import List, Optional, Callable, Any
from .logger_type import LoggerInfo, LoggerOutput, SQLiteLog, Union, LoggerMark
from .get_system_info import SystemInfo

# 正則表達式"#*:* "
TAG_REGULAR = r"#\S+?:\S+"

ValueTypes = Union[str, int, float, bool, list, tuple, set, dict, None]
ErrorReturnTypes = Union[Callable[[], Any], ValueTypes]


class Logger:
    def __init__(
        self,
        logger_info: LoggerInfo = LoggerInfo(),
        logger_output: Optional[LoggerOutput] = None,
    ):
        self.__logger_info = logger_info.copy()
        if logger_output is None:
            logger_output = LoggerOutput()
        self.__logger_output = logger_output
        self.__system_info = SystemInfo()

    def __parse_func_doc(self, func: Callable[..., Any]) -> dict[str, str]:
        """解析函數的註釋"""
        func_doc = func.__doc__
        func_tag = self.__logger_info.get_field_value()
        if func_doc:
            func_re = re.findall(TAG_REGULAR, func_doc)
            func_re_tag = dict()
            for item in func_re:
                key, value = item.lstrip("#").split(":")
                if key in func_tag.keys():
                    if key in LoggerMark.__args__:
                        func_re_tag[key] = value
                    else:
                        func_re_tag[key] = False if value.lower() == "false" else True
            self.__logger_info.update_record(func_re_tag)

        return func_tag

    def __set_system_logger(self, logger_info: LoggerInfo) -> None:
        is_record = logger_info.get_is_record()
        if is_record["computer"] == True:
            logger_info.set_field_value("computer", self.__system_info.get_host_info())
        if is_record["cpu"] == True:
            logger_info.set_field_value("cpu", self.__system_info.get_cpu_info())
        if is_record["memory"] == True:
            logger_info.set_field_value("memory", self.__system_info.get_memory_info())
        if is_record["gpu"] == True:
            logger_info.set_field_value("gpu", self.__system_info.get_gpu_info())
        if is_record["host"] == True:
            logger_info.set_field_value("host", self.__system_info.get_host_info())

    def __set_thread_logger(self, logger_info: LoggerInfo) -> None:
        is_record = logger_info.get_is_record()
        if is_record["thread"] == True:
            logger_info.set_field_value("thread_name", threading.current_thread().name)
            logger_info.set_field_value("thread_id", threading.current_thread().ident)
            logger_info.set_field_value("process_id", os.getpid())

    def __run_error_return(self, error_return: ErrorReturnTypes) -> Any:
        if callable(error_return):
            try:
                return error_return()
            except Exception as e:
                return f"Error return function error: {e}"
        return error_return

    def try_except(
        self,
        func: Optional[Callable[..., Any]] = None,
        *,
        error_return: ErrorReturnTypes = None,
    ) -> Any:
        """
        裝飾器函數，用於捕獲函數執行過程中的異常，並記錄異常信息。
        可透過func.__doc__中的註釋來設置tag。
        格式為#tag_name:tag_value，多個tag之間用空格分隔。
        Args:
            error_return: 異常時的返回值，可以是固定值，也可以是函數。

        Tag:
            #level: 設置日誌級別，默認為LOG，形態為str。
            #tag: 設置日誌標籤，形態為str。
            #message: 設置日誌消息，形態為str。
            #function: 設置是否要記錄函數資訊，可接收內容為true或false。
            #thread: 設置是否要記錄執行緒資訊，可接收內容為true或false。
            #computer: 設置是否要記錄電腦資訊，可接收內容為true或false。
            #cpu: 設置是否要記錄CPU資訊，可接收內容為true或false。
            #memory: 設置是否要記錄記憶體資訊，可接收內容為true或false。
            #gpu: 設置是否要記錄GPU資訊，可接收內容為true或false。
            #host: 設置是否要記錄主機資訊，可接收內容為true或false。
        """
        if func is None:
            return functools.partial(
                self.try_except,
                error_return=error_return,
            )
        self.__parse_func_doc(func)
        __logger_info = self.__logger_info
        is_record = __logger_info.get_is_record()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger_info = __logger_info.copy()
            start_time = datetime.datetime.now()
            start_time_timestamp = start_time.timestamp()
            start_time = start_time.isoformat()
            logger_info.set_field_value("timestamp", start_time)
            self.__set_system_logger(logger_info)
            self.__set_thread_logger(logger_info)

            if is_record["function"] == True:
                logger_info.set_field_value("function_name", func.__name__)
                logger_info.set_field_value("args", str(args))
                logger_info.set_field_value("kwargs", str(kwargs))

            return_value = None
            try:
                return_value = func(*args, **kwargs)
            except Exception as e:
                if is_record["function"] == True:
                    logger_info.set_field_value("traceback", traceback.format_exc())
                    error_type = f"Function error: {type(e).__name__}"
                    logger_info.set_field_value("error_type", error_type)
                return_value = self.__run_error_return(error_return)
            finally:
                if is_record["function"] == True:
                    end_time_timestamp = datetime.datetime.now().timestamp()
                    function_time = end_time_timestamp - start_time_timestamp
                    return_value_str = str(return_value)
                    logger_info.set_field_value("function_return", return_value_str)
                    logger_info.set_field_value("function_time", function_time)
                # 執行日誌輸出
                try:
                    self.__logger_output.output(logger_info)
                except Exception as e:
                    print(f"Logger output error: {e}")
                    logger_info.print_data()

            return return_value

        return wrapper
