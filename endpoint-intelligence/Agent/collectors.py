"""
collectors.py - Telemetry collection for the endpoint intelligence agent.

Each hardware/OS category has its own small function that returns a dict.
collect() calls them all and merges the results into one flat snapshot dict.

This structure means adding a new telemetry source later (e.g. SMART, thermal)
is just writing one more collect_* function and adding it to collect().

Dependencies:
    pip install psutil

Run standalone to see a snapshot from the current machine:
    python collectors.py
"""

import platform
import socket
from datetime import datetime

import psutil


def collect_identity():
    """Who and what is this machine, and when was this reading taken."""
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }


def collect_uptime():
    """How long since the machine last booted, in hours."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = (datetime.now() - boot_time).total_seconds()
    return {
        "uptime_hours": round(uptime_seconds / 3600, 1),
    }


def collect_cpu():
    """CPU load and core count.

    interval=1 samples over one second for an accurate load figure (the very
    first call to cpu_percent otherwise returns 0.0).
    """
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count": psutil.cpu_count(logical=True),
    }


def collect_memory():
    """RAM total and how full it is."""
    mem = psutil.virtual_memory()
    return {
        "ram_total_gb": round(mem.total / (1024 ** 3), 1),
        "ram_used_percent": mem.percent,
    }


def collect_disk():
    """System drive capacity and usage.

    We check the drive Windows booted from rather than hard-coding C:,
    and fall back to / on non-Windows machines.
    """
    system_drive = "C:\\"
    if platform.system() != "Windows":
        system_drive = "/"
    disk = psutil.disk_usage(system_drive)
    return {
        "disk_path": system_drive,
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "disk_used_percent": disk.percent,
    }


def collect_battery():
    """Battery level and power state.

    Returns None values on desktops/servers where no battery exists, so the
    snapshot shape stays consistent across all device types.
    """
    battery = psutil.sensors_battery()
    if battery is None:
        return {
            "battery_percent": None,
            "battery_plugged_in": None,
        }
    return {
        "battery_percent": battery.percent,
        "battery_plugged_in": battery.power_plugged,
    }


def collect():
    """Run every collector and merge into one flat snapshot dict.

    To add a new telemetry source later, write a collect_*() function above
    and add it to this list. Nothing else in the project needs to change.
    """
    snapshot = {}
    for collector in (
        collect_identity,
        collect_uptime,
        collect_cpu,
        collect_memory,
        collect_disk,
        collect_battery,
    ):
        try:
            snapshot.update(collector())
        except Exception as exc:
            # One failing collector should never crash the whole snapshot.
            # We record the failure and keep going.
            snapshot[f"error_{collector.__name__}"] = str(exc)
    return snapshot


if __name__ == "__main__":
    import json

    print(json.dumps(collect(), indent=2))