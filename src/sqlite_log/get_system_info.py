import psutil
import platform
import GPUtil
import json
import socket
import subprocess
import os
import getpass

__GB_SIZE = 1024**3


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


def get_system_info():
    computer_info = get_computer_info()
    cpu_info = get_cpu_info()
    memory_info = get_memory_info()
    gpu_info = get_gpu_info()

    system_info = {
        "Computer_info": computer_info,
        "CPU_info": cpu_info,
        "RAM_info": memory_info,
        "GPU_info": gpu_info,
    }
    return system_info


def get_system_info_json():
    system_info = get_system_info()
    system_info_json = json.dumps(system_info, indent=4, ensure_ascii=False)
    return system_info_json


def get_host_info():
    host_info = {}
