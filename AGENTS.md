# AGENTS.md

This file provides guidance to Codex when working with code in this repository.

## Project Overview

This is a **Personal OS** research and implementation project. The current architecture treats the personal OS as a **build system**: all changes are git diffs, all processing goes through PR review, all views are pre-compiled artifacts.

**Key design docs:**
- `docs/design.md` — single design document (运转机制 + MVP Week 1 落地 + Obsidian 前端)
- onepage lives in the vault at `workspace/project/forge/onepage.md` (authoritative, not in this repo)

## Current Focus

MVP Week 1: build the end-to-end pipeline from conversation → inbox → PR → approve → rebuild → new AGENTS.md view.

The vault (OS data) lives in a **separate git repo**. This repo contains design docs, scripts, and tooling.

## Commands

Rebuild the visualization site (`site/index.html`) from `site/content.md` and `site/diagrams/*.json`:
```bash
python3 scripts/build_site.py
```

Preview the site locally:
```bash
python3 -m http.server 8126 --bind 127.0.0.1 -d site
```

## Architecture

**Agent-first model:**
- Agent (Codex) is the primary orchestrator, monitoring the OS daily
- Scripts (`watch.py`, `deps.py`, `approve.py`) are deterministic tools called by the agent or human
- Agent reads `system/operating-rule/global.md + events/<type>.md` as processing guidelines

**Three actors, no overlap:**
- **Human**: controls review gate (approve / reject / request-changes)
- **Agent**: monitors, evaluates, creates PRs, updates inbox status
- **Code**: scans git diffs, computes dependency graphs, rebuilds derived files, performs merges

**Docs structure:**
- `docs/design.md` — single design document
- `docs/research/` — survey of current memory approaches and practitioner patterns (pending migration to vault knowledge base/)
- `docs/architecture/_archive/` — superseded design and implementation docs

**Archived (old prototype, not current):**
- `_archive/src/memory_system/` — Phase 0 JSON memory engine (deprecated)
- `_archive/tests/` — tests for the old prototype
