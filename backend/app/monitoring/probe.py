import ipaddress
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

CREATE_NO_WINDOW: int = (
    subprocess.CREATE_NO_WINDOW
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW")
    else 0
)


def classify(exit_code: int, output_bytes: bytes, ip: str) -> bool:
    """Classify reachability from raw ping exit code and output bytes.

    Online requires exit code 0, case-insensitive 'TTL=' in output bytes,
    and the target IP present as ASCII. The output bytes are never decoded as text.
    Anything else is considered Offline.
    """
    if exit_code != 0:
        return False

    if not output_bytes:
        return False

    if b"ttl=" not in output_bytes.lower():
        return False

    try:
        ip_bytes = ip.encode("ascii")
    except UnicodeEncodeError:
        return False

    return ip_bytes in output_bytes


def _get_ping_executable() -> str:
    """Locate the system ping executable on Windows, falling back to 'ping'."""
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    ping_path = Path(system_root) / "System32" / "PING.EXE"
    if ping_path.is_file():
        return str(ping_path)
    return "ping"


def ping_host(ip: str) -> bool:
    """Probe an IPv4 host reachability via native OS ping command.

    Validates that ip is a valid IPv4Address first. Executes without shell,
    enforcing a hard 3-second timeout and suppressing console windows on Windows.
    Catches all exceptions, logs them, and returns False without raising.
    """
    try:
        ipaddress.IPv4Address(ip)
    except (ipaddress.AddressValueError, ValueError):
        logger.warning("Invalid IPv4 address provided for ping: %r", ip)
        return False

    ping_exe = _get_ping_executable()
    cmd = [ping_exe, "-n", "1", "-w", "1000", ip]

    try:
        result = subprocess.run(
            cmd,
            shell=False,
            capture_output=True,
            timeout=3.0,
            creationflags=CREATE_NO_WINDOW,
        )
        return classify(result.returncode, result.stdout, ip)
    except subprocess.TimeoutExpired:
        logger.warning("Ping subprocess timed out for host %s", ip)
        return False
    except Exception as exc:
        logger.warning("Ping execution failed for host %s: %s", ip, exc)
        return False
