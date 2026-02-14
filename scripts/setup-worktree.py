#!/usr/bin/env python3
"""Manage git worktrees in .worktrees/ directory.

Usage:
    setup-worktree.py <branch-name>                       Create worktree for branch
    setup-worktree.py <branch-name> --install             Also pip install -e from worktree
    setup-worktree.py <branch-name> --with-content        Also copy content/ directory
    setup-worktree.py <branch-name> --integration         Shorthand for --install --with-content
    setup-worktree.py --list                              List worktree directory names
    setup-worktree.py --cleanup NAME                      Remove a worktree
    setup-worktree.py --cleanup NAME --force              Remove without confirmation
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
WORKTREES_DIR = PROJECT_ROOT / ".worktrees"


def run(
    cmd: list[str],
    *,
    capture: bool = True,
    check: bool = True,
    cwd: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and return the result."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
        cwd=cwd,
    )


def slugify(branch_name: str) -> str:
    """Derive a directory name from a branch name by stripping the type prefix.

    "feat/42-dark-mode" -> "42-dark-mode"
    "fix/15-header-overflow" -> "15-header-overflow"
    "my-feature" -> "my-feature"
    """
    # Strip type prefix (everything before the first slash)
    if "/" in branch_name:
        slug = branch_name.split("/", 1)[1]
    else:
        slug = branch_name
    # Sanitize for filesystem
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def install_editable(path: Path) -> None:
    """Run pip install -e from the given path so imports resolve to its code."""
    print(f"Installing editable package from {path}...")
    try:
        run(
            [sys.executable, "-m", "pip", "install", "-e", f"{path}[dev]"],
            capture=False,
        )
        print("Editable install complete.")
    except subprocess.CalledProcessError:
        print("Warning: pip install failed. You may need to install manually:")
        print(f'  pip install -e "{path}[dev]"')


def is_installed_from(path: Path) -> bool:
    """Check if squishmark is currently editable-installed from the given path."""
    result = run(
        [sys.executable, "-m", "pip", "show", "squishmark"],
        check=False,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if line.startswith("Editable project location:"):
            location = Path(line.split(":", 1)[1].strip()).resolve()
            return str(location).startswith(str(path.resolve()))
    return False


def copy_content(worktree_path: Path) -> None:
    """Copy the content/ directory into the worktree if it exists."""
    src = PROJECT_ROOT / "content"
    dest = worktree_path / "content"

    if dest.exists():
        print("Content directory already exists in worktree, skipping copy.")
        return

    if not src.exists():
        print("No content/ directory found in main repo, skipping copy.")
        return

    print("Copying content/ into worktree...")
    shutil.copytree(src, dest)
    print(f"Copied {sum(1 for _ in dest.rglob('*') if _.is_file())} files to {dest}")


def create_worktree(
    branch_name: str,
    *,
    install: bool = False,
    with_content: bool = False,
) -> None:
    """Create a worktree in .worktrees/ for the given branch."""
    slug = slugify(branch_name)
    worktree_path = WORKTREES_DIR / slug

    print(f"Branch:   {branch_name}")
    print(f"Worktree: {worktree_path}")
    print()

    # Check if worktree already exists
    if worktree_path.exists():
        print(f"Error: Worktree directory already exists: {worktree_path}")
        sys.exit(1)

    # Check if branch already exists (local)
    result = run(["git", "branch", "--list", branch_name], cwd=PROJECT_ROOT)
    branch_exists = bool(result.stdout.strip())

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if branch_exists:
            run(
                ["git", "worktree", "add", str(worktree_path), branch_name],
                cwd=PROJECT_ROOT,
                capture=False,
            )
        else:
            run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_path)],
                cwd=PROJECT_ROOT,
                capture=False,
            )
    except subprocess.CalledProcessError:
        print("Error: Failed to create worktree.")
        sys.exit(1)

    # Post-creation setup
    if with_content:
        print()
        copy_content(worktree_path)

    if install:
        print()
        install_editable(worktree_path)

    print()
    print("=" * 60)
    print("Worktree ready!")
    print(f"  cd {worktree_path}")
    print("  python scripts/start-dev.py")
    print()
    print("When done, clean up with:")
    print(f"  python scripts/setup-worktree.py --cleanup {slug}")
    print("=" * 60)


def list_worktrees() -> None:
    """List worktree directory names from .worktrees/."""
    if not WORKTREES_DIR.exists():
        print("No active worktrees found in .worktrees/")
        return

    dirs = sorted(p.name for p in WORKTREES_DIR.iterdir() if p.is_dir())
    if not dirs:
        print("No active worktrees found in .worktrees/")
        return

    for name in dirs:
        print(name)


def cleanup_worktree(name: str, *, force: bool = False) -> None:
    """Remove a worktree and delete its associated branch."""
    worktree_path = WORKTREES_DIR / name

    # Find the branch for this worktree from git porcelain output
    result = run(["git", "worktree", "list", "--porcelain"], cwd=PROJECT_ROOT)

    branch = None
    current_path = None
    for line in result.stdout.strip().split("\n"):
        if line.startswith("worktree "):
            current_path = line[len("worktree ") :]
        elif line.startswith("branch ") and current_path == str(worktree_path):
            branch = line[len("branch ") :]
            if branch.startswith("refs/heads/"):
                branch = branch[len("refs/heads/") :]
            break

    if branch is None:
        if worktree_path.exists():
            print(f"Error: '{name}' exists at {worktree_path} but is not a registered worktree.")
        else:
            print(f"Error: No worktree found with name '{name}'.")
            print("Use --list to see active worktrees.")
        sys.exit(1)

    print(f"Worktree: {worktree_path}")
    print(f"Branch:   {branch}")

    # Check if editable install points at this worktree before removing it
    needs_reinstall = is_installed_from(worktree_path)

    # Confirmation unless --force
    if not force:
        print()
        confirm = input(f"Remove worktree '{name}' and delete branch '{branch}'? [y/N] ")
        if confirm.lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    # Remove worktree
    print("\nRemoving worktree...")
    try:
        run(
            ["git", "worktree", "remove", str(worktree_path)],
            cwd=PROJECT_ROOT,
        )
    except subprocess.CalledProcessError:
        print("  Retrying with --force...")
        result = run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=PROJECT_ROOT,
            check=False,
        )
        if result.returncode != 0:
            print(f"Error: Failed to remove worktree '{name}'. Skipping branch deletion.")
            sys.exit(1)

    # Delete local branch
    print("Deleting local branch...")
    run(
        ["git", "branch", "-D", branch],
        cwd=PROJECT_ROOT,
        check=False,
    )

    # Restore editable install to main repo if it pointed at the removed worktree
    if needs_reinstall:
        print("\nRestoring editable install to main repo...")
        install_editable(PROJECT_ROOT)

    print(f"\nCleaned up worktree '{name}'.")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Manage git worktrees in .worktrees/ directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s feat/42-dark-mode              Create worktree for branch
  %(prog)s feat/42-dark-mode --install    Also pip install -e from worktree
  %(prog)s feat/42-dark-mode --integration  Install + copy content/
  %(prog)s --list                         List active worktrees
  %(prog)s --cleanup 42-dark-mode         Remove worktree '42-dark-mode'
""",
    )

    parser.add_argument(
        "branch",
        nargs="?",
        help="Branch name to create worktree for",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List active worktrees",
    )
    parser.add_argument(
        "--cleanup",
        metavar="NAME",
        help="Remove a worktree by directory name",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt during cleanup",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Run pip install -e from the worktree after creation",
    )
    parser.add_argument(
        "--with-content",
        action="store_true",
        help="Copy content/ directory into the worktree",
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Shorthand for --install --with-content",
    )

    return parser


def main() -> None:
    """Entry point for the setup-worktree script."""
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        list_worktrees()
    elif args.cleanup:
        cleanup_worktree(args.cleanup, force=args.force)
    elif args.branch:
        install = args.install or args.integration
        with_content = args.with_content or args.integration
        create_worktree(args.branch, install=install, with_content=with_content)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
