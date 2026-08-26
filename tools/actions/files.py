import logging
from pathlib import Path

from config import METIS_HOME

logger = logging.getLogger(__name__)


def _resolve_safe_path(path: str) -> Path:
    candidate = Path(path).expanduser().resolve()
    home_root = METIS_HOME.resolve()
    if not str(candidate).startswith(str(home_root)) and str(candidate) != str(home_root):
        raise PermissionError(f"Path '{path}' is outside the allowed Metis working area.")
    return candidate


def delete_file(path: str) -> dict:
    """Delete a file only if it is within the allowed Metis working area."""
    target = _resolve_safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")
    if not target.is_file():
        raise ValueError(f"Path is not a file: {target}")
    target.unlink()
    logger.warning("Deleted file %s", target)
    return {"deleted": str(target)}


def move_file(source: str, destination: str) -> dict:
    """Move a file only within the allowed Metis working area."""
    source_path = _resolve_safe_path(source)
    destination_path = _resolve_safe_path(destination)
    if not source_path.exists():
        raise FileNotFoundError(f"Source not found: {source_path}")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.rename(destination_path)
    logger.warning("Moved file from %s to %s", source_path, destination_path)
    return {"moved_from": str(source_path), "moved_to": str(destination_path)}


TOOLS = [
    {
        "name": "delete_file",
        "description": "Delete a file that is inside the allowed Metis working area.",
        "category": "actions",
        "permission": "confirmation_required",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to delete."}
            },
            "required": ["path"],
        },
        "function_name": "delete_file",
    },
    {
        "name": "move_file",
        "description": "Move a file from one safe location to another within the allowed Metis working area.",
        "category": "actions",
        "permission": "confirmation_required",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Current file path."},
                "destination": {"type": "string", "description": "Destination file path."},
            },
            "required": ["source", "destination"],
        },
        "function_name": "move_file",
    },
]
