"""Isletim sistemi kaynak metriklerini standart kutuphane ile okur."""

from __future__ import annotations

import os
import sys
from ctypes import Structure, byref, c_ulong, c_ulonglong
import ctypes


class _MemoryStatusEx(Structure):
    """Windows GlobalMemoryStatusEx sonuc yapisi."""

    _fields_ = [
        ("dwLength", c_ulong),
        ("dwMemoryLoad", c_ulong),
        ("ullTotalPhys", c_ulonglong),
        ("ullAvailPhys", c_ulonglong),
        ("ullTotalPageFile", c_ulonglong),
        ("ullAvailPageFile", c_ulonglong),
        ("ullTotalVirtual", c_ulonglong),
        ("ullAvailVirtual", c_ulonglong),
        ("ullAvailExtendedVirtual", c_ulonglong),
    ]


class _FileTime(Structure):
    """Windows FILETIME yapisini 64 bit sayiya cevirmek icin kullanilir."""

    _fields_ = [
        ("dwLowDateTime", c_ulong),
        ("dwHighDateTime", c_ulong),
    ]

    def as_int(self) -> int:
        """FILETIME degerini tek tamsayiya cevirir."""
        return (self.dwHighDateTime << 32) + self.dwLowDateTime


_last_windows_cpu_times: tuple[int, int] | None = None


def _windows_cpu_percent() -> float | None:
    """Windows GetSystemTimes ile iki olcum arasi CPU kullanim yuzdesini hesaplar."""
    global _last_windows_cpu_times
    try:
        idle = _FileTime()
        kernel = _FileTime()
        user = _FileTime()
        if not ctypes.windll.kernel32.GetSystemTimes(byref(idle), byref(kernel), byref(user)):
            return None
        idle_time = idle.as_int()
        total_time = kernel.as_int() + user.as_int()
        if _last_windows_cpu_times is None:
            _last_windows_cpu_times = (idle_time, total_time)
            return None
        previous_idle, previous_total = _last_windows_cpu_times
        _last_windows_cpu_times = (idle_time, total_time)
        total_delta = total_time - previous_total
        idle_delta = idle_time - previous_idle
        if total_delta <= 0:
            return None
        return round(max(0.0, min(100.0, (1 - (idle_delta / total_delta)) * 100)), 1)
    except Exception:
        return None


def _windows_memory() -> tuple[float | None, float | None]:
    """Windows fiziksel bellek kullanimi ve uygun MB bilgisini dondurur."""
    try:
        status = _MemoryStatusEx()
        status.dwLength = c_ulong(64)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(byref(status)):
            return None, None
        return float(status.dwMemoryLoad), round(status.ullAvailPhys / (1024 * 1024), 1)
    except Exception:
        return None, None


def _linux_memory() -> tuple[float | None, float | None]:
    """Linux /proc/meminfo uzerinden bellek kullanimi ve uygun MB bilgisini dondurur."""
    try:
        values: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as file:
            for line in file:
                key, raw_value = line.split(":", 1)
                values[key] = int(raw_value.strip().split()[0])
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        if not total or available is None:
            return None, None
        used_percent = round(((total - available) / total) * 100, 1)
        return used_percent, round(available / 1024, 1)
    except Exception:
        return None, None


def _loadavg_cpu_percent() -> float | None:
    """Unix load average degerini CPU sayisina gore yaklasik yuzdeye cevirir."""
    try:
        load_1m, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        return round(min(max((load_1m / cpu_count) * 100, 0), 100), 1)
    except (AttributeError, OSError):
        return None


def get_host_resource_metrics() -> dict:
    """CPU ve bellek durumunu best-effort olarak dondurur."""
    if sys.platform.startswith("win"):
        cpu_percent = _windows_cpu_percent()
        memory_used_percent, memory_available_mb = _windows_memory()
    else:
        cpu_percent = _loadavg_cpu_percent()
        memory_used_percent, memory_available_mb = _linux_memory()

    return {
        "host_cpu_load_percent": cpu_percent,
        "host_memory_used_percent": memory_used_percent,
        "host_memory_available_mb": memory_available_mb,
    }
