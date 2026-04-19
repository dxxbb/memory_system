#!/usr/bin/env python3
"""
import_cc_memory.py - import Claude Code auto-memory files into the vault.

Scans ~/.claude/projects/<slug>/memory/*.md and copies each to
<vault>/assist/memory collection/agents memory/<slug>/<file>.md.

Note: historical per-project content has been consolidated into a single
`agents memory/memory of claude.md` (see vault commit 9468c63). New imports
continue to write per-project subdirs alongside the merged file; the script
itself does not yet consolidate. Future redesign may merge per import.

CC memory files are already-distilled user signals (preferences, project
context) written eagerly by Claude Code. This importer just copies them
verbatim; the forge triage pipeline will later compare them against
sp/section/ and decide what to sediment.

Idempotent: files with identical content are skipped; differing files are
overwritten (CC rewrites memories in place, so this mirrors that).

Usage:
    python3 import_cc_memory.py
    python3 import_cc_memory.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

CC_SUBDIR = "01 assist/memory collection/agents memory"


def vault_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("PERSONAL_OS_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "dxy_OS").resolve()


def slug_from_dir(name: str) -> str:
    return name.lstrip("-")


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
    ap.add_argument("--source", help="claude projects dir (default: ~/.claude/projects)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vault = vault_root(args.vault)
    if not vault.is_dir():
        sys.stderr.write(f"vault not found: {vault}\n")
        return 2

    source = Path(args.source).expanduser().resolve() if args.source else (Path.home() / ".claude" / "projects").resolve()
    if not source.is_dir():
        sys.stderr.write(f"source not found: {source}\n")
        return 2

    total = 0
    touched = 0
    for pdir in sorted(source.iterdir()):
        mem = pdir / "memory"
        if not mem.is_dir():
            continue
        mds = sorted(mem.glob("*.md"))
        if not mds:
            continue
        slug = slug_from_dir(pdir.name)
        out_dir = vault / CC_SUBDIR / slug
        print(f"[{slug}] {len(mds)} memory files")
        for src in mds:
            dst = out_dir / src.name
            status = import_one(src, dst, args.dry_run)
            print(f"  {src.name}: {status}")
            total += 1
            if status not in ("unchanged",):
                touched += 1
    print(f"processed {total} files ({touched} new/changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
