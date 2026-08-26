import logging
from typing import Any, Callable, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

VALID_PERMISSIONS = {
    "readonly",
    "safe",
    "confirmation_required",
    "restricted",
}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        function: Callable[..., Any],
        *,
        name: Optional[str] = None,
        description: str = "",
        category: str = "unknown",
        permission: str = "readonly",
        arguments: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not callable(function):
            raise TypeError("Tool registration requires a callable.")

        tool_name = (name or getattr(function, "__name__", "") or "unnamed_tool").strip()
        if not tool_name:
            raise ValueError("Every tool must have a valid name.")

        permission = permission.lower()
        if permission not in VALID_PERMISSIONS:
            raise ValueError(f"Unsupported permission '{permission}' for tool '{tool_name}'.")

        tool_definition = {
            "name": tool_name,
            "description": description or f"Executes the {tool_name} capability.",
            "category": category.lower(),
            "permission": permission,
            "function": function,
            "arguments": dict(arguments or {}),
        }
        if parameters is not None:
            tool_definition["parameters"] = dict(parameters)

        self._tools[tool_name] = tool_definition
        logger.info("Registered tool %s in category %s with permission %s", tool_name, category, permission)
        return tool_definition

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def get_all_tools(self) -> List[Dict[str, Any]]:
        return [self._tools[name] for name in sorted(self._tools)]

    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        return [tool for tool in self.get_all_tools() if tool["category"] == category.lower()]

    def execute_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None, *, confirmed: bool = False) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            arguments = dict(arguments or {})

        tool = self.get_tool(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")

        if tool["permission"] in {"confirmation_required", "restricted"} and not confirmed:
            raise PermissionError(f"Tool '{name}' requires confirmation before execution.")

        try:
            result = tool["function"](**arguments)
        except TypeError as error:
            raise TypeError(f"Invalid arguments for '{name}': {error}") from error
        except Exception as error:
            logger.exception("Tool execution failed for %s", name)
            raise RuntimeError(f"Tool '{name}' failed: {error}") from error

        return {"success": True, "tool": name, "result": result}

    def build_tool_definitions(self) -> List[Dict[str, Any]]:
        tool_definitions = []

        for tool in self.get_all_tools():
            parameters = tool.get(
                "parameters",
                {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            )

            definition = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": parameters,
                },
            }

            tool_definitions.append(definition)

        return tool_definitions

    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


registry = ToolRegistry()


def register_tool(function: Callable[..., Any], **kwargs: Any) -> Dict[str, Any]:
    return registry.register_tool(function, **kwargs)


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    return registry.get_tool(name)


def get_all_tools() -> List[Dict[str, Any]]:
    return registry.get_all_tools()


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    return registry.get_tools_by_category(category)


def execute_tool(name: str, arguments: Optional[Dict[str, Any]] = None, *, confirmed: bool = False) -> Dict[str, Any]:
    return registry.execute_tool(name, arguments, confirmed=confirmed)
