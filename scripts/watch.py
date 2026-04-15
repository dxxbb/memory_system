#!/usr/bin/env python3
"""
watch.py - scan new commits on main and produce inbox TODOs.

For every new commit since .watcher-state.last_seen_commit:
  - skip commits whose message contains Approved-by / Rebuilt-by / System-owned-by trailer
  - for each file in the diff:
      - skip paths under system/**
      - read the file's frontmatter on HEAD
      - skip kind: derived or kind: system
      - kind: source (or no frontmatter) -> classify by path prefix -> write a TODO

Vault path defaults to $PERSONAL_OS_VAULT or ~/dxy_OS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("watch.py needs PyYAML: pip install pyyaml\n")
    sys.exit(1)

SKIP_TRAILERS = ("Approved-by:", "Rebuilt-by:", "System-owned-by:")
STATE_FILE = "system/.watcher-state.json"
INBOX_DIR = "system/monitor-inbox"
FALLBACK_WINDOW = 50  # commits to look back when state is missing


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
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr
        )
    return result.stdout


def classify(path: str) -> str:
    if path.startswith("conversation memory/claude code memory/"):
        return "cc_memory"
    if path.startswith("conversation memory/"):
        return "conversation"
    if path.startswith("user/daily memo/"):
        return "daily_memo"
    if path.startswith("user/"):
        return "identity_change"
    if path.startswith("workspace/project/"):
        return "project_update"
    if path.startswith("workspace/topic/"):
        return "topic_update"
    if path.startswith("workspace/reading/"):
        return "reading_update"
    if path.startswith("workspace/writing/"):
        return "writing_update"
    if path.startswith("ingest src/"):
        return "ingest"
    return "unclassified"


def read_frontmatter_at(root: Path, rev: str, path: str) -> dict | None:
    try:
        blob = git(root, "show", f"{rev}:{path}")
    except subprocess.CalledProcessError:
        return None
    if not blob.startswith("---"):
        return None
    end = blob.find("\n---", 3)
    if end == -1:
        return None
    try:
        data = yaml.safe_load(blob[3:end].strip()) or {}
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def load_state(root: Path) -> dict:
    p = root / STATE_FILE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(root: Path, state: dict) -> None:
    p = root / STATE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def next_todo_id(root: Path) -> int:
    inbox = root / INBOX_DIR
    inbox.mkdir(parents=True, exist_ok=True)
    max_id = 0
    for p in inbox.glob("*.md"):
        name = p.stem
        prefix = name.split("-", 1)[0]
        if prefix.isdigit():
            max_id = max(max_id, int(prefix))
    return max_id + 1


def commit_has_skip_trailer(msg: str) -> bool:
    for line in msg.splitlines():
        for t in SKIP_TRAILERS:
            if line.startswith(t):
                return True
    return False


def commits_between(root: Path, since: str | None) -> list[str]:
    if since:
        try:
            out = git(root, "rev-list", "--reverse", f"{since}..HEAD")
        except subprocess.CalledProcessError:
            return []
    else:
        out = git(
            root, "rev-list", "--reverse", f"--max-count={FALLBACK_WINDOW}", "HEAD"
        )
    return [c for c in out.strip().splitlines() if c]


def files_in_commit(root: Path, rev: str) -> list[str]:
    # Use name-status with rename detection so pure renames (R100) can be
    # skipped. A rename with unchanged content should not fire a new TODO
    # because the previous path already triggered one.
    out = git(root, "show", "--pretty=", "--name-status", "-M", rev)
    paths = []
    for line in out.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R"):
            # R100 = rename with identical content; skip. R0xx = content
            # changed during the rename; report the new path.
            if status == "R100":
                continue
            paths.append(parts[2])
        elif status.startswith("D"):
            # deletions can't be classified by frontmatter anyway
            continue
        else:
            paths.append(parts[1] if len(parts) > 1 else parts[0])
    return paths


def commit_message(root: Path, rev: str) -> str:
    return git(root, "log", "-1", "--format=%B", rev)


def write_todo(
    root: Path,
    todo_id: int,
    event_type: str,
    source_path: str,
    source_commit: str,
    diff_summary: str,
) -> Path:
    inbox = root / INBOX_DIR
    inbox.mkdir(parents=True, exist_ok=True)
    fn = f"{todo_id:04d}-{event_type}.md"
    fp = inbox / fn
    now = dt.datetime.now().replace(microsecond=0).isoformat()
    fm = {
        "kind": "system",
        "id": f"{todo_id:04d}",
        "status": "todo",
        "event_type": event_type,
        "source_path": source_path,
        "source_commit": source_commit,
        "created_at": now,
    }
    body_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    body = f"---\n{body_fm}\n---\n\n{diff_summary}\n"
    fp.write_text(body, encoding="utf-8")
    return fp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", help="vault root (default: $PERSONAL_OS_VAULT or ~/dxy_OS)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--init",
        action="store_true",
        help="set last_seen_commit=HEAD without producing TODOs (bootstrap)",
    )
    args = ap.parse_args()

    root = Path(args.vault).expanduser().resolve() if args.vault else vault_root()
    if not (root / ".git").is_dir():
        sys.stderr.write(f"not a git repo: {root}\n")
        return 2

    head = git(root, "rev-parse", "HEAD").strip()
    state = load_state(root)

    if args.init:
        state["last_seen_commit"] = head
        save_state(root, state)
        print(f"initialized last_seen_commit = {head}")
        return 0

    since = state.get("last_seen_commit")

    if since == head:
        print("up to date")
        return 0

    commits = commits_between(root, since)
    if not commits:
        print("no new commits")
        if not args.dry_run:
            state["last_seen_commit"] = head
            save_state(root, state)
        return 0

    todo_id = next_todo_id(root)
    wrote = 0
    skipped_commits = 0
    skipped_files = 0

    for rev in commits:
        msg = commit_message(root, rev)
        if commit_has_skip_trailer(msg):
            skipped_commits += 1
            continue
        for f in files_in_commit(root, rev):
            if f.startswith("system/") or f.startswith("."):
                skipped_files += 1
                continue
            if "/." in f:
                skipped_files += 1
                continue
            if not f.endswith(".md"):
                skipped_files += 1
                continue
            fm = read_frontmatter_at(root, rev, f)
            kind = (fm or {}).get("kind")
            if kind in ("derived", "system"):
                skipped_files += 1
                continue
            if fm is None:
                print(f"defaulted to source: {f}")
            event_type = classify(f)
            summary = msg.splitlines()[0] if msg else ""
            if args.dry_run:
                print(f"[dry-run] would write todo {todo_id:04d} {event_type} {f}@{rev[:7]}")
            else:
                write_todo(root, todo_id, event_type, f, rev, summary)
                print(f"wrote {INBOX_DIR}/{todo_id:04d}-{event_type}.md  ({f})")
            todo_id += 1
            wrote += 1

    if not args.dry_run:
        state["last_seen_commit"] = head
        save_state(root, state)

    print(
        f"done: wrote={wrote} skipped_commits={skipped_commits} "
        f"skipped_files={skipped_files}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
