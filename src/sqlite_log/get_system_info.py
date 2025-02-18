import psutil
import platform
import GPUtil
import json
import socket
import subprocess
import os
import getpass
from typing import Dict, Optional, Literal

__GB_SIZE = 1024**3

SystemClass = Literal["computer", "cpu", "memory", "gpu", "host"]
SystemInfoConfig = Dict[SystemClass, bool]


def get_cpu_info():
    """
    獲取 CPU 資訊。

    回傳:
        dict: 包含以下 CPU 詳細資訊的字典：
            - usage (str): CPU 使用率百分比。
            - physical_cores (int): 實體核心數。
            - logical_cores (int): 邏輯核心數。
            - current_frequency (str, 選填): 目前 CPU 頻率 (MHz)。
            - min_frequency (str, 選填): 最小 CPU 頻率 (MHz)。
            - max_frequency (str, 選填): 最大 CPU 頻率 (MHz)。
    """
    cpu_usage = f"{psutil.cpu_percent(interval=0)}%"
    cpu_physical_cores = psutil.cpu_count(logical=False)
    cpu_logical_cores = psutil.cpu_count(logical=True)
    cpu_info = {
        "usage": cpu_usage,
        "physical_cores": cpu_physical_cores,
        "logical_cores": cpu_logical_cores,
    }
    cpu_freq = psutil.cpu_freq()
    if cpu_freq is not None:
        cpu_info["current_frequency"] = f"{cpu_freq.current:.2f} MHz"
        cpu_info["min_frequency"] = f"{cpu_freq.min:.2f} MHz"
        cpu_info["max_frequency"] = f"{cpu_freq.max:.2f} MHz"
    return cpu_info


def get_memory_info():
    """
    獲取記憶體 (RAM) 資訊。

    回傳:
        dict: 包含以下記憶體詳細資訊的字典：
            - total (str): 總記憶體大小 (GB)。
            - used (str): 使用中記憶體大小 (GB)。
            - free (str): 空閒記憶體大小 (GB)。
            - percent (str): 記憶體使用率百分比。
    """
    memory = psutil.virtual_memory()
    ram_total = f"{memory.total / __GB_SIZE:.2f} GB"
    ram_used = f"{memory.used / __GB_SIZE:.2f} GB"
    ram_free = f"{memory.free / __GB_SIZE:.2f} GB"
    ram_percent = f"{memory.percent:.2f} %"
    ram_info = {
        "total": ram_total,
        "used": ram_used,
        "free": ram_free,
        "percent": ram_percent,
    }
    return ram_info


def get_gpu_info():
    """
    獲取 GPU 資訊，若此list為空則未檢測到 GPU。

    回傳:
        dict: 包含以下 GPU 詳細資訊的字典：
            - id (int): GPU 編號。
            - name (str): GPU 名稱。
            - memory_total (str): 總記憶體大小 (GB)。
            - memory_used (str): 使用中記憶體大小 (GB)。
            - memory_free (str): 空閒記憶體大小 (GB)。
            - memory_percent (str): 記憶體使用率百分比。
            - temperature (str): 溫度 (°C)。
            - power (str): 功耗 (W)。
            - utilization (str): 使用率百分比。
    """
    gpus = GPUtil.getGPUs()
    gpu_info = []
    for gpu in gpus:
        gpu_info.append(
            {
                "id": gpu.id,
                "name": gpu.name,
                "memory_total": f"{gpu.memoryTotal / __GB_SIZE:.2f} GB",
                "memory_used": f"{gpu.memoryUsed / __GB_SIZE:.2f} GB",
                "memory_free": f"{gpu.memoryFree / __GB_SIZE:.2f} GB",
                "memory_percent": f"{gpu.memoryUtil:.2f} % ",
                "temperature": f"{gpu.temperature:.2f} °C",
                "power": f"{gpu.powerUtil} W",
                "utilization": f"{gpu.gpuUtil:.2f} %",
            }
        )
    return gpu_info


def get_computer_name():
    """
    獲取電腦名稱。

    回傳:
        str: 電腦名稱。
    """
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


def get_computer_info():
    """
    獲取電腦資訊。

    回傳:
        dict: 包含以下電腦詳細資訊的字典：
            - computer_name (str): 電腦名稱。
            - user_name (str): 使用者名稱。
            - system_name (str): 作業系統名稱。
            - system_version (str): 作業系統版本。
            - system_release (str): 作業系統發行版本。
            - system_machine (str): 系統架構。
            - system_processor (str): 處理器資訊。
    """
    computer_name = get_computer_name()
    user_name = getpass.getuser()
    system_info = platform.uname()
    system_name = system_info.system
    system_version = system_info.version
    system_release = system_info.release
    system_machine = system_info.machine
    system_processor = system_info.processor

    computer_info = {
        "computer_name": computer_name,
        "user_name": user_name,
        "system_name": system_name,
        "system_version": system_version,
        "system_release": system_release,
        "system_machine": system_machine,
        "system_processor": system_processor,
    }
    return computer_info


def get_system_info(is_computer=True, is_cpu=True, is_memory=True, is_gpu=True):
    """
    獲取系統資訊。

    參數:
        is_computer (bool): 是否獲取電腦資訊。
        is_cpu (bool): 是否獲取 CPU 資訊。
        is_memory (bool): 是否獲取記憶體資訊。
        is_gpu (bool): 是否獲取 GPU 資訊。

    回傳:
        dict: 包含系統資訊的字典。
        computer_info (dict): 電腦資訊。
        cpu_info (dict): CPU 資訊。
        memory_info (dict): 記憶體資訊。
        gpu_info (dict): GPU 資訊。
    """
    info_func = {
        "computer_info": (is_computer, get_computer_info),
        "cpu_info": (is_cpu, get_cpu_info),
        "memory_info": (is_memory, get_memory_info),
        "gpu_info": (is_gpu, get_gpu_info),
    }
    system_info = {key: func() for key, (is_get, func) in info_func.items() if is_get}
    return system_info


def get_system_info_json(is_computer=True, is_cpu=True, is_memory=True, is_gpu=True):
    """
    獲取系統資訊的 JSON 格式。

    參數:
        is_computer (bool): 是否獲取電腦資訊。
        is_cpu (bool): 是否獲取 CPU 資訊。
        is_memory (bool): 是否獲取記憶體資訊。
        is_gpu (bool): 是否獲取 GPU 資訊。

    回傳:
        str: 包含系統資訊的 JSON 字串。
    """
    system_info = get_system_info(is_computer, is_cpu, is_memory, is_gpu)
    system_info_json = json.dumps(system_info, indent=4, ensure_ascii=False)
    return system_info_json


def get_host_info(computer_name=get_computer_name(), user_name=getpass.getuser()):
    """
    獲取主機資訊。

    參數:
        computer_name (str): 電腦名稱。
        user_name (str): 使用者名稱。

    回傳:
        dict: 包含以下主機詳細資訊的字典：
            - computer_name (str): 電腦名稱。
            - user_name (str): 使用者名稱。
            - system (str): 作業系統名稱。
            - node (str): 網路節點名稱。
            - release (str): 作業系統發行版本。
            - version (str): 作業系統版本。
            - machine (str): 系統架構。
            - processor (str): 處理器資訊。
    """
    host_info = platform.uname()
    host_info = {
        "computer_name": computer_name,
        "user_name": user_name,
        "system": host_info.system,
        "node": host_info.node,
        "release": host_info.release,
        "version": host_info.version,
        "machine": host_info.machine,
        "processor": host_info.processor,
    }
    return host_info


class SystemInfo:
    DEFAULT_CONFIG = {
        "computer": True,
        "cpu": True,
        "memory": True,
        "gpu": True,
    }

    def __init__(self, config: Optional[SystemInfoConfig] = None):
        self.__config = SystemInfo.DEFAULT_CONFIG.copy()
        if config:
            self.__config.update(config)
        self.__data = {k: dict() for k in self.__config.keys() if k == True}
        if self.__config["computer"]:
            self.__data["computer"] = get_computer_info()
            self.__data["computer_json"] = json.dumps(
                self.__data["computer"], indent=4, ensure_ascii=False
            )

    def get_computer_info(self) -> Optional[str]:
        if self.__config["computer"]:
            return self.__data["computer_json"]
        return None

    def get_cpu_info(self) -> Optional[str]:
        if self.__config["cpu"]:
            self.__data["cpu"] = get_cpu_info()
            self.__data["cpu_json"] = json.dumps(
                self.__data["cpu"], indent=4, ensure_ascii=False
            )
            return self.__data["cpu_json"]
        return None

    def get_memory_info(self) -> Optional[str]:
        if self.__config["memory"]:
            self.__data["memory"] = get_memory_info()
            self.__data["memory_json"] = json.dumps(
                self.__data["memory"], indent=4, ensure_ascii=False
            )
            return self.__data["memory_json"]
        return None

    def get_gpu_info(self) -> Optional[str]:
        if self.__config["gpu"]:
            self.__data["gpu"] = get_gpu_info()
            self.__data["gpu_json"] = json.dumps(
                self.__data["gpu"], indent=4, ensure_ascii=False
            )
            return self.__data["gpu_json"]
        return None

    def get_host_info(self) -> Optional[str]:
        if self.__config["host"]:
            self.__data["host"] = get_host_info(
                computer_name=self.__data["computer"]["computer_name"],
                user_name=self.__data["computer"]["user_name"],
            )
            self.__data["host_json"] = json.dumps(
                self.__data["host"], indent=4, ensure_ascii=False
            )
            return self.__data["host_json"]
        return None
