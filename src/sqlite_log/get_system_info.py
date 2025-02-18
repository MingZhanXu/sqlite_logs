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

SystemClass = Literal["computer", "cpu", "memory", "gpu"]
SystemInfoConfig = Dict[SystemClass, bool]


def get_cpu_info():
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
    info_func = {
        "computer_info": (is_computer, get_computer_info),
        "cpu_info": (is_cpu, get_cpu_info),
        "memory_info": (is_memory, get_memory_info),
        "gpu_info": (is_gpu, get_gpu_info),
    }
    system_info = {key: func() for key, (is_get, func) in info_func.items() if is_get}
    return system_info


def get_system_info_json(is_computer=True, is_cpu=True, is_memory=True, is_gpu=True):
    system_info = get_system_info(is_computer, is_cpu, is_memory, is_gpu)
    system_info_json = json.dumps(system_info, indent=4, ensure_ascii=False)
    return system_info_json


def get_host_info(computer_name=get_computer_name(), user_name=getpass.getuser()):
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
