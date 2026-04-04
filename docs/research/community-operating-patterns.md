# Community Operating Patterns

更新时间：`2026-04-03`

这份文档整理来自实际工具与社区工作流的模式，重点不是“官方定义”，而是个人 memory 系统在真实使用中的操作习惯。以下内容基于你提供的调研笔记归纳，适合作为架构输入，而不是最终事实来源。

## 核心判断

这些案例共同说明了一件事：

- `Memory is an asset`
- 它不是只负责 `save and retrieve`
- 它还需要 `organize` 和 `evolve`

因此，个人 memory 系统至少要回答四个问题：

1. 怎么捕获 session、事件和观察？
2. 怎么把原始记录整理成稳定知识？
3. 怎么把重复 lesson 提炼成行为规则或技能？
4. 怎么让最重要的信息常驻，低价值内容自动降级和归档？

## 1. File-first memory 仍然很强

从 OpenClaw 这一类实践看，file-first 方案的优点很明确：

- session 原始记录易保存，常见形式是 `jsonl`
- daily memory 天然适合按日期滚动
- `memory.md` 这类核心文件适合放进上下文窗口常驻
- 所有内容都可搜索、可编辑、可 git 管理

项目启发：

- canonical store 可以是数据库，但必须支持导出到 file projection
- file projection 对个人用户很重要，因为它可读、可 diff、可 hand-edit
- `memory.md` 应被视为 `HOT` memory projection，而不是全部 memory 本体

## 2. Organize / Dream 是 memory 系统的必要后台任务

Auto Dream 一类方案说明，“记住”之后还必须做 consolidation：

- 从 session / notes 中采集原始 observations
- 合并进现有 topic files
- 将相对时间改成绝对时间
- 删除被证伪的旧事实
- prune 和 re-index

项目启发：

- organize 不是可选优化，而是长期可用性的核心
- raw event 不应直接等于最终知识
- topic memory 应由后台 consolidation 产生

推荐抽象：

- `capture`: 保存 session、note、event、observation
- `consolidate`: merge / dedupe / conflict-resolve / reindex
- `project`: 输出 `MEMORY.md`、topic files、search index

## 3. Evolve 代表从记忆到能力的升级

Everything Claude Code 和 self-improving 工作流都指向同一类机制：

- 从 session 中抽取 repeated patterns
- 记录 trigger / action / confidence / scope
- 把 lesson 聚类为更稳定的 skills / commands / agents

这意味着 memory 系统不能只沉淀“知道了什么”，还要沉淀“以后该怎么做”。

项目启发：

- `procedural memory` 需要单独建模
- repeated corrections 比普通 facts 更值得提炼为 procedure
- skills / commands / agents 更像是从 memory 推导出的高阶资产

推荐抽象：

- `observation`: 原始观察
- `lesson`: 明确的经验或纠偏
- `instinct`: 可复用 trigger-action 规则
- `skill`: 多个 lesson / instinct 聚类后的稳定能力单元

## 4. HOT / WARM / COLD 是很实用的 serving model

self-improving 模式里的三层加载方式非常适合个人 memory：

- `HOT`: 始终加载，如 `memory.md`、corrections、关键约束
- `WARM`: 按 project / domain 按需加载
- `COLD`: 长期归档，仅回溯时使用

这层分类和 `semantic / episodic / procedural` 不是一回事。

更准确地说：

- `memory type` 决定内容语义
- `temperature` 决定加载策略

项目启发：

- 不应只按内容类型建模，还要按 serve policy 建模
- promote / demote / archive 应成为后台任务
- 冲突优先级可以是 `project > domain > global`，同层 recent wins

## 5. Knowledge base 是 memory 的重要投影层

Obsidian 这类知识库对个人场景仍然重要，因为：

- 用户习惯直接读写 Markdown
- topic pages 比原始 event 更容易维护
- 知识网络可作为人工审阅界面

但它更适合作为 projection layer，而不是唯一 canonical store：

- canonical source 应保留事件、时间、来源和失效机制
- knowledge base 可由 canonical memory 生成
- 用户也可以直接编辑 knowledge base，再回写 canonical memory

## 对本项目的直接影响

基于这些社区模式，项目需要补上的不是更多“检索技巧”，而是完整生命周期：

1. `Capture`: session / note / event / correction / reflection
2. `Organize`: merge、absolute-date normalization、conflict cleanup、topic projection
3. `Serve`: profile + hot memories + relevant warm memories + cold recall
4. `Evolve`: lesson extraction、instinct formation、skill synthesis

## 建议的仓库模块

- `core`: canonical models 和 retrieval
- `capture`: 各类 adapter 和 observation ingestion
- `organize`: dream / consolidate / topic projection
- `evolve`: lessons / instincts / skills
- `serve`: context assembly、API、MCP、SDK
- `projections`: Markdown knowledge base、topic files、memory.md

## 参考案例

- OpenClaw
- Auto Dream: <https://claudefa.st/blog/guide/mechanics/auto-dream>
- Everything Claude Code: <https://github.com/affaan-m/everything-claude-code>
- Self-improving workflow: <https://clawhub.ai/ivangdavila/self-improving>
- BMAD METHOD: <https://github.com/bmad-code-org/BMAD-METHOD>
