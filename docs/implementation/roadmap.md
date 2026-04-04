# Implementation Roadmap

## Phase 0: Research and framing

交付物：

- 当前实践调研
- 参考架构
- 开源项目边界

完成标准：

- 明确 KB 的结构层和处理流程
- 明确 MVP 不做什么
- 明确生产版演进方向

## Phase 1: Knowledge base foundation

交付物：

- `Capture / Store / Projections` 最小模型
- `kb/` 目录结构约定
- Obsidian-compatible vault schema
- 四个平台能力表：Claude Code / OpenClaw / Codex local / ChatGPT
- platform landing spec: OpenClaw / Claude Code / Codex / ChatGPT
- 节点类型定义：`profile/project/decision/topic/procedure/lesson`
- decision lifecycle：`proposed / active / superseded`
- frontmatter schema
- stable id 规则
- note templates
- usage SOP / operating workflow
- create / update / move / archive 操作接口
- same-day correction 规则：支持平台、写入位置、过期规则
- `Consolidate / Project` 规则
- ChatGPT export 和 delivery status 规则
- `examples/phase1-kb-first/` 这类真实文件例子

完成标准：

- 可以把长期知识稳定保存成树优先、可链接的文件系统
- 用户可以直接查看和编辑核心知识节点
- 用户可以在 Obsidian 中自然完成日常 capture / review / archive
- 节点可重命名、移动、归档而不丢 identity
- 已明确四个平台各自能做什么、做不到什么
- Claude / OpenClaw / Codex local 能消费最新 projection
- ChatGPT 能消费导出摘要
- 项目决策和主题知识不会混写

## Phase 2: Capture and ingestion

交付物：

- `inbox/` 和 `daily/` 入口
- raw observation schema
- source reference 规范
- chat / notes / files 的最小导入器
- basic normalization pipeline
- same-day correction inbox item
- correction 过期和关闭机制

完成标准：

- 原始输入可以先进入 KB，而不是直接写成稳定结论
- 每条输入都保留 provenance
- 用户可以手动检查原始输入与稳定知识之间的关系
- 用户与 agent 的写入边界清晰

## Phase 3: Organize / Dream pipeline

交付物：

- consolidation jobs
- inbox -> topic/entity merge
- absolute-date normalization
- conflict / invalidation handling
- hot / warm / cold adjustment
- archive routing
- local index rebuild

完成标准：

- raw inputs 不直接充当长期知识
- knowledge base 可持续整理，而不是只追加
- topic / entity 节点可以持续合并更新
- 被证伪事实可失效

## Phase 4: Projections and platform sync

交付物：

- OpenClaw projection
- Claude Code projection
- Codex local/cloud landing：`AGENTS.md` / `AGENTS.override.md` / `config.toml` / MCP
- ChatGPT summary projection
- projection freshness 规则和 rebuild triggers
- projection delivery status，尤其是 ChatGPT 这类手工平台
- projection read-only 和 import-back 规则
- Claude / OpenClaw / Codex local projection 刷新脚本
- ChatGPT export package
- 可选 backlink / metadata index
- FastAPI / MCP / SDK 最小接口
- embeddings / graph 作为可选加速件

完成标准：

- 不同平台都有明确的 projection 形态和 input path
- Claude / OpenClaw / Codex local 的 projection 刷新链路可跑通
- ChatGPT 能区分 `generated` 和 `delivered`
- index、embedding 和 graph 都是增强层，不是前置依赖

## Phase 5: Evolve pipeline

交付物：

- lesson extraction
- instinct rule schema
- skill synthesis jobs
- reusable commands / agent templates

完成标准：

- repeated corrections 可沉淀成 procedure
- 高频成功模式可升级为 skill
- evolve 结果可审查、可回退

## Phase 6: Data connectors and sync

优先级建议：

1. Chat exports / chat logs
2. Notes
3. Calendar
4. Tasks
5. Files
6. Obsidian / Markdown vault sync

完成标准：

- 所有接入源都输出统一事件协议
- provenance 可追溯
- 用户可按 source 关闭采集
- knowledge base 可与外部文件系统双向同步

## Phase 7: Evaluation and productization

交付物：

- 评测数据集
- 召回与污染率指标
- latency / cost dashboard
- 最小 Web UI

关键指标：

- recall@k
- stale-memory rate
- contradiction rate
- context token cost
- edit / delete success rate

## 开源协作建议

- `kb`: 目录结构、frontmatter、文件操作
- `workflow`: 模板、SOP、Obsidian 使用规范
- `capture`: inbox、daily、导入器
- `organize`: consolidate / dream / archive
- `projections`: projection 生成、平台同步、delivery status、API
- `evolve`: lessons / instincts / skills
- `indexes`: backlinks、embeddings、graph projections
- `connectors`: 外部数据源与 vault sync
- `evals`: 评测
- `examples`: 不同个人场景模板
