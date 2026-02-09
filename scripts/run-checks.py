#!/usr/bin/env python3
"""Run CI checks locally: formatting, linting, tests, and type checking."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# ANSI color codes — only used when the terminal supports them
_USE_COLOR = sys.stdout.isatty()


def _color(code: str, text: str) -> str:
    if _USE_COLOR:
        return f"\033[{code}m{text}\033[0m"
    return text


def green(text: str) -> str:
    return _color("32", text)


def red(text: str) -> str:
    return _color("31", text)


def bold(text: str) -> str:
    return _color("1", text)


def dim(text: str) -> str:
    return _color("2", text)


# Each check: (display name, command)
CHECKS: list[tuple[str, list[str]]] = [
    ("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
    ("pytest", [sys.executable, "-m", "pytest"]),
    ("pyright", [sys.executable, "-m", "pyright"]),
]

DOCKER_CHECK: tuple[str, list[str]] = (
    "docker build",
    ["docker", "build", "-t", "squishmark", "."],
)


def run_check(name: str, cmd: list[str]) -> tuple[str, bool, float]:
    """Run a single check and return (name, passed, duration_seconds)."""
    start = time.monotonic()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=False)
    elapsed = time.monotonic() - start
    passed = result.returncode == 0
    return name, passed, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CI checks locally.")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure instead of running all checks.",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Also run docker build (skipped by default, it's slow).",
    )
    args = parser.parse_args()

    checks = list(CHECKS)
    if args.docker:
        checks.append(DOCKER_CHECK)

    # Longest name for alignment
    max_name_len = max(len(name) for name, _ in checks)

    print(f"\n{bold('Running checks...')}\n")

    results: list[tuple[str, bool, float]] = []

    for name, cmd in checks:
        padded = name.ljust(max_name_len)
        # Print the check name before running so the user sees live output
        print(f"  {bold(padded)}  ", end="", flush=True)

        name, passed, elapsed = run_check(name, cmd)
        results.append((name, passed, elapsed))

        status = green("PASS") if passed else red("FAIL")
        print(f"{status}  {dim(f'({elapsed:.1f}s)')}")

        if not passed and args.fail_fast:
            print(f"\n{red('Stopping early (--fail-fast)')}\n")
            break

    # Summary
    total = len(results)
    passed_count = sum(1 for _, passed, _ in results if passed)

    print()
    if passed_count == total:
        print(f"{bold('Summary:')} {green(f'{passed_count}/{total} checks passed')}")
    else:
        print(f"{bold('Summary:')} {red(f'{passed_count}/{total} checks passed')}")

        failed = [name for name, passed, _ in results if not passed]
        print(f"{bold('Failed:')}  {', '.join(failed)}")
    print()

    sys.exit(0 if passed_count == total else 1)


if __name__ == "__main__":
    main()
