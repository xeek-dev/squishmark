#!/usr/bin/env python3
"""Development server startup script. Works on Mac, Windows, and Linux."""

import os
import subprocess
import sys
from pathlib import Path

# Project root is parent of scripts/
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def ensure_dependencies() -> None:
    """Ensure the project is installed with dependencies."""
    try:
        import squishmark  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        print("Installing dependencies from pyproject.toml...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(PROJECT_ROOT)],
            check=True,
        )
        print()


def main() -> None:
    """Start the development server with local content."""
    os.chdir(PROJECT_ROOT)
    ensure_dependencies()

    # Set environment variables for local development
    env = os.environ.copy()
    env.setdefault("GITHUB_CONTENT_REPO", f"file://{PROJECT_ROOT / 'content'}")
    env.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'squishmark.db'}")

    # Ensure data directory exists
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)

    # Parse arguments
    host = "127.0.0.1"
    port = "8000"
    reload = True

    for arg in sys.argv[1:]:
        if arg.startswith("--host="):
            host = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = arg.split("=", 1)[1]
        elif arg == "--no-reload":
            reload = False

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

    print(f"Starting dev server at http://{host}:{port}")
    print(f"Content: {env['GITHUB_CONTENT_REPO']}")
    print(f"Database: {env['DATABASE_URL']}")
    print()

    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
