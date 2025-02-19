import functools
import datetime
import traceback
import os
import threading
import getpass
import json
import re

from typing import List, Optional, Callable, Any
from .logger_type import LoggerInfo, LoggerOutput, SQLiteLog, Union

# 正則表達式"#*:* "
TAG_REGULAR = r"#\S+?:\S+"

__ValueTypes = Union[str, int, float, bool, list, tuple, set, dict, None]
__ErrorReturnTypes = Union[Callable[[], Any], __ValueTypes]


class Logger:
    def __init__(
        self,
        logger_info: LoggerInfo = LoggerInfo(),
        logger_output: Optional[LoggerOutput] = None,
    ):
        self.__logger_info = logger_info
        if logger_output is None:
            logger_output = LoggerOutput()
        self.__logger_output = logger_output

    def __parse_func_doc(self, func: Callable[..., Any]) -> dict[str, str]:
        """解析函數的註釋"""
        func_doc = func.__doc__
        func_tag = self.__logger_info.get_field_value()
        if func_doc:
            func_re = re.findall(TAG_REGULAR, func_doc)
            func_re_tag = {
                k.lstrip("#"): v
                for k, v in (item.split(":") for item in func_re)
                if k.lstrip("#") in func_tag.keys()
            }
            self.__logger_info.update_record(func_re_tag)

        return func_tag

    def try_except(
        self,
        func: Optional[Callable[..., Any]] = None,
        *,
        error_return: __ErrorReturnTypes = None,
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
        logger_info = self.__logger_info
        self.__parse_func_doc(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return_value = None
            try:
                return_value = func(*args, **kwargs)
            except Exception as e:
                if callable(error_return):
                    try:
                        return_value = error_return()
                    except Exception as inner_e:
                        return_value = f"Error return function error: {inner_e}"
                else:
                    return_value = error_return
            finally:
                try:
                    self.__logger_output.output(logger_info)
                except Exception as e:
                    print(f"Logger output error: {e}")
                    logger_info.print_data()

            return return_value

        return wrapper
