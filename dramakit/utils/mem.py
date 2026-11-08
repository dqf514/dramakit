"""How much room this process is using.

A MemoryError that is not a big string is a process that ran out of
room, and the only way to know where it went is to look at it while it
happens.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def rss_mb() -> float:
    """This process's working set, in megabytes."""
    try:
        counters = _PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb)
        if not ok:
            return 0.0
        return counters.WorkingSetSize / 1048576.0
    except Exception:  # noqa: BLE001
        return 0.0


def free_mb() -> float:
    """The machine's free memory, in megabytes."""
    try:
        class _MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_size_t),
                ("ullAvailPhys", ctypes.c_size_t),
                ("ullTotalPageFile", ctypes.c_size_t),
                ("ullAvailPageFile", ctypes.c_size_t),
                ("ullTotalVirtual", ctypes.c_size_t),
                ("ullAvailVirtual", ctypes.c_size_t),
                ("ullAvailExtendedVirtual", ctypes.c_size_t),
            ]
        st = _MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(st)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            return 0.0
        return st.ullAvailPhys / 1048576.0
    except Exception:  # noqa: BLE001
        return 0.0
