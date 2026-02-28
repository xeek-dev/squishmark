#!/usr/bin/env python3
"""Development server startup script with multi-server management.

Works on Mac, Windows, and Linux.

Usage:
    python scripts/start-dev.py                  # foreground on :8000
    python scripts/start-dev.py -b               # background on :8000
    python scripts/start-dev.py -b --port=8001   # background on :8001
    python scripts/start-dev.py --name=api -b    # named background instance
    python scripts/start-dev.py --list            # show all tracked servers
    python scripts/start-dev.py --stop            # stop default server
    python scripts/start-dev.py --stop api        # stop named server
    python scripts/start-dev.py --stop 12345      # stop server by PID
    python scripts/start-dev.py --stop-all        # stop all servers
    python scripts/start-dev.py --restart -b      # restart default server
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Project root is parent of scripts/
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
REGISTRY_PATH = PROJECT_ROOT / ".dev-servers.json"


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def _read_registry() -> list[dict]:
    """Read the server registry, returning a list of server entries."""
    if not REGISTRY_PATH.exists():
        return []
    try:
        data = json.loads(REGISTRY_PATH.read_text())
        if not isinstance(data, dict):
            return []
        servers = data.get("servers", [])
        if not isinstance(servers, list):
            return []
        return servers
    except (json.JSONDecodeError, TypeError, AttributeError):
        return []


def _write_registry(servers: list[dict]) -> None:
    """Write the server registry to disk."""
    REGISTRY_PATH.write_text(json.dumps({"servers": servers}, indent=2) + "\n")


if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259

    def _is_pid_alive(pid: int) -> bool:
        """Check if a process with the given PID is still running (Windows)."""
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.wintypes.DWORD()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == _STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(handle)

else:

    def _is_pid_alive(pid: int) -> bool:
        """Check if a process with the given PID is still running (POSIX)."""
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we don't have permission to signal it
            return True
        return True


def _kill_registered_pid(pid: int, servers: list[dict] | None = None) -> bool:
    """Kill a process by PID, but only if it exists in the server registry.

    Returns True if successfully killed.
    """
    if servers is None:
        servers = _read_registry()
    registered_pids = {s["pid"] for s in servers}
    if pid not in registered_pids:
        print(f"Error: PID {pid} is not in the server registry. Refusing to kill.")
        return False
    try:
        if sys.platform == "win32":
            # Use taskkill /T to kill the entire process tree (uvicorn + workers)
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
            )
            return result.returncode == 0
        else:
            os.kill(pid, signal.SIGTERM)
            return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _get_git_branch() -> str:
    """Return the current git branch slug, or 'default'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        print("Warning: git is not installed. Using 'default' as server name.")
    return "default"


def _clean_stale(servers: list[dict]) -> list[dict]:
    """Remove entries whose PIDs are no longer alive."""
    return [s for s in servers if _is_pid_alive(s["pid"])]


def _find_server(servers: list[dict], name: str) -> dict | None:
    """Find a server entry by name."""
    for s in servers:
        if s["name"] == name:
            return s
    return None


def _find_server_by_pid(servers: list[dict], pid: int) -> dict | None:
    """Find a server entry by PID."""
    for s in servers:
        if s["pid"] == pid:
            return s
    return None


def _register_server(name: str, pid: int, port: int, branch: str) -> None:
    """Add a server entry to the registry."""
    servers = _read_registry()
    # Remove any stale entry with the same name
    servers = [s for s in servers if s["name"] != name]
    servers.append(
        {
            "name": name,
            "pid": pid,
            "port": port,
            "branch": branch,
            "started_at": datetime.now(UTC).isoformat(),
        }
    )
    _write_registry(servers)


def _deregister_server(name: str) -> None:
    """Remove a server entry from the registry by name."""
    servers = _read_registry()
    servers = [s for s in servers if s["name"] != name]
    _write_registry(servers)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_port_conflict(servers: list[dict], port: int, name: str) -> None:
    """Check if the port is already in use by another server. Exits on conflict."""
    for s in servers:
        if s["port"] == port and s["name"] != name:
            if _is_pid_alive(s["pid"]):
                print(
                    f"Error: Port {port} is already in use by server '{s['name']}' "
                    f"(PID {s['pid']}). Use --restart or --stop first."
                )
                sys.exit(1)
            else:
                # Stale entry, clean it up
                _deregister_server(s["name"])


def _check_existing_server(name: str) -> None:
    """Check if a server with this name is already running. Exits on conflict."""
    entry = _find_server(_read_registry(), name)
    if entry is not None and _is_pid_alive(entry["pid"]):
        print(
            f"Error: Server '{name}' is already running (PID {entry['pid']}, port {entry['port']}). "
            f"Use --restart or --stop first."
        )
        sys.exit(1)
    elif entry is not None:
        # Stale entry, clean it up
        _deregister_server(name)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_list() -> None:
    """Show all tracked servers with status."""
    servers = _read_registry()
    if not servers:
        print("No tracked servers.")
        return

    # Header
    print(f"{'NAME':<20} {'PID':<8} {'PORT':<7} {'BRANCH':<30} {'STATUS':<8} {'STARTED'}")
    print("-" * 100)

    for s in servers:
        alive = _is_pid_alive(s["pid"])
        status = "running" if alive else "stale"
        started = s.get("started_at", "?")
        print(f"{s['name']:<20} {s['pid']:<8} {s['port']:<7} {s.get('branch', '?'):<30} {status:<8} {started}")

    stale_count = sum(1 for s in servers if not _is_pid_alive(s["pid"]))
    if stale_count:
        print(f"\n{stale_count} stale server(s). Use --stop NAME or --stop-all to clean up.")


def _stop_entry(entry: dict, servers: list[dict]) -> None:
    """Stop a single server entry and deregister it."""
    pid = entry["pid"]
    name = entry["name"]
    if _is_pid_alive(pid):
        if _kill_registered_pid(pid, servers):
            print(f"Stopped '{name}' (PID {pid}).")
            _deregister_server(name)
        else:
            print(f"Failed to stop '{name}' (PID {pid}). Entry kept in registry.")
    else:
        print(f"'{name}' (PID {pid}) was already stopped.")
        _deregister_server(name)


def cmd_stop(target: str) -> None:
    """Stop a server by name or PID."""
    servers = _read_registry()

    # Try name lookup first
    entry = _find_server(servers, target)
    if entry is not None:
        _stop_entry(entry, servers)
        return

    # Try PID lookup
    try:
        pid = int(target)
        entry = _find_server_by_pid(servers, pid)
        if entry is not None:
            _stop_entry(entry, servers)
            return
    except ValueError:
        # Target is not a numeric PID; fall through to "not found" message below
        pass

    print(f"No tracked server matching '{target}' (looked up by name and PID).")
    sys.exit(1)


def cmd_stop_all() -> None:
    """Stop all tracked servers."""
    servers = _read_registry()
    if not servers:
        print("No tracked servers.")
        return

    for s in servers:
        _stop_entry(s, servers)

    _write_registry([])


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------


def ensure_dependencies() -> None:
    """Ensure the project is installed with dependencies."""
    try:
        import uvicorn  # noqa: F401

        import squishmark  # noqa: F401
    except ImportError:
        print("Installing dependencies from pyproject.toml...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(PROJECT_ROOT)],
            check=True,
        )
        print()


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the dev server script."""
    parser = argparse.ArgumentParser(
        description="Development server startup script with multi-server management.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("-b", "--background", action="store_true", help="Run in background mode")
    parser.add_argument("--name", default=None, help="Server instance name (default: git branch)")

    # Management commands (mutually exclusive)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="Show all tracked servers")
    group.add_argument(
        "--stop",
        nargs="?",
        const="__default__",
        metavar="NAME_OR_PID",
        help="Stop a server by name or PID (default: current branch)",
    )
    group.add_argument("--stop-all", action="store_true", help="Stop all tracked servers")
    group.add_argument("--restart", action="store_true", help="Restart the server")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Start the development server with local content. Returns exit code."""
    os.chdir(PROJECT_ROOT)

    parser = _build_parser()
    args = parser.parse_args()

    host = args.host
    port = args.port
    reload = not args.no_reload
    background = args.background
    name = args.name

    # Default name: current git branch or "default"
    if name is None:
        name = _get_git_branch()

    # Handle management commands
    if args.list:
        cmd_list()
        return 0

    if args.stop is not None:
        target = name if args.stop == "__default__" else args.stop
        cmd_stop(target)
        return 0

    if args.stop_all:
        cmd_stop_all()
        return 0

    if args.restart:
        # Stop the server if it's running, then fall through to start
        servers = _read_registry()
        entry = _find_server(servers, name)
        if entry is not None:
            pid = entry["pid"]
            if _is_pid_alive(pid):
                _kill_registered_pid(pid, servers)
                print(f"Stopped '{name}' (PID {pid}).")
            _deregister_server(name)

    # --- Start server ---
    ensure_dependencies()

    # Set environment variables for local development
    env = os.environ.copy()
    env.setdefault("DEBUG", "true")
    content_path = PROJECT_ROOT / "content"
    db_path = PROJECT_ROOT / "data" / "squishmark.db"
    env.setdefault("GITHUB_CONTENT_REPO", content_path.as_uri())
    env.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")

    # Ensure data directory exists
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)

    # Clean stale entries and check for port conflicts
    servers = _clean_stale(_read_registry())
    _write_registry(servers)
    _check_port_conflict(servers, port, name)
    _check_existing_server(name)

    # Build uvicorn command
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "squishmark.main:app",
        f"--host={host}",
        f"--port={port}",
    ]
    if reload:
        cmd.append("--reload")

    branch = _get_git_branch()

    print(f"Starting dev server at http://{host}:{port}")
    print(f"Content: {env['GITHUB_CONTENT_REPO']}")
    print(f"Database: {env['DATABASE_URL']}")
    print(f"Name: {name}")
    if background:
        print("Running in background mode")
    print()

    # On Windows, put the child in its own process group so we can signal it
    # independently. Background servers also get CREATE_NO_WINDOW to detach
    # from the console.
    popen_kwargs: dict = {"env": env}
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP
        if background:
            flags |= subprocess.CREATE_NO_WINDOW
        popen_kwargs["creationflags"] = flags

    if background:
        process = subprocess.Popen(cmd, **popen_kwargs)
        _register_server(name, process.pid, port, branch)
        print(f"Server '{name}' started in background (PID: {process.pid})")
        return 0
    else:
        # Use Popen so we register the actual uvicorn child PID
        process = subprocess.Popen(cmd, **popen_kwargs)
        _register_server(name, process.pid, port, branch)
        try:
            return process.wait()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return 0
        finally:
            _deregister_server(name)


if __name__ == "__main__":
    sys.exit(main())
