import logging
import shutil
import subprocess
from pathlib import Path

from config import METIS_HOME

logger = logging.getLogger(__name__)


def _resolve_allowed_script(script_path: str) -> Path:
    candidate = Path(script_path).expanduser().resolve()
    allowed_root = METIS_HOME.resolve()
    if not str(candidate).startswith(str(allowed_root)):
        raise PermissionError(f"Script '{script_path}' is outside the allowed Metis working area.")
    if not candidate.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    if not candidate.is_file():
        raise ValueError(f"Path is not a file: {script_path}")
    if candidate.suffix.lower() not in {".py", ".sh"}:
        raise ValueError("Only .py and .sh scripts are allowed.")
    return candidate


def run_script(script_path: str, arguments: list | None = None) -> dict:
    """Execute a script only if it lives inside the Metis-controlled workspace."""
    script = _resolve_allowed_script(script_path)
    argv = list(arguments or [])
    if script.suffix.lower() == ".py":
        argv = ["python3", str(script), *argv]
    elif script.suffix.lower() == ".sh":
        argv = ["bash", str(script), *argv]

    try:
        run_result = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Script failed to execute: {error}") from error

    if run_result.returncode != 0:
        raise RuntimeError(f"Script exited with code {run_result.returncode}: {run_result.stderr.strip() or run_result.stdout.strip()}")

    logger.warning("Executed script %s", script)
    return {
        "script": str(script),
        "returncode": run_result.returncode,
        "stdout": run_result.stdout.strip()[:2000],
        "stderr": run_result.stderr.strip()[:2000],
    }


def change_volume(level: int) -> dict:
    """Adjust the default audio sink volume using a controlled API."""
    if not 0 <= level <= 100:
        raise ValueError("Volume level must be between 0 and 100.")

    volume_target = f"{level}%"
    command = None
    for candidate in (["pactl", "set-sink-volume", "@DEFAULT_SINK@", volume_target], ["amixer", "-D", "pulse", "sset", "Master", volume_target]):
        if shutil.which(candidate[0]):
            command = candidate
            break

    if command is None:
        raise RuntimeError("No supported volume control utility is available.")

    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Volume change failed: {error.stderr.strip() or error.stdout.strip()}") from error

    logger.warning("Changed volume to %s", volume_target)
    return {"volume_percent": level, "status": "updated"}


TOOLS = [
    {
        "name": "run_script",
        "description": "Execute an approved Python or shell script from the controlled Metis workspace only.",
        "category": "actions",
        "permission": "confirmation_required",
        "parameters": {
            "type": "object",
            "properties": {
                "script_path": {"type": "string", "description": "Path to the script inside the Metis working area."},
                "arguments": {"type": "array", "description": "Optional arguments passed to the script."},
            },
            "required": ["script_path"],
        },
        "function_name": "run_script",
    },
    {
        "name": "change_volume",
        "description": "Adjust the default audio volume to a percentage between 0 and 100.",
        "category": "actions",
        "permission": "confirmation_required",
        "parameters": {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Volume percentage from 0 to 100."},
            },
            "required": ["level"],
        },
        "function_name": "change_volume",
    },
]
