import os
from pathlib import Path

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MODEL = os.getenv("MODEL", "qwen2.5:7b")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
METIS_HOME = Path(os.getenv("METIS_HOME", Path(__file__).resolve().parent)).resolve()

for directory in (METIS_HOME / "memory", METIS_HOME / "knowledge", METIS_HOME / "logs"):
    directory.mkdir(parents=True, exist_ok=True)

ALLOWED_SCRIPT_ROOTS = [
    str(METIS_HOME),
    str(METIS_HOME / "memory"),
    str(METIS_HOME / "knowledge"),
    str(METIS_HOME / "logs"),
]
