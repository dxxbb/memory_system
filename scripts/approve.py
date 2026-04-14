#!/usr/bin/env python3
"""
approve.py - approve a PR branch and squash-merge it into main.

Under the current model, the agent has already performed the full downstream
rebuild inside the pr/* branch (see system/operating-rule/*-rebuild.md). This
script does NOT run rebuild. It only:

  1. assert main is clean
  2. assert the pr branch exists and diverges from main
  3. read the original PR commit message (first commit on the branch)
  4. squash-merge into main with an Approved-by: trailer
  5. delete the branch
  6. append a line to system/change-log/<YYYY-MM>.md
  7. mark the corresponding inbox TODO as done (if present)

Usage:
    python3 approve.py pr/0001-add-assumption-check
    python3 approve.py pr/0001-add-assumption-check --dry-run
    python3 approve.py pr/0001-add-assumption-check --vault /path/to/vault

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
    sys.stderr.write("approve.py needs PyYAML: pip install pyyaml\n")
    sys.exit(1)

CHANGE_LOG_DIR = "system/change-log"
INBOX_DIR = "system/monitor-inbox"
PR_ID_RE = re.compile(r"^pr/(\d+)(?:-.*)?$")


def vault_root() -> Path:
    env = os.environ.get("PERSONAL_OS_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "dxy_OS").resolve()


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}):\n{result.stderr}"
        )
    return result.stdout


def default_branch(root: Path) -> str:
    for name in ("master", "main"):
        try:
            git(root, "rev-parse", "--verify", f"refs/heads/{name}")
            return name
        except RuntimeError:
            continue
    raise RuntimeError("no master or main branch found in vault")


def parse_pr_id(branch: str) -> str:
    m = PR_ID_RE.match(branch)
    if not m:
        raise ValueError(
            f"branch name must match 'pr/<id>[-<desc>]', got: {branch}"
        )
    return m.group(1)


def assert_clean_base(root: Path, base: str) -> None:
    head = git(root, "symbolic-ref", "--short", "HEAD").strip()
    if head != base:
        raise RuntimeError(f"not on {base} (current: {head}). checkout {base} first.")
    dirty = git(root, "status", "--porcelain").strip()
    if dirty:
        raise RuntimeError(f"{base} has uncommitted changes:\n{dirty}")


def assert_branch_exists(root: Path, branch: str) -> None:
    out = git(root, "branch", "--list", branch).strip()
    if not out:
        raise RuntimeError(f"branch not found: {branch}")


def assert_branch_ahead(root: Path, branch: str, base: str) -> None:
    commits = git(root, "rev-list", f"{base}..{branch}").strip()
    if not commits:
        raise RuntimeError(f"branch {branch} has no commits ahead of {base}")


def first_pr_commit_message(root: Path, branch: str, base: str) -> tuple[str, str]:
    """Return (title, body) of the first PR commit (oldest on the branch).

    Filters out later commits like 'Review comments round N' and agent response
    commits, keeping the original proposal message as the canonical one.
    """
    out = git(
        root,
        "rev-list",
        "--reverse",
        f"{base}..{branch}",
    ).strip()
    shas = [s for s in out.splitlines() if s]
    if not shas:
        raise RuntimeError(f"no commits on {branch} ahead of main")
    msg = git(root, "log", "-1", "--format=%B", shas[0]).strip()
    parts = msg.split("\n\n", 1)
    title = parts[0].strip()
    body = parts[1].strip() if len(parts) > 1 else ""
    return title, body


def squash_merge(root: Path, branch: str) -> None:
    git(root, "merge", "--squash", branch)


def commit_squash(root: Path, title: str, body: str, pr_id: str, branch: str) -> str:
    trailer = f"Approved-by: approve.py pr/{pr_id}"
    if body:
        msg = f"{title}\n\n{body}\n\n{trailer}\n"
    else:
        msg = f"{title}\n\n{trailer}\n"
    result = subprocess.run(
        ["git", "-C", str(root), "commit", "-F", "-"],
        input=msg,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"commit failed:\n{result.stderr}")
    sha = git(root, "rev-parse", "HEAD").strip()
    return sha


def delete_branch(root: Path, branch: str) -> None:
    git(root, "branch", "-D", branch)


def append_change_log(root: Path, pr_id: str, title: str, merged_sha: str) -> None:
    log_dir = root / CHANGE_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().replace(microsecond=0)
    month = now.strftime("%Y-%m")
    log_file = log_dir / f"{month}.md"
    header = ""
    if not log_file.exists():
        header = f"---\nkind: derived\n---\n\n# Change Log · {month}\n\n"
    line = f"- {now.isoformat()} approved pr/{pr_id} {merged_sha[:7]} — {title}\n"
    with log_file.open("a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(line)


def update_inbox(root: Path, pr_id: str, branch: str) -> Path | None:
    inbox = root / INBOX_DIR
    if not inbox.is_dir():
        return None
    pattern = f"{pr_id}-*.md"
    matches = sorted(inbox.glob(pattern))
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

    fm["status"] = "done"
    fm["pr_branch"] = branch
    fm["merged_at"] = dt.datetime.now().replace(microsecond=0).isoformat()

    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    target.write_text(f"---\n{new_fm}\n---\n\n{body}", encoding="utf-8")
    return target


def commit_system_files(root: Path, pr_id: str) -> None:
    """Commit change-log + inbox updates with a System-owned-by trailer."""
    dirty = git(root, "status", "--porcelain").strip()
    if not dirty:
        return
    git(root, "add", CHANGE_LOG_DIR, INBOX_DIR)
    still_dirty = git(root, "diff", "--cached", "--name-only").strip()
    if not still_dirty:
        return
    msg = (
        f"Record approval of pr/{pr_id}\n\n"
        f"System-owned-by: approve.py pr/{pr_id}\n"
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
    ap.add_argument("--vault", help="vault root (default: $PERSONAL_OS_VAULT or ~/dxy_OS)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    branch = args.branch
    try:
        pr_id = parse_pr_id(branch)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        return 2

    root = Path(args.vault).expanduser().resolve() if args.vault else vault_root()
    if not (root / ".git").is_dir():
        sys.stderr.write(f"not a git repo: {root}\n")
        return 2

    try:
        base = default_branch(root)
        assert_clean_base(root, base)
        assert_branch_exists(root, branch)
        assert_branch_ahead(root, branch, base)
        title, body = first_pr_commit_message(root, branch, base)
    except (RuntimeError, ValueError) as e:
        sys.stderr.write(f"pre-check failed: {e}\n")
        return 1

    print(f"approving {branch}")
    print(f"  title: {title}")
    print(f"  pr_id: {pr_id}")

    if args.dry_run:
        print("[dry-run] would squash merge, commit, delete branch, update log/inbox")
        return 0

    try:
        squash_merge(root, branch)
        merged_sha = commit_squash(root, title, body, pr_id, branch)
        print(f"  merged as {merged_sha[:7]}")
        delete_branch(root, branch)
        print(f"  deleted branch {branch}")
        append_change_log(root, pr_id, title, merged_sha)
        inbox_file = update_inbox(root, pr_id, branch)
        if inbox_file:
            print(f"  marked inbox {inbox_file.name} done")
        commit_system_files(root, pr_id)
    except RuntimeError as e:
        sys.stderr.write(f"\nFAILED: {e}\n")
        sys.stderr.write(
            "NOTE: no automatic rollback. check `git status` and `git log -3` "
            "and resolve manually.\n"
        )
        return 1

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
