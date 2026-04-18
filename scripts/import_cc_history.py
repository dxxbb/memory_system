#!/usr/bin/env python3
"""
import_cc_history.py - import Claude Code session transcripts into the vault.

Scans ~/.claude/projects/<slug>/*.jsonl (top-level only, skipping subagent
transcripts in subdirs) and renders each session as a single markdown file
under <vault>/assist/memory collection/history/<YYYY-MM-DD>/cc-<slug>-<short-uuid>.md.

Only user and assistant events are rendered. tool_use / tool_result blocks are
compressed to one-line summaries. thinking blocks are skipped.

Sessions with fewer than 2 user messages are skipped. Existing output files
are left untouched (idempotent), unless --force is given.

Usage:
    python3 import_cc_history.py
    python3 import_cc_history.py --dry-run
    python3 import_cc_history.py --vault ~/dxy_OS --source ~/.claude/projects
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

CONV_DIR = "assist/memory collection/history"
MAX_RESULT_CHARS = 200


def vault_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("PERSONAL_OS_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "dxy_OS").resolve()


def iso_date(ts: str) -> str:
    return ts[:10] if ts else "unknown"


def slug_from_dir(name: str) -> str:
    return name.lstrip("-")


def summarize_tool_use(block: dict) -> str:
    name = block.get("name", "?")
    inp = block.get("input", {}) or {}
    if isinstance(inp, dict):
        for k in ("command", "file_path", "pattern", "query", "description"):
            if k in inp:
                v = str(inp[k]).replace("\n", " ")
                if len(v) > MAX_RESULT_CHARS:
                    v = v[:MAX_RESULT_CHARS] + "…"
                return f"[tool_use: {name} — {k}={v}]"
    return f"[tool_use: {name}]"


def summarize_tool_result(block: dict) -> str:
    content = block.get("content", "")
    is_err = block.get("is_error")
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        content = "\n".join(parts)
    content = str(content).replace("\n", " ")
    if len(content) > MAX_RESULT_CHARS:
        content = content[:MAX_RESULT_CHARS] + "…"
    tag = "tool_result:err" if is_err else "tool_result"
    return f"[{tag}: {content}]"


def render_content(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    out = []
    for b in content:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            out.append(b.get("text", "").strip())
        elif t == "tool_use":
            out.append(summarize_tool_use(b))
        elif t == "tool_result":
            out.append(summarize_tool_result(b))
        # thinking: skip
    return "\n\n".join(x for x in out if x)


def parse_session(path: Path) -> dict:
    users = []
    entries = []
    first_ts = None
    last_ts = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = e.get("type")
        if t not in ("user", "assistant"):
            continue
        msg = e.get("message") or {}
        role = msg.get("role") or t
        content = render_content(msg.get("content"))
        if not content:
            continue
        ts = e.get("timestamp", "")
        first_ts = first_ts or ts
        last_ts = ts or last_ts
        if role == "user":
            users.append(content)
        entries.append((role, ts, content))
    return {
        "entries": entries,
        "user_count": len(users),
        "first_ts": first_ts or "",
        "last_ts": last_ts or "",
    }


def render_markdown(session: dict, meta: dict) -> str:
    fm_lines = [
        "---",
        "kind: source",
        "source: claude-code",
        f"session_id: {meta['session_id']}",
        f"project: {meta['project']}",
        f"started_at: {session['first_ts']}",
        f"ended_at: {session['last_ts']}",
        f"imported_from: {meta['imported_from']}",
        "---",
        "",
        f"# Claude Code session {meta['short_id']}",
        "",
    ]
    body = []
    for role, ts, content in session["entries"]:
        header = f"## {role.capitalize()}"
        if ts:
            header += f" · {ts}"
        body.append(header)
        body.append("")
        body.append(content)
        body.append("")
    return "\n".join(fm_lines) + "\n".join(body) + "\n"


def safe_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", s)


def import_one(jsonl: Path, project_dir: str, vault: Path, force: bool, dry: bool) -> str:
    session_id = jsonl.stem
    session = parse_session(jsonl)
    if session["user_count"] < 2:
        return f"skip (thin: {session['user_count']} user msgs)"
    date = iso_date(session["first_ts"])
    slug = slug_from_dir(project_dir)
    short_id = session_id.split("-")[0]
    out_dir = vault / CONV_DIR / date
    fn = safe_filename(f"cc-{slug}-{short_id}.md")
    out_path = out_dir / fn
    if out_path.exists() and not force:
        return f"skip (exists: {out_path.relative_to(vault)})"
    meta = {
        "session_id": session_id,
        "short_id": short_id,
        "project": slug,
        "imported_from": str(jsonl),
    }
    md = render_markdown(session, meta)
    if dry:
        return f"would write {out_path.relative_to(vault)} ({len(session['entries'])} entries)"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return f"wrote {out_path.relative_to(vault)} ({len(session['entries'])} entries)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", help="vault root (default: $PERSONAL_OS_VAULT or ~/dxy_OS)")
    ap.add_argument("--source", help="claude projects dir (default: ~/.claude/projects)")
    ap.add_argument("--project", help="only import this project dir (basename)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite existing output")
    args = ap.parse_args()

    vault = vault_root(args.vault)
    if not vault.is_dir():
        sys.stderr.write(f"vault not found: {vault}\n")
        return 2

    source = Path(args.source).expanduser().resolve() if args.source else (Path.home() / ".claude" / "projects").resolve()
    if not source.is_dir():
        sys.stderr.write(f"source not found: {source}\n")
        return 2

    project_dirs = sorted(p for p in source.iterdir() if p.is_dir())
    if args.project:
        project_dirs = [p for p in project_dirs if p.name == args.project]
        if not project_dirs:
            sys.stderr.write(f"project not found: {args.project}\n")
            return 1

    total = 0
    for pdir in project_dirs:
        jsonls = sorted(pdir.glob("*.jsonl"))
        if not jsonls:
            continue
        print(f"[{pdir.name}] {len(jsonls)} sessions")
        for j in jsonls:
            try:
                status = import_one(j, pdir.name, vault, args.force, args.dry_run)
            except Exception as e:
                status = f"ERROR: {e}"
            print(f"  {j.name}: {status}")
            total += 1
    print(f"processed {total} sessions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
