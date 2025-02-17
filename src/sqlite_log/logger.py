import functools
import datetime
import traceback
import os
import threading
import getpass
import json
import re

from typing import List, Optional, Callable, Any
from .logger_type import LoggerInfo

# 正則表達式"#*:* "
TAG_REGULAR = r"#\S+?:\S+"


class Logger:
    def __init__(
        self,
        logger_info: LoggerInfo = LoggerInfo(),
    ):
        self.__loger_info = logger_info

    def try_except(
        self,
        func: Optional[Callable[..., Any]] = None,
        *,
        error_return: Any = None,
    ) -> Any:
        if func is None:
            return functools.partial(
                self.try_except,
                error_return=error_return,
            )

        return_value = None

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return_value = func(*args, **kwargs)
            except Exception as e:
                return_value = error_return
            finally:
                pass
            return return_value

        return wrapper
