#!/usr/bin/env python3
"""
request-changes.py - request changes on a PR branch.

Opens $EDITOR for the reviewer to write a comment, saves it as
system/pr-review/pr-<id>-comments-round<N>.md, commits it to the PR branch,
returns to main, and enqueues a pr_revision inbox TODO so the agent will pick
it up on the next monitor.

Usage:
    python3 request-changes.py pr/0001-add-assumption-check

Vault path defaults to $PERSONAL_OS_VAULT or ~/dxy_OS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("request-changes.py needs PyYAML: pip install pyyaml\n")
    sys.exit(1)

PR_REVIEW_DIR = "system/pr-review"
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


def next_round(root: Path, pr_id: str) -> int:
    d = root / PR_REVIEW_DIR
    if not d.is_dir():
        return 1
    pattern = re.compile(rf"^pr-{pr_id}-comments-round(\d+)\.md$")
    max_round = 0
    for p in d.glob(f"pr-{pr_id}-comments-round*.md"):
        m = pattern.match(p.name)
        if m:
            max_round = max(max_round, int(m.group(1)))
    return max_round + 1


def open_editor(initial: str) -> str:
    editor = os.environ.get("EDITOR", "vim")
    with tempfile.NamedTemporaryFile(
        "w+", suffix=".md", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(initial)
        path = tf.name
    try:
        result = subprocess.run([editor, path])
        if result.returncode != 0:
            raise RuntimeError(f"editor exited with code {result.returncode}")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    finally:
        os.unlink(path)
    return text


def strip_placeholder(text: str) -> str:
    """Remove comment lines starting with '#' that look like editor hints."""
    lines = []
    for line in text.splitlines():
        if line.startswith("# <!--") or line.strip() == "# <!-- REMOVE ABOVE -->":
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def write_inbox_todo(
    root: Path, pr_id: str, branch: str, comment_path: str, round_n: int
) -> Path:
    inbox = root / INBOX_DIR
    inbox.mkdir(parents=True, exist_ok=True)
    max_id = 0
    for p in inbox.glob("*.md"):
        prefix = p.stem.split("-", 1)[0]
        if prefix.isdigit():
            max_id = max(max_id, int(prefix))
    new_id = max_id + 1
    fn = f"{new_id:04d}-pr_revision.md"
    fp = inbox / fn
    now = dt.datetime.now().replace(microsecond=0).isoformat()
    fm = {
        "kind": "system",
        "id": f"{new_id:04d}",
        "status": "todo",
        "event_type": "pr_revision",
        "pr_branch": branch,
        "pr_id": pr_id,
        "comment_file": comment_path,
        "round": round_n,
        "created_at": now,
    }
    body_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    fp.write_text(
        f"---\n{body_fm}\n---\n\nReviewer left round {round_n} comments on pr/{pr_id}.\n",
        encoding="utf-8",
    )
    return fp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("branch", help="PR branch, e.g. pr/0001-add-assumption-check")
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
        if git(root, "status", "--porcelain").strip():
            sys.stderr.write(f"{base} has uncommitted changes\n")
            return 1
        if not git(root, "branch", "--list", branch).strip():
            sys.stderr.write(f"branch not found: {branch}\n")
            return 1
    except RuntimeError as e:
        sys.stderr.write(f"{e}\n")
        return 1

    round_n = next_round(root, pr_id)
    print(f"request-changes on {branch} (round {round_n})")

    placeholder = (
        f"# <!-- Review comments for pr/{pr_id} round {round_n} -->\n"
        f"# <!-- REMOVE ABOVE -->\n"
        f"\n"
        f"## What needs to change\n\n"
        f"\n"
        f"## Why\n\n"
        f"\n"
    )
    text = strip_placeholder(open_editor(placeholder))
    if not text:
        sys.stderr.write("empty comment, aborting\n")
        return 1

    comment_rel = f"{PR_REVIEW_DIR}/pr-{pr_id}-comments-round{round_n}.md"
    comment_abs = root / comment_rel
    comment_abs.parent.mkdir(parents=True, exist_ok=True)

    try:
        git(root, "checkout", branch)
        comment_abs.write_text(
            f"---\nkind: system\nround: {round_n}\n---\n\n{text}\n",
            encoding="utf-8",
        )
        git(root, "add", comment_rel)
        commit_msg = (
            f"Review comments for pr/{pr_id} (round {round_n})\n\n"
            f"System-owned-by: request-changes.py pr/{pr_id}\n"
        )
        result = subprocess.run(
            ["git", "-C", str(root), "commit", "-F", "-"],
            input=commit_msg,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"commit failed:\n{result.stderr}")
        git(root, "checkout", base)
    except RuntimeError as e:
        sys.stderr.write(f"\nFAILED while committing comment: {e}\n")
        sys.stderr.write("you may need to `git checkout main` manually.\n")
        return 1

    try:
        todo = write_inbox_todo(root, pr_id, branch, comment_rel, round_n)
        git(root, "add", INBOX_DIR)
        inbox_msg = (
            f"Enqueue pr_revision TODO for pr/{pr_id} round {round_n}\n\n"
            f"System-owned-by: request-changes.py pr/{pr_id}\n"
        )
        result = subprocess.run(
            ["git", "-C", str(root), "commit", "-F", "-"],
            input=inbox_msg,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"inbox commit failed:\n{result.stderr}")
        print(f"  committed comment to {branch}")
        print(f"  enqueued {todo.name}")
    except RuntimeError as e:
        sys.stderr.write(f"\nFAILED while enqueuing inbox: {e}\n")
        return 1

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
