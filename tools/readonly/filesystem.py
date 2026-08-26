import shutil


def get_disk_usage() -> dict:
    """Return compact disk usage data for the root filesystem."""
    usage = shutil.disk_usage("/")
    total_gb = usage.total / (1024 ** 3)
    used_gb = usage.used / (1024 ** 3)
    free_gb = usage.free / (1024 ** 3)
    return {
        "total_gb": round(total_gb, 2),
        "used_gb": round(used_gb, 2),
        "free_gb": round(free_gb, 2),
        "percent_used": round((usage.used / usage.total) * 100, 2) if usage.total else 0.0,
    }


TOOLS = [
    {
        "name": "get_disk_usage",
        "description": "Return the current disk usage for the root filesystem.",
        "category": "readonly",
        "permission": "readonly",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "function_name": "get_disk_usage",
    }
]
