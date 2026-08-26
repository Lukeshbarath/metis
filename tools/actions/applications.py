import logging
import os
import signal
import subprocess

logger = logging.getLogger(__name__)


def launch_application(command: str, args: list | None = None) -> dict:
    """Launch a local application without using a shell."""
    if not command or any(token in command for token in [";", "&&", "|", "$", "`", "*", "?", "\n"]):
        raise ValueError("Unsafe application launch command.")

    argv = [command]
    if args:
        argv.extend(args)

    try:
        process = subprocess.Popen(argv, start_new_session=True)
    except OSError as error:
        raise RuntimeError(f"Failed to launch application: {error}") from error

    logger.warning("Started application %s with pid %s", command, process.pid)
    return {"command": command, "pid": process.pid}


def kill_process(pid: int) -> dict:
    """Terminate a process by PID using SIGTERM."""
    if pid <= 0:
        raise ValueError("pid must be a positive integer.")

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError as error:
        raise FileNotFoundError(f"Process {pid} does not exist.") from error

    logger.warning("Sent SIGTERM to pid %s", pid)
    return {"pid": pid, "status": "terminated"}


TOOLS = [
    {
        "name": "launch_application",
        "description": "Launch an application without using a shell. Requires explicit confirmation.",
        "category": "actions",
        "permission": "confirmation_required",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Executable path or command name."},
                "args": {"type": "array", "description": "Optional list of command-line arguments."},
            },
            "required": ["command"],
        },
        "function_name": "launch_application",
    },
    {
        "name": "kill_process",
        "description": "Terminate a specific process by PID.",
        "category": "actions",
        "permission": "confirmation_required",
        "parameters": {
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "PID of the process to terminate."},
            },
            "required": ["pid"],
        },
        "function_name": "kill_process",
    },
]
