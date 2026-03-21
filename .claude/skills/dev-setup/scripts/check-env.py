#!/usr/bin/env python3
"""Check that the SquishMark development environment is ready."""

import os
import sys
from pathlib import Path


def check(label: str, condition: bool, fix: str) -> bool:
    if condition:
        print(f"  OK  {label}")
    else:
        print(f"  FAIL  {label}")
        print(f"        Fix: {fix}")
    return condition


def main() -> None:
    root = Path(__file__).resolve().parents[3]  # .claude/skills/dev-setup/scripts -> repo root
    os.chdir(root)

    print("Checking SquishMark dev environment...\n")
    checks = []

    # venv exists
    venv = root / ".venv"
    checks.append(
        check(
            "Virtual environment exists",
            venv.is_dir(),
            "python -m venv .venv",
        )
    )

    # venv is active
    checks.append(
        check(
            "Virtual environment is active",
            sys.prefix != sys.base_prefix,
            "source .venv/bin/activate",
        )
    )

    # package is importable
    try:
        import squishmark  # noqa: F401

        importable = True
    except ImportError:
        importable = False
    checks.append(
        check(
            "squishmark package installed",
            importable,
            'pip install -e ".[dev]"',
        )
    )

    # content directory
    checks.append(
        check(
            "content/ directory exists",
            (root / "content").is_dir(),
            "Create a content/ directory with posts/, pages/, and config.yml",
        )
    )

    # data directory
    data_dir = root / "data"
    checks.append(
        check(
            "data/ directory exists",
            data_dir.is_dir(),
            "mkdir data",
        )
    )

    print()
    passed = sum(checks)
    total = len(checks)
    if passed == total:
        print(f"All {total} checks passed.")
    else:
        print(f"{passed}/{total} checks passed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
