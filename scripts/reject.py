#!/usr/bin/env python3
"""
reject.py - reject a PR branch.

Deletes the pr/* branch, prepends a rejection line to the change log, and marks
the corresponding inbox TODO as rejected.

Usage:
    python3 reject.py pr/0001-add-assumption-check --reason "too aggressive"

Vault path defaults to $PERSONAL_OS_VAULT or ~/dxy_OS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("reject.py needs PyYAML: pip install pyyaml\n")
    sys.exit(1)

CHANGE_LOG_DIR = "system/change-log"
INBOX_DIR = "system/monitor-inbox"
PR_ID_RE = re.compile(r"^pr/(\d+)(?:-.*)?$")


def vault_root() -> Path:
    env = os.environ.get("PERSONAL_OS_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "dxy_OS").resolve()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], text=True, capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def default_branch(root: Path) -> str:
    for name in ("master", "main"):
        try:
            git(root, "rev-parse", "--verify", f"refs/heads/{name}")
            return name
        except RuntimeError:
            continue
    raise RuntimeError("no master or main branch found in vault")


def branch_title(root: Path, branch: str, base: str) -> str:
    """Try to get the PR branch title for the log entry."""
    try:
        out = git(root, "rev-list", "--reverse", f"{base}..{branch}").strip()
        shas = [s for s in out.splitlines() if s]
        if shas:
            msg = git(root, "log", "-1", "--format=%s", shas[0]).strip()
            return msg
    except RuntimeError:
        pass
    return branch


def prepend_change_log(root: Path, pr_id: str, branch: str, base: str, reason: str) -> None:
    """Write a concise rejection entry at the TOP of the monthly log."""
    log_dir = root / CHANGE_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().replace(microsecond=0)
    month = now.strftime("%Y-%m")
    log_file = log_dir / f"{month}.md"
    file_header = f"---\nkind: derived\n---\n\n# Change Log · {month}\n\n"

    title = branch_title(root, branch, base)
    line = f"- {now.strftime('%m-%d %H:%M')} rejected pr/{pr_id} — {title}，原因: {reason}"

    existing_entries = ""
    if log_file.exists():
        text = log_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, l in enumerate(lines):
            if l.startswith("- "):
                existing_entries = "\n".join(lines[i:])
                break

    parts = [file_header.rstrip(), line]
    if existing_entries:
        parts.append(existing_entries)
    log_file.write_text("\n".join(parts) + "\n", encoding="utf-8")


def update_inbox(root: Path, pr_id: str, branch: str, reason: str) -> Path | None:
    inbox = root / INBOX_DIR
    if not inbox.is_dir():
        return None
    matches = sorted(inbox.glob(f"{pr_id}-*.md"))
    if not matches:
        return None
    target = matches[0]
    target.unlink()
    return target


def commit_system_files(root: Path, pr_id: str) -> None:
    dirty = git(root, "status", "--porcelain").strip()
    if not dirty:
        return
    git(root, "add", CHANGE_LOG_DIR, INBOX_DIR)
    staged = git(root, "diff", "--cached", "--name-only").strip()
    if not staged:
        return
    msg = (
        f"Record rejection of pr/{pr_id}\n\n"
        f"System-owned-by: reject.py pr/{pr_id}\n"
    )
    result = subprocess.run(
        ["git", "-C", str(root), "commit", "-F", "-"],
        input=msg,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"system commit failed:\n{result.stderr}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("branch", help="PR branch, e.g. pr/0001-add-assumption-check")
    ap.add_argument("--reason", required=True, help="why this PR is rejected")
    ap.add_argument("--vault", help="vault root (default: $PERSONAL_OS_VAULT or ~/dxy_OS)")
    args = ap.parse_args()

    branch = args.branch
    m = PR_ID_RE.match(branch)
    if not m:
        sys.stderr.write(f"bad branch name: {branch}\n")
        return 2
    pr_id = m.group(1)

    root = Path(args.vault).expanduser().resolve() if args.vault else vault_root()
    if not (root / ".git").is_dir():
        sys.stderr.write(f"not a git repo: {root}\n")
        return 2

    try:
        base = default_branch(root)
        head = git(root, "symbolic-ref", "--short", "HEAD").strip()
        if head != base:
            sys.stderr.write(f"not on {base} (current: {head})\n")
            return 1
        if not git(root, "branch", "--list", branch).strip():
            sys.stderr.write(f"branch not found: {branch}\n")
            return 1
    except RuntimeError as e:
        sys.stderr.write(f"{e}\n")
        return 1

    print(f"rejecting {branch}")
    print(f"  reason: {args.reason}")

    try:
        prepend_change_log(root, pr_id, branch, base, args.reason)
        git(root, "branch", "-D", branch)
        print(f"  deleted branch")
        inbox_file = update_inbox(root, pr_id, branch, args.reason)
        if inbox_file:
            print(f"  marked inbox {inbox_file.name} rejected")
        commit_system_files(root, pr_id)
    except RuntimeError as e:
        sys.stderr.write(f"\nFAILED: {e}\n")
        return 1

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
