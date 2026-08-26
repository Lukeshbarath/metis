import json
import logging
import sys
from typing import Any, Dict, List, Optional

import requests

from config import LOG_LEVEL, METIS_HOME, MODEL, OLLAMA_URL
from tools import discover_tools, execute_tool, registry

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("metis")

SYSTEM_PROMPT = """
YYou are Metis, a local personal AI assistant.

Be concise by default. Prefer short answers unless the user
explicitly asks for detail.

Use tools when current information about the user's computer
is required.

Never invent tool results.

Respect tool permissions.

Ask for confirmation before destructive or disruptive actions."""


def build_system_prompt() -> str:
    tool_lines = []
    for tool in registry.get_all_tools():
        tool_lines.append(f"- {tool['name']} ({tool['category']}, {tool['permission']}): {tool['description']}")
    if not tool_lines:
        tool_lines.append("- No tools are currently available.")
    return SYSTEM_PROMPT + "\n\nAvailable tools:\n" + "\n".join(tool_lines)


def ask_ollama(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    try:
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=180)
        if not response.ok:
            logger.error("Ollama returned %s: %s", response.status_code, response.text)

    except requests.RequestException as error:
        logger.exception("Ollama request failed")
        raise RuntimeError(f"Ollama is unavailable or timed out: {error}") from error

    try:
        data = response.json()
        message = data["message"]
    except (ValueError, KeyError) as error:
        logger.exception("Malformed Ollama response")
        raise ValueError("Ollama returned a malformed response.") from error

    return message


def parse_tool_request(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tool_calls = message.get("tool_calls")
    if tool_calls:
        first_call = tool_calls[0]
        function = first_call.get("function", {})
        name = function.get("name")
        arguments = function.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}
        if name:
            return {"name": name, "arguments": arguments}
        return None

    content = (message.get("content") or "").strip()
    if not content:
        return None

    lines = content.splitlines()
    if len(lines) < 2 or lines[0].strip() != "TOOL":
        return None

    tool_name = lines[1].strip()
    arguments: Dict[str, Any] = {}
    if len(lines) >= 3:
        try:
            arguments = json.loads("\n".join(lines[2:]))
        except json.JSONDecodeError:
            logger.warning("Malformed tool request payload from model: %s", content)
            arguments = {}

    return {"name": tool_name, "arguments": arguments}


def execute_requested_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict):
        raise TypeError("Tool arguments must be a dictionary.")

    allowed = registry.get_tool(tool_name)
    if allowed is None:
        logger.warning("Rejected unknown tool request: %s", tool_name)
        return {"success": False, "error": f"Tool '{tool_name}' is not available."}

    confirmed = bool(arguments.pop("confirmed", False))

    # If the tool requires confirmation and the request is not already confirmed,
    # request explicit human confirmation via the interactive console.
    if allowed["permission"] in {"confirmation_required", "restricted"} and not confirmed:
        logger.info("Tool %s requires confirmation", tool_name)

        # If we are non-interactive, deny the request safely.
        if not sys.stdin or not sys.stdin.isatty():
            logger.warning("Cannot confirm tool %s in non-interactive mode", tool_name)
            return {"success": False, "error": "Tool requires confirmation but Metis is not running interactively."}

        print()
        print(f"Tool '{tool_name}' requires confirmation before execution.")
        print(f"Description: {allowed.get('description')}")
        if arguments:
            print("Arguments:")
            for k, v in arguments.items():
                print(f"  - {k}: {v}")
        else:
            print("No arguments provided.")
        print("Permission level:", allowed.get("permission"))

        choice = input("Proceed with this action? (y/N): ").strip().lower()
        if choice not in {"y", "yes"}:
            logger.info("User denied confirmation for tool %s", tool_name)
            return {"success": False, "error": "User denied confirmation."}

        # proceed with confirmed execution
        confirmed = True

    try:
        result = execute_tool(tool_name, arguments, confirmed=confirmed)
        logger.info("Executed tool %s successfully", tool_name)
        return result
    except PermissionError as error:
        logger.warning("Permission denied for tool %s: %s", tool_name, error)
        return {"success": False, "error": str(error)}
    except Exception as error:
        logger.exception("Tool execution error for %s", tool_name)
        return {"success": False, "error": str(error)}


def run_metis(user_input: str) -> str:
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_input},
    ]

    try:
        response = ask_ollama(messages, tools=registry.build_tool_definitions())
    except Exception as error:
        logger.exception("LLM interaction failed")
        return f"Metis could not contact Ollama: {error}"

    tool_request = parse_tool_request(response)
    if tool_request is None:
        return (response.get("content") or "").strip()

    tool_name = tool_request["name"]
    arguments = tool_request.get("arguments", {})
    logger.info("Detected tool request: %s with arguments %s", tool_name, arguments)

    tool_result = execute_requested_tool(tool_name, arguments)

    messages.append({"role": "assistant", "content": response.get("content") or ""})
    messages.append(
        {
            "role": "user",
            "content": (
                "Tool result:\n"
                + json.dumps(tool_result, indent=2)
                + "\n\nUse this actual information to answer the user's original question."
            ),
        }
    )

    final_response = ask_ollama(messages, tools=registry.build_tool_definitions()) 
    return (final_response.get("content") or "").strip()


def main() -> None:
    logger.info("Metis startup; discovering tools.")
    discovered = discover_tools()
    logger.info("Discovered tools: %s", discovered)
    print("Metis online.")
    print(f"Loaded {len(discovered)} tools.")
    print("Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                print("Metis: Goodbye.")
                break
            
            answer = run_metis(user_input)
            print(f"\nMetis: {answer}\n")

        except KeyboardInterrupt:
            print("\nMetis: Goodbye.")
            break
        except Exception as error:
            logger.exception("Unexpected Metis error")
            print(f"\n[Metis error] {error}\n")


if __name__ == "__main__":
    main()
