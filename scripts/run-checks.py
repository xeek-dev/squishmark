#!/usr/bin/env python3
"""Run CI checks locally: formatting, linting, tests, and type checking."""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

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


def run_check(name: str, cmd: list[str]) -> tuple[str, bool]:
    """Run a single check and return (name, passed)."""
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=False)
    return name, result.returncode == 0


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

    max_name_len = max(len(name) for name, _ in checks)

    print("\nRunning checks...\n")

    results: list[tuple[str, bool]] = []

    for name, cmd in checks:
        padded = name.ljust(max_name_len)
        print(f"  {padded}  ", end="", flush=True)

        name, passed = run_check(name, cmd)
        results.append((name, passed))

        print("PASS" if passed else "FAIL")

        if not passed and args.fail_fast:
            print("\nStopping early (--fail-fast)\n")
            break

    # Summary
    total = len(results)
    passed_count = sum(1 for _, p in results if p)

    print()
    if passed_count == total:
        print(f"Summary: {passed_count}/{total} checks passed")
    else:
        print(f"Summary: {passed_count}/{total} checks passed")
        failed = [name for name, p in results if not p]
        print(f"Failed:  {', '.join(failed)}")
    print()

    sys.exit(0 if passed_count == total else 1)


if __name__ == "__main__":
    main()
