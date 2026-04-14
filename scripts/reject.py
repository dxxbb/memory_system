#!/usr/bin/env python3
"""
reject.py - reject a PR branch.

Deletes the pr/* branch, appends a rejection line to the change log, and marks
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


def append_change_log(root: Path, pr_id: str, reason: str) -> None:
    log_dir = root / CHANGE_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().replace(microsecond=0)
    month = now.strftime("%Y-%m")
    log_file = log_dir / f"{month}.md"
    header = ""
    if not log_file.exists():
        header = f"---\nkind: derived\n---\n\n# Change Log · {month}\n\n"
    line = f'- {now.isoformat()} rejected pr/{pr_id} — "{reason}"\n'
    with log_file.open("a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(line)


def update_inbox(root: Path, pr_id: str, branch: str, reason: str) -> Path | None:
    inbox = root / INBOX_DIR
    if not inbox.is_dir():
        return None
    matches = sorted(inbox.glob(f"{pr_id}-*.md"))
    if not matches:
        return None
    target = matches[0]
    text = target.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    try:
        fm = yaml.safe_load(text[3:end].strip()) or {}
    except yaml.YAMLError:
        return None
    body = text[end + 4 :].lstrip("\n")

    fm["status"] = "rejected"
    fm["pr_branch"] = branch
    fm["rejected_at"] = dt.datetime.now().replace(microsecond=0).isoformat()
    fm["reject_reason"] = reason

    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    target.write_text(f"---\n{new_fm}\n---\n\n{body}", encoding="utf-8")
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
        git(root, "branch", "-D", branch)
        print(f"  deleted branch")
        append_change_log(root, pr_id, args.reason)
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
