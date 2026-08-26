import importlib
import logging
from pathlib import Path
from typing import Iterable, List, Tuple

from .registry import registry

logger = logging.getLogger(__name__)

CATEGORIES = ("readonly", "actions", "modules")


def iter_tool_modules() -> Iterable[Tuple[str, Path]]:
    root = Path(__file__).resolve().parent
    for category in CATEGORIES:
        category_dir = root / category
        if not category_dir.exists():
            continue
        for module_path in sorted(category_dir.glob("*.py")):
            if module_path.name.startswith("__"):
                continue
            yield category, module_path


def discover_tools() -> List[str]:
    discovered: List[str] = []

    for category, module_path in iter_tool_modules():
        module_name = f"tools.{category}.{module_path.stem}"
        try:
            module = importlib.import_module(module_name)
        except Exception as error:
            logger.warning("Failed to import tool module %s: %s", module_name, error)
            continue

        entries = getattr(module, "TOOLS", getattr(module, "TOOL_METADATA", None))
        if entries is None:
            continue
        if isinstance(entries, dict):
            entries = [entries]

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            function_name = entry.get("function_name") or entry.get("function")
            function = None
            if callable(function_name):
                function = function_name
            elif isinstance(function_name, str):
                function = getattr(module, function_name, None)

            if function is None:
                function_name = entry.get("name")
                if function_name:
                    function = getattr(module, function_name, None)

            if function is None or not callable(function):
                logger.warning("Tool module %s did not expose a callable for %s", module_name, entry.get("name"))
                continue

            registry.register_tool(
                function,
                name=entry.get("name", function.__name__),
                description=entry.get("description", f"Executes {function.__name__}."),
                category=entry.get("category", category),
                permission=entry.get("permission", "readonly"),
                arguments=entry.get("arguments", {}),
                parameters=entry.get("parameters", None),
            )
            discovered.append(entry.get("name", function.__name__))

    logger.info("Discovered %d tools", len(discovered))
    return discovered
