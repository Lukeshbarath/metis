import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_memory() -> dict:
    """Return RAM and swap usage using /proc/meminfo."""
    meminfo = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            try:
                meminfo[key.strip()] = int(value.split()[0])
            except ValueError:
                continue

    total_kib = meminfo.get("MemTotal", 0)
    available_kib = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    used_kib = max(total_kib - available_kib, 0)

    swap_total_kib = meminfo.get("SwapTotal", 0)
    swap_free_kib = meminfo.get("SwapFree", 0)
    swap_used_kib = max(swap_total_kib - swap_free_kib, 0)

    return {
        "total_ram_gb": round(total_kib / 1024 / 1024, 2),
        "used_ram_gb": round(used_kib / 1024 / 1024, 2),
        "available_ram_gb": round(available_kib / 1024 / 1024, 2),
        "swap_total_gb": round(swap_total_kib / 1024 / 1024, 2),
        "swap_used_gb": round(swap_used_kib / 1024 / 1024, 2),
        "swap_free_gb": round(swap_free_kib / 1024 / 1024, 2),
    }


def get_processes(limit: int = 10) -> dict:
    """Return a compact snapshot of the most memory-heavy active processes."""
    if limit < 1:
        raise ValueError("limit must be at least 1.")

    processes = []
    for pid_dir in sorted(Path("/proc").iterdir(), key=lambda p: p.name):
        if not pid_dir.name.isdigit():
            continue
        status_path = pid_dir / "status"
        if not status_path.exists():
            continue
        try:
            status = status_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        name = "unknown"
        vmrss_kib = 0
        state = "unknown"
        for line in status.splitlines():
            if line.startswith("Name:"):
                name = line.split("\t", 1)[1].strip() if "\t" in line else line.split(":", 1)[1].strip()
            elif line.startswith("VmRSS:"):
                try:
                    vmrss_kib = int(line.split()[1])
                except (IndexError, ValueError):
                    vmrss_kib = 0
            elif line.startswith("State:"):
                state = line.split()[1] if len(line.split()) > 1 else "unknown"

        processes.append({
            "pid": int(pid_dir.name),
            "name": name,
            "rss_mb": round(vmrss_kib / 1024, 2),
            "state": state,
        })

    processes.sort(key=lambda item: item["rss_mb"], reverse=True)
    return {
        "count": min(len(processes), limit),
        "processes": processes[:limit],
    }


def get_logs(minutes: int = 10, limit: int = 25) -> dict:
    """Return recent journald entries, filtered to the last number of minutes."""
    if not 1 <= minutes <= 1440:
        raise ValueError("minutes must be between 1 and 1440.")
    if limit < 1:
        raise ValueError("limit must be at least 1.")

    command = ["journalctl", "--since", f"{minutes} minutes ago", "-n", str(limit), "--no-pager"]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as error:
        raise RuntimeError(f"Unable to read logs: {error}") from error

    if completed.returncode != 0:
        raise RuntimeError(f"journalctl failed: {completed.stderr.strip() or 'unknown error'}")

    entries = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return {
        "minutes": minutes,
        "count": len(entries),
        "entries": entries,
    }


def get_hardware() -> dict:
    """Return basic CPU and platform information."""
    cpu_model = "unknown"
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except OSError:
        cpu_model = "unknown"

    try:
        with open("/etc/os-release", "r", encoding="utf-8") as handle:
            os_name = "unknown"
            for line in handle:
                if line.startswith("NAME="):
                    os_name = line.split("=", 1)[1].strip().strip('"')
                    break
    except OSError:
        os_name = "unknown"

    cpu_count = 0
    try:
        cpu_count = sum(1 for _ in open("/proc/cpuinfo", "r", encoding="utf-8"))
    except OSError:
        cpu_count = 0

    return {
        "os": os_name,
        "cpu_model": cpu_model,
        "cpu_cores": max(1, cpu_count // 5) if cpu_count else 1,
        "platform": "linux",
    }


TOOLS = [
    {
        "name": "get_memory",
        "description": "Return current RAM and swap usage for the system.",
        "category": "readonly",
        "permission": "readonly",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "function_name": "get_memory",
    },
    {
        "name": "get_processes",
        "description": "Return the largest active processes by memory consumption.",
        "category": "readonly",
        "permission": "readonly",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of processes to return."}
            },
            "required": [],
        },
        "function_name": "get_processes",
    },
    {
        "name": "get_logs",
        "description": "Return recent system journal entries for a time window in minutes.",
        "category": "readonly",
        "permission": "readonly",
        "parameters": {
            "type": "object",
            "properties": {
                "minutes": {"type": "integer", "description": "Look back this many minutes."},
                "limit": {"type": "integer", "description": "Maximum number of log lines to return."},
            },
            "required": [],
        },
        "function_name": "get_logs",
    },
    {
        "name": "get_hardware",
        "description": "Return basic hardware and platform information.",
        "category": "readonly",
        "permission": "readonly",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "function_name": "get_hardware",
    },
]
