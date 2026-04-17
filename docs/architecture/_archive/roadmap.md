# Implementation Roadmap

补充说明：

- 经过 `2026-04-09` 这轮 practitioner research 之后，架构已经不是单纯的 `KB-first`
- 当前主方案已经升级成：`Capture / Workspace / Store / Projections`
- 但重点不是层数，而是：`review gate + clean/generated separation + path/properties/views + research knowledge + operational state + platform entry`

更完整的重设计说明见：

- [personal-os-design.md](../architecture/personal-os-design.md) (`2026-04-13` 起的当前主方案)
- [_archive/solution-design-v2.md](../architecture/_archive/solution-design-v2.md) (memory 子系统 Phase 1，已归档)
- [_archive/reframed-architecture.md](../architecture/_archive/reframed-architecture.md) (架构推理过程，已归档)
- [mvp-week1.md](mvp-week1.md) (Week 1 具体交付物)

> **说明**：下面的 Phase 0-7 是旧 KB-first 叙事的遗留，保留作为历史参考。当前主线已切换到 build-system 模型，最新交付节奏见 `mvp-week1.md` 和 `personal-os-design.md`。

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

- `Capture / Workspace / Store / Projections` 最小模型
- `Store` node families：`evidence / knowledge / state`
- `Workspace` model：`candidate / generated / ephemeral / review queue / promotion queue`
- 目录结构约定：`capture / workspace / store / projections`
- Obsidian-compatible vault mapping：`capture / workspace / store / _system`
- 分类规则：`Path / Properties / Views`
- 四个平台能力表：Claude Code / OpenClaw / Codex local / ChatGPT
- platform landing spec: OpenClaw / Claude Code / Codex / ChatGPT
- 节点类型定义：`source/observation/topic/entity/profile/goal/project/decision/procedure/lesson/review/people/routine`
- decision lifecycle：`proposed / active / superseded`
- 状态轴：`confirmed / candidate / clean / generated / persistent / ephemeral / source-backed / synthesized`
- 扁平 frontmatter schema
- 公共字段：`id / family / kind / title / status / project_refs / domain_refs / source_refs / origin_* / confirmed_*`
- stable id 规则
- note templates
- usage SOP / operating workflow
- Bases / inline index note spec
- review-gated promotion 规则
- create / update / move / archive 操作接口
- same-day correction 规则：支持平台、写入位置、过期规则
- `Consolidate / Project` 规则
- ChatGPT export 和 delivery status 规则
- `examples/phase1-kb-first/` 这类真实文件例子

完成标准：

- 可以把长期知识稳定保存成树优先、可链接的文件系统
- 用户可以直接查看和编辑核心知识节点
- `research knowledge` 和 `operational state` 已明确区分
- `clean` 和 `generated` 已明确区分
- `Path`、`properties`、`views` 的分工已经固定
- 一份文件只有一个 canonical home，但可以同时出现在多个视图里
- 关键文件可以兼做内容页和索引页
- 用户可以在 Obsidian 中自然完成日常 capture / review / archive
- 节点可重命名、移动、归档而不丢 identity
- 已明确四个平台各自能做什么、做不到什么
- Claude / OpenClaw / Codex local 能消费最新 projection
- ChatGPT 能消费导出摘要
- 项目决策和主题知识不会混写

## Phase 1.5: Graph & Temporal Enhancements (2026 Trend)

交付物：

- **Graph Explorer**: 基于 Markdown 链接的轻量级拓扑发现
- **Temporal Anchor**: 在 frontmatter 中强制记录 `created_at` 和 `superseded_at`
- **Identity Resolver**: 处理同名不同义或同义不同名的实体合并规则

完成标准：

- 能够识别知识库中的孤儿页面 (Orphan Pages)
- 能够按时间线回溯知识的演进过程 (Timeline view)

## Phase 2: Capture and ingestion

交付物：

- `capture/inbox/` 和 `capture/daily/` 入口
- raw observation schema
- source reference 规范
- chat / notes / files 的最小导入器
- basic normalization pipeline
- same-day correction feedback item
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

## Phase 3.5: Auto-Compiler & Self-Healing (Karpathy's LLM Wiki)

交付物：

- **Knowledge Compiler Loop**: 自动将 `raw/` 增量编译进相关 `topic/` 页面
- **Self-Healing Lint**: 自动检测陈旧说法、矛盾证据和断链
- **Web Gap Filler**: 自动检索补齐 Wiki 中的信息空缺

完成标准：

- 摄入新原始资料后，系统能自动更新 5-10 个关联页面
- 能够通过 Lint 脚本生成“知识库健康报告”

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

- 评测数据集 (针对个人场景)
- **LOCOMO (Long-term Conversational Memory) Benchmark** 适配
- 召回与污染率指标
- latency / cost dashboard
- 最小 Web UI

关键指标：

- recall@k
- stale-memory rate
- contradiction rate
- context token cost
- edit / delete success rate
- **Fact-Superseding Accuracy** (时序正确率)

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
