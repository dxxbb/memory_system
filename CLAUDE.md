# CLAUDE.md

This file provides guidance to Claude Code when working in **this repository (forge)**.

forge 的设计语言（build-system 隐喻、三角色分工、SP MVC 三层等）已在 vault 5 段 SP 里讲过，agent 通过 `~/.claude/CLAUDE.md` 读到，本文件不再复述。

## Repository facts

- forge 是设计文档 + 脚本 + tooling 仓库；OS 数据本身在 vault（独立 git repo，本机 `~/dxy_OS/`）
- 单一设计文档：`docs/design.md`（运转机制 + MVP Week 1 落地 + Obsidian 前端）
- onepage 不在本仓库，在 vault `03 workspace/project/forge/onepage.md`（权威版本）
- 调研材料在 vault `04 knowledge base/`（2026-04-17 PR 0005 迁出）

## Current focus

MVP Week 1 闭环已跑通（vault SP `Workspace` 段有详情）。下一步从 `events/` guideline 补全开始。

## Commands

Rebuild 可视化站点（`site/index.html`）：
```bash
python3 scripts/build_site.py
```

本地预览：
```bash
python3 -m http.server 8126 --bind 127.0.0.1 -d site
```

## Archived

- `_archive/src/memory_system/` — Phase 0 JSON memory engine（已废弃）
- `_archive/tests/` — 老 prototype 的测试
- `docs/architecture/_archive/` — 被合并进 `docs/design.md` 的旧设计文档
