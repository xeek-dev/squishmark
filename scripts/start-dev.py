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
    python scripts/start-dev.py --stop-all        # stop all servers
    python scripts/start-dev.py --restart -b      # restart default server
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
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
        return data.get("servers", [])
    except (json.JSONDecodeError, KeyError):
        return []


def _write_registry(servers: list[dict]) -> None:
    """Write the server registry to disk."""
    REGISTRY_PATH.write_text(json.dumps({"servers": servers}, indent=2) + "\n")


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission to signal it
        return True
    return True


def _kill_pid(pid: int) -> bool:
    """Kill a process by PID. Returns True if successfully killed."""
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except (ProcessLookupError, PermissionError):
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
        pass
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
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_registry(servers)


def _deregister_server(name: str) -> None:
    """Remove a server entry from the registry by name."""
    servers = _read_registry()
    servers = [s for s in servers if s["name"] != name]
    _write_registry(servers)


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


def cmd_stop(name: str) -> None:
    """Stop a specific server by name."""
    servers = _read_registry()
    entry = _find_server(servers, name)
    if entry is None:
        print(f"No tracked server named '{name}'.")
        sys.exit(1)

    pid = entry["pid"]
    if _is_pid_alive(pid):
        if _kill_pid(pid):
            print(f"Stopped server '{name}' (PID {pid}).")
        else:
            print(f"Failed to stop server '{name}' (PID {pid}).")
            sys.exit(1)
    else:
        print(f"Server '{name}' (PID {pid}) was already stopped (stale entry removed).")

    _deregister_server(name)


def cmd_stop_all() -> None:
    """Stop all tracked servers."""
    servers = _read_registry()
    if not servers:
        print("No tracked servers.")
        return

    for s in servers:
        pid = s["pid"]
        name = s["name"]
        if _is_pid_alive(pid):
            if _kill_pid(pid):
                print(f"Stopped '{name}' (PID {pid}).")
            else:
                print(f"Failed to stop '{name}' (PID {pid}).")
        else:
            print(f"'{name}' (PID {pid}) was already stopped.")

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
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the development server with local content."""
    os.chdir(PROJECT_ROOT)

    # Parse arguments
    host = "127.0.0.1"
    port = "8000"
    reload = True
    background = False
    name: str | None = None
    action: str | None = None  # "list", "stop", "stop-all", "restart"
    stop_target: str | None = None  # name for --stop

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--host="):
            host = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = arg.split("=", 1)[1]
        elif arg == "--no-reload":
            reload = False
        elif arg in ("-b", "--background"):
            background = True
        elif arg.startswith("--name="):
            name = arg.split("=", 1)[1]
        elif arg == "--name" and i + 1 < len(args) and not args[i + 1].startswith("-"):
            i += 1
            name = args[i]
        elif arg == "--list":
            action = "list"
        elif arg == "--stop-all":
            action = "stop-all"
        elif arg == "--stop":
            action = "stop"
            # Check for optional name argument
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                i += 1
                stop_target = args[i]
        elif arg == "--restart":
            action = "restart"
        i += 1

    # Default name: current git branch or "default"
    if name is None:
        name = _get_git_branch()

    # Handle management commands
    if action == "list":
        cmd_list()
        return

    if action == "stop":
        cmd_stop(stop_target or name)
        return

    if action == "stop-all":
        cmd_stop_all()
        return

    if action == "restart":
        # Stop the server if it's running, then fall through to start
        servers = _read_registry()
        entry = _find_server(servers, name)
        if entry is not None:
            pid = entry["pid"]
            if _is_pid_alive(pid):
                _kill_pid(pid)
                print(f"Stopped '{name}' (PID {pid}).")
            _deregister_server(name)

    # --- Start server ---
    ensure_dependencies()

    # Set environment variables for local development
    env = os.environ.copy()
    env.setdefault("GITHUB_CONTENT_REPO", f"file://{PROJECT_ROOT / 'content'}")
    env.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'squishmark.db'}")

    # Ensure data directory exists
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)

    # Clean stale entries and check for port conflicts
    servers = _clean_stale(_read_registry())
    _write_registry(servers)
    port_int = int(port)
    for s in servers:
        if s["port"] == port_int and s["name"] != name:
            if _is_pid_alive(s["pid"]):
                print(
                    f"Error: Port {port} is already in use by server '{s['name']}' "
                    f"(PID {s['pid']}). Use --restart or --stop first."
                )
                sys.exit(1)
            else:
                # Stale entry, clean it up
                _deregister_server(s["name"])

    # Check if this name already has a running server
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

    if background:
        process = subprocess.Popen(cmd, env=env)
        _register_server(name, process.pid, port_int, branch)
        print(f"Server '{name}' started in background (PID: {process.pid})")
    else:
        # Register foreground server too, deregister on exit
        _register_server(name, os.getpid(), port_int, branch)
        try:
            subprocess.run(cmd, env=env, check=True)
        except KeyboardInterrupt:
            print("\nServer stopped.")
        finally:
            _deregister_server(name)


if __name__ == "__main__":
    main()
