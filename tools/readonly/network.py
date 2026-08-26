import os


def _read_first_line(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.readline().strip()
    except OSError:
        return "unknown"


def get_network_status() -> dict:
    """Return a compact summary of active network interfaces and IPv4 addresses."""
    interfaces = []
    for name in sorted(os.listdir("/sys/class/net")):
        address_path = f"/sys/class/net/{name}/address"
        operstate = _read_first_line(f"/sys/class/net/{name}/operstate")
        ipv4 = _read_first_line(f"/proc/net/fib_trie")
        # fib_trie is too broad; use /proc/net/route for routing and interface lists.
        interfaces.append(
            {
                "name": name,
                "mac": _read_first_line(address_path),
                "status": operstate,
                "ipv4": "unknown",
            }
        )

    default_route = None
    try:
        with open("/proc/net/route", "r", encoding="utf-8") as handle:
            lines = handle.read().strip().splitlines()[1:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "00000000":
                    default_route = parts[0]
                    break
    except OSError:
        default_route = None

    for iface in interfaces:
        iface_name = iface["name"]
        try:
            with open(f"/proc/net/fib_trie", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith(f"{iface_name} "):
                        continue
        except OSError:
            pass

    try:
        with open("/proc/net/fib_trie", "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        for iface in interfaces:
            iface_name = iface["name"]
            found = False
            for line in lines:
                if line.strip().startswith("32 host") and iface_name in line:
                    found = True
            if found:
                iface["ipv4"] = "assigned"
    except OSError:
        pass

    return {
        "interfaces": interfaces,
        "default_route": default_route,
        "summary": f"{len(interfaces)} interface(s) detected",
    }


TOOLS = [
    {
        "name": "get_network_status",
        "description": "Return a compact network status summary for the active interfaces.",
        "category": "readonly",
        "permission": "readonly",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "function_name": "get_network_status",
    }
]
