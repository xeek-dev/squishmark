#!/usr/bin/env python3
"""Update GitHub issue metadata (type, labels, milestone).

Usage:
    github-issue-updater.py <issue> --type task|bug|feature
    github-issue-updater.py <issue> --add-label "engine,themes"
    github-issue-updater.py <issue> --milestone "SquishMark 1.0"
    github-issue-updater.py <issue> --type task --add-label engine --milestone "SquishMark 1.0"
"""

from __future__ import annotations

import argparse
import subprocess
import sys

ISSUE_TYPE_IDS = {
    "task": "IT_kwDOBA-w0M4Aw6D3",
    "bug": "IT_kwDOBA-w0M4Aw6D4",
    "feature": "IT_kwDOBA-w0M4Aw6D7",
}


def run(
    cmd: list[str],
    *,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and return the result."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


def verify_issue(issue: int) -> None:
    """Verify that the issue exists, exit on failure."""
    try:
        run(["gh", "issue", "view", str(issue), "--json", "number"])
    except subprocess.CalledProcessError:
        print(f"Error: Issue #{issue} not found or not accessible.")
        sys.exit(1)


def set_issue_type(issue: int, type_name: str) -> None:
    """Set the issue type via GraphQL mutation."""
    type_id = ISSUE_TYPE_IDS[type_name]

    # Get the issue node ID
    result = run(["gh", "issue", "view", str(issue), "--json", "id", "--jq", ".id"])
    issue_id = result.stdout.strip()

    query = f"""
    mutation {{
      updateIssue(input: {{
        id: "{issue_id}",
        issueTypeId: "{type_id}"
      }}) {{
        issue {{ id }}
      }}
    }}
    """
    try:
        run(["gh", "api", "graphql", "-f", f"query={query}"])
        print(f"  Type: set to '{type_name}'")
    except subprocess.CalledProcessError as e:
        print(f"  Error setting type: {e.stderr if e.stderr else 'GraphQL mutation failed'}")
        raise


def update_labels(issue: int, labels: str) -> None:
    """Add labels to an issue."""
    try:
        run(["gh", "issue", "edit", str(issue), "--add-label", labels])
        print(f"  Labels: added '{labels}'")
    except subprocess.CalledProcessError as e:
        print(f"  Error adding labels: {e.stderr if e.stderr else 'command failed'}")
        raise


def set_milestone(issue: int, milestone: str) -> None:
    """Set the milestone on an issue."""
    try:
        run(["gh", "issue", "edit", str(issue), "--milestone", milestone])
        print(f"  Milestone: set to '{milestone}'")
    except subprocess.CalledProcessError as e:
        print(f"  Error setting milestone: {e.stderr if e.stderr else 'command failed'}")
        raise


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Update GitHub issue metadata (type, labels, milestone).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s 42 --type task
  %(prog)s 42 --add-label "engine,themes"
  %(prog)s 42 --milestone "SquishMark 1.0"
  %(prog)s 42 --type task --add-label engine --milestone "SquishMark 1.0"
""",
    )

    parser.add_argument("issue", type=int, help="GitHub issue number")
    parser.add_argument(
        "--type",
        choices=ISSUE_TYPE_IDS.keys(),
        help="Set the issue type",
    )
    parser.add_argument(
        "--add-label",
        metavar="LABELS",
        help="Comma-separated labels to add",
    )
    parser.add_argument(
        "--milestone",
        metavar="NAME",
        help="Milestone to assign",
    )

    return parser


def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not any([args.type, args.add_label, args.milestone]):
        parser.error("at least one of --type, --add-label, or --milestone is required")

    verify_issue(args.issue)
    print(f"Updating issue #{args.issue}:")

    failed = False

    if args.type:
        try:
            set_issue_type(args.issue, args.type)
        except subprocess.CalledProcessError:
            failed = True

    if args.add_label:
        try:
            update_labels(args.issue, args.add_label)
        except subprocess.CalledProcessError:
            failed = True

    if args.milestone:
        try:
            set_milestone(args.issue, args.milestone)
        except subprocess.CalledProcessError:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
