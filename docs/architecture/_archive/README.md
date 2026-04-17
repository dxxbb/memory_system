# Architecture Archive

这里存放被后续版本取代、但保留作为历史参考的架构与实施文档。

## 为什么保留

被取代的文档仍然有价值，因为：

- 记录了架构演进的推理过程
- 当前方案里的一些决定需要对比旧方案才能理解
- 未来如果要回溯"为什么当初没走 X 路线"，这些旧文档是答案

## 当前归档

| 文件 | 原位置 | 归档日期 | 取代者 / 备注 |
|---|---|---|---|
| `reference-architecture.md` | `docs/architecture/reference-architecture.md` | `2026-04-13` | `solution-design-v2.md` → `personal-os-design.md` |
| `solution-design-v1.md`(原名 `solution-design.md`) | `docs/architecture/solution-design.md` | `2026-04-13` | `solution-design-v2.md` → `personal-os-design.md` |
| `solution-design-v2.md` | `docs/architecture/solution-design-v2.md` | `2026-04-13` | `personal-os-design.md`（KB-first 方案被 build-system 取代） |
| `reframed-architecture.md` | `docs/architecture/reframed-architecture.md` | `2026-04-13` | 仅作架构演进推理过程的历史参考 |
| `x-thread-ingest.md` | `docs/architecture/x-thread-ingest.md` | — | 具体 ingest 流程早期草稿 |
| `personal-os-design.md` | `docs/architecture/personal-os-design.md` | `2026-04-17` | `docs/design.md`（内容合并） |
| `platform-landing-review.md` | `docs/architecture/platform-landing-review.md` | `2026-04-17` | 旧 KB-first 平台落地方案，已被 build-system 模型 + 只针对 Claude Code 的聚焦取代 |
| `mvp-week1.md` | `docs/implementation/mvp-week1.md` | `2026-04-17` | `docs/design.md` §14（内容合并） |
| `roadmap.md` | `docs/implementation/roadmap.md` | `2026-04-17` | 自述"Phase 0-7 是旧 KB-first 叙事的遗留"，整份归档 |
| `obsidian-kb-sop.md` | `docs/implementation/obsidian-kb-sop.md` | `2026-04-17` | 04-03 前的 `capture / workspace / store / _system` 四层方案，已被 build-system 模型 + 极简 frontmatter 取代；当前 Obsidian 约定见 `docs/design.md` §13 |

## 当前主文档

归档之外，活跃的设计文档只有一份：

- [../../design.md](../../design.md) —— forge 的单一设计文档（运转机制 + MVP Week 1 落地 + Obsidian 前端约定）

onepage 在 vault `workspace/project/forge/onepage.md`，不在本仓库。

