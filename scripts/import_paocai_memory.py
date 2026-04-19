#!/usr/bin/env python3
"""
import_paocai_memory.py - mirror the paocai_memory git repo into the vault.

Pulls https://github.com/dxxbb/paocai_memory and copies a curated subset
into <vault>/01 assist/memory collection/agents memory/paocai/.

paocai (泡菜) is a separate personal AI persona built on the openclaw
framework. Its memory backup repo holds the persona's identity files,
running MEMORY.md, themes/people/daily logs, etc. We mirror the
*content-bearing* parts so forge's triage flow can compare against
SP/section just like it does for CC memory.

What's included:
  - Top-level identity/profile: IDENTITY.md, SOUL.md, USER.md, MEMORY.md
  - memory/** (themes/, daily/, people/, books/, README.md, individual day files)

What's excluded:
  - paocai's own agent system docs (AGENTS.md, BOOTSTRAP.md, HEARTBEAT.md,
    PERMISSIONS.md, TOOLS.md) — these are paocai's runtime rules, not signals
  - skills/, runtime/, backups/, .openclaw/, .learnings/, .disabled-skills/
  - non-markdown files (*.json state, etc.)

Idempotent: file-content compare; only writes changed files.

Does NOT auto-commit. Prints the recommended commit (with
System-owned-by trailer) for the initial bulk import so that watch.py
skips the flood of cc_memory inbox events. For incremental updates,
commit normally to let the agent triage diffs.

Usage:
    python3 import_paocai_memory.py
    python3 import_paocai_memory.py --dry-run
    python3 import_paocai_memory.py --source-repo /path/to/local/clone  # skip fetch
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO = "https://github.com/dxxbb/paocai_memory.git"
DEFAULT_CACHE = Path.home() / ".cache" / "forge" / "paocai_memory"
TARGET_SUBDIR = "01 assist/memory collection/agents memory/paocai"

INCLUDE_TOP_LEVEL = ["IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"]
INCLUDE_SUBTREES = ["memory"]


def vault_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("PERSONAL_OS_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "dxy_OS").resolve()


def fetch(repo_url: str, cache: Path) -> Path:
    cache.parent.mkdir(parents=True, exist_ok=True)
    if (cache / ".git").is_dir():
        print(f"updating {cache}")
        subprocess.run(["git", "-C", str(cache), "fetch", "--quiet", "origin"], check=True)
        subprocess.run(["git", "-C", str(cache), "reset", "--hard", "--quiet", "origin/HEAD"], check=True)
    else:
        if cache.exists():
            sys.stderr.write(f"cache path exists but is not a git repo: {cache}\n")
            sys.exit(2)
        print(f"cloning {repo_url} -> {cache}")
        subprocess.run(["git", "clone", "--quiet", repo_url, str(cache)], check=True)
    return cache


def discover_files(repo_root: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for name in INCLUDE_TOP_LEVEL:
        p = repo_root / name
        if p.is_file():
            files.append((p, name))
    for sub in INCLUDE_SUBTREES:
        sub_root = repo_root / sub
        if not sub_root.is_dir():
            continue
        for p in sorted(sub_root.rglob("*.md")):
            rel = p.relative_to(repo_root)
            files.append((p, str(rel)))
    return files


def import_one(src: Path, dst: Path, dry: bool) -> str:
    new = src.read_bytes()
    if dst.exists():
        if dst.read_bytes() == new:
            return "unchanged"
        verb = "would update" if dry else "updated"
    else:
        verb = "would write" if dry else "wrote"
    if not dry:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(new)
    return verb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", help="vault root (default: $PERSONAL_OS_VAULT or ~/dxy_OS)")
    ap.add_argument("--source-repo", help="local path to paocai_memory clone (skips fetch)")
    ap.add_argument("--repo-url", default=DEFAULT_REPO, help=f"repo url (default: {DEFAULT_REPO})")
    ap.add_argument("--cache-dir", help=f"cache dir for clone (default: {DEFAULT_CACHE})")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vault = vault_root(args.vault)
    if not vault.is_dir():
        sys.stderr.write(f"vault not found: {vault}\n")
        return 2

    if args.source_repo:
        repo_root = Path(args.source_repo).expanduser().resolve()
        if not repo_root.is_dir():
            sys.stderr.write(f"source-repo not found: {repo_root}\n")
            return 2
    else:
        cache = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else DEFAULT_CACHE
        repo_root = fetch(args.repo_url, cache)

    files = discover_files(repo_root)
    if not files:
        sys.stderr.write(f"no files found in {repo_root}\n")
        return 1

    target_root = vault / TARGET_SUBDIR
    total = 0
    touched = 0
    for src, rel in files:
        dst = target_root / rel
        status = import_one(src, dst, args.dry_run)
        print(f"  {rel}: {status}")
        total += 1
        if status != "unchanged":
            touched += 1

    print()
    print(f"processed {total} files ({touched} new/changed)")

    if touched > 0 and not args.dry_run:
        print()
        print("To suppress watch.py inbox flood, commit the bulk import with the")
        print("System-owned-by trailer (recognized by watch.py SKIP_TRAILERS):")
        print()
        print(f'  cd "{vault}"')
        print(f'  git add "{TARGET_SUBDIR}"')
        print('  git commit -m "Import paocai_memory snapshot" \\')
        print('             -m "System-owned-by: import_paocai_memory.py"')
        print()
        print("For incremental imports later, commit without the trailer to let")
        print("the agent triage diffs as cc_memory events.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
