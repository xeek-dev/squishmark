#!/usr/bin/env python3
"""Automate git worktree creation from GitHub issues.

Usage:
    setup-worktree.py <issue-number>          Create worktree from issue
    setup-worktree.py <issue-number> --type=fix  Override branch type
    setup-worktree.py --list                  List active worktrees
    setup-worktree.py --cleanup NAME          Remove a worktree
    setup-worktree.py --cleanup NAME --force  Remove even if PR not merged
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
WORKTREES_DIR = PROJECT_ROOT / ".worktrees"

BRANCH_TYPES = [
    "feat",
    "fix",
    "chore",
    "test",
    "docs",
    "refactor",
    "perf",
    "style",
    "build",
    "ci",
]

LABEL_TO_TYPE: dict[str, str] = {
    "bug": "fix",
    "enhancement": "feat",
    "documentation": "docs",
    "dx": "chore",
}


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


def slugify(title: str, max_length: int = 50) -> str:
    """Convert an issue title to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def fetch_issue(issue_number: int) -> dict:
    """Fetch issue title and labels from GitHub."""
    try:
        result = run(["gh", "issue", "view", str(issue_number), "--json", "title,labels"])
    except subprocess.CalledProcessError:
        print(f"Error: Could not fetch issue #{issue_number}.")
        print("Make sure `gh` is installed and authenticated.")
        sys.exit(1)

    return json.loads(result.stdout)


def infer_branch_type(labels: list[dict]) -> str | None:
    """Infer branch type from issue labels. Returns None if ambiguous."""
    label_names = {label["name"].lower() for label in labels}
    matches = []
    for label_name, branch_type in LABEL_TO_TYPE.items():
        if label_name in label_names:
            matches.append(branch_type)

    # Deduplicate — multiple labels could map to the same type
    unique_matches = list(dict.fromkeys(matches))
    if len(unique_matches) == 1:
        return unique_matches[0]
    return None


def prompt_branch_type() -> str:
    """Prompt the user to select a branch type."""
    print("Could not auto-detect branch type from issue labels.")
    print("Select a branch type:")
    for i, t in enumerate(BRANCH_TYPES, 1):
        print(f"  {i:2d}. {t}")

    while True:
        choice = input("\nEnter number or type name: ").strip()
        if choice in BRANCH_TYPES:
            return choice
        try:
            idx = int(choice)
            if 1 <= idx <= len(BRANCH_TYPES):
                return BRANCH_TYPES[idx - 1]
        except ValueError:
            pass
        print("Invalid choice. Try again.")


def create_worktree(issue_number: int, branch_type: str | None = None) -> None:
    """Create a worktree from a GitHub issue."""
    issue = fetch_issue(issue_number)
    title = issue["title"]
    labels = issue.get("labels", [])

    # Determine branch type
    if branch_type:
        if branch_type not in BRANCH_TYPES:
            print(f"Error: Unknown branch type '{branch_type}'.")
            print(f"Valid types: {', '.join(BRANCH_TYPES)}")
            sys.exit(1)
    else:
        branch_type = infer_branch_type(labels)
        if branch_type is None:
            branch_type = prompt_branch_type()

    slug = slugify(title)
    branch_name = f"{branch_type}/{issue_number}-{slug}"
    worktree_path = WORKTREES_DIR / slug

    print(f"Issue:    #{issue_number} — {title}")
    print(f"Branch:   {branch_name}")
    print(f"Worktree: {worktree_path}")
    print()

    # Check if worktree already exists
    if worktree_path.exists():
        print(f"Error: Worktree directory already exists: {worktree_path}")
        sys.exit(1)

    # Check if branch already exists
    result = run(
        ["git", "branch", "--list", branch_name],
        cwd=PROJECT_ROOT,
    )
    if result.stdout.strip():
        print(f"Error: Branch '{branch_name}' already exists.")
        sys.exit(1)

    # Create worktree with new branch
    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        run(
            ["git", "worktree", "add", "-b", branch_name, str(worktree_path)],
            cwd=PROJECT_ROOT,
            capture=False,
        )
    except subprocess.CalledProcessError:
        print("Error: Failed to create worktree.")
        sys.exit(1)

    # Install dependencies in the worktree
    print("\nInstalling dependencies...")
    try:
        run(
            [sys.executable, "-m", "pip", "install", "-e", str(worktree_path)],
            capture=False,
        )
    except subprocess.CalledProcessError:
        print("Warning: Failed to install dependencies. You may need to install manually.")

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
    """List active worktrees with branch and PR info."""
    result = run(["git", "worktree", "list", "--porcelain"], cwd=PROJECT_ROOT)
    worktrees = parse_worktree_list(result.stdout)

    # Filter to only worktrees under .worktrees/
    managed = [wt for wt in worktrees if WORKTREES_DIR.as_posix() in wt.get("path", "")]

    if not managed:
        print("No active worktrees found in .worktrees/")
        return

    print(f"{'Name':<30} {'Branch':<40} {'PR':>6}")
    print("-" * 78)

    for wt in managed:
        path = Path(wt["path"])
        name = path.name
        branch = wt.get("branch", "detached")
        # Strip refs/heads/ prefix
        if branch.startswith("refs/heads/"):
            branch = branch[len("refs/heads/") :]

        # Check for PR
        pr_info = get_pr_status(branch)

        print(f"{name:<30} {branch:<40} {pr_info:>6}")


def parse_worktree_list(output: str) -> list[dict[str, str]]:
    """Parse `git worktree list --porcelain` output."""
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in output.strip().split("\n"):
        if not line.strip():
            if current:
                worktrees.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line[len("worktree ") :]
        elif line.startswith("branch "):
            current["branch"] = line[len("branch ") :]
        elif line == "bare":
            current["bare"] = "true"
        elif line == "detached":
            current["branch"] = "detached"

    if current:
        worktrees.append(current)

    return worktrees


def get_pr_status(branch: str) -> str:
    """Get PR status for a branch. Returns a short status string."""
    try:
        result = run(
            ["gh", "pr", "list", "--head", branch, "--json", "number,state", "--limit", "1"],
            check=False,
        )
        if result.returncode != 0:
            return "?"
        prs = json.loads(result.stdout)
        if not prs:
            return "none"
        pr = prs[0]
        state = pr["state"].lower()
        number = pr["number"]
        if state == "merged":
            return f"#{number} M"
        elif state == "open":
            return f"#{number} O"
        elif state == "closed":
            return f"#{number} C"
        return f"#{number}"
    except Exception:
        return "?"


def cleanup_worktree(name: str, *, force: bool = False) -> None:
    """Remove a worktree and its associated branch."""
    worktree_path = WORKTREES_DIR / name

    # Find the branch for this worktree
    result = run(["git", "worktree", "list", "--porcelain"], cwd=PROJECT_ROOT)
    worktrees = parse_worktree_list(result.stdout)

    branch = None
    for wt in worktrees:
        if wt.get("path") == str(worktree_path):
            branch = wt.get("branch", "")
            if branch.startswith("refs/heads/"):
                branch = branch[len("refs/heads/") :]
            break

    if branch is None:
        # Check if the directory exists but isn't a worktree
        if worktree_path.exists():
            print(f"Error: '{name}' exists at {worktree_path} but is not a registered worktree.")
        else:
            print(f"Error: No worktree found with name '{name}'.")
            print("Use --list to see active worktrees.")
        sys.exit(1)

    print(f"Worktree: {worktree_path}")
    print(f"Branch:   {branch}")

    # Check for merged PR
    merged = False
    try:
        pr_result = run(
            ["gh", "pr", "list", "--head", branch, "--state", "merged", "--json", "number", "--limit", "1"],
            check=False,
        )
        if pr_result.returncode == 0:
            prs = json.loads(pr_result.stdout)
            if prs:
                merged = True
                print(f"PR:       #{prs[0]['number']} (merged)")
    except Exception:
        pass

    if not merged and not force:
        print()
        print("Warning: No merged PR found for this branch.")
        print("Use --force to remove anyway, or merge the PR first.")
        sys.exit(1)

    # Safety confirmation
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
        # Try with --force if there are untracked files
        print("  Retrying with --force...")
        run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=PROJECT_ROOT,
            check=False,
        )

    # Delete local branch
    print("Deleting local branch...")
    run(
        ["git", "branch", "-d" if merged else "-D", branch],
        cwd=PROJECT_ROOT,
        check=False,
    )

    # Delete remote branch
    print("Deleting remote branch...")
    run(
        ["git", "push", "origin", "--delete", branch],
        cwd=PROJECT_ROOT,
        check=False,
    )

    print(f"\nCleaned up worktree '{name}'.")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Create and manage git worktrees from GitHub issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s 42                    Create worktree from issue #42
  %(prog)s 42 --type=fix         Override branch type to 'fix'
  %(prog)s --list                List active worktrees
  %(prog)s --cleanup my-feature  Remove worktree 'my-feature'
""",
    )

    parser.add_argument(
        "issue",
        nargs="?",
        type=int,
        help="GitHub issue number to create worktree from",
    )
    parser.add_argument(
        "--type",
        dest="branch_type",
        choices=BRANCH_TYPES,
        help="Override auto-detected branch type",
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
        help="Force cleanup even if PR is not merged",
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
    elif args.issue:
        create_worktree(args.issue, branch_type=args.branch_type)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
