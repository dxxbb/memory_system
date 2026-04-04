# Reference Architecture

## 1. 目标

这个项目 Phase 1 要做成下面这个形态：

- 一套三块结构：`Capture`、`Store`、`Projections`
- 一份本地、可编辑的 `Store`
- 三份 repo 内 `Projections`：OpenClaw、Claude Code、ChatGPT
- 一组 Codex 正式入口文件：`~/.codex/AGENTS.md`、repo `AGENTS.md`、`config.toml`
- 一条稳定路径：新信息先进入 `Capture`，再进 `Store`，再刷新 `Projections`
- 一条同天纠正路径：文件型平台当天生效，ChatGPT 走导出和手工送达

这版架构只解决一件事：

- 让 `knowledge base -> platform use` 这条链路先跑通

这版架构不解决这些事：

- vector-first 检索
- graph-first 组织
- 自动 skill synthesis
- 普通 ChatGPT 自动读取本地 KB

## 2. 最小结构

这版架构只保留 3 个结构块：

- `Capture`：`daily/`、`inbox/`、raw inputs
- `Store`：稳定、当前有效、可持续维护的长期内容
- `Projections`：按平台生成的派生视图和入口文件

两条动作：

- `Consolidate`：把 `Capture` 和平台侧确认的改动并进 `Store`
- `Project`：从 `Store` 刷新各平台的 `Projections`

可视化说明放到独立页面：

- `site/index.html`

这个页面不是手写正文页，而是由下面两类源生成：

- `site/content.md`
- `site/diagrams/*.json`

## 3. 平台能力表

这里直接写死四个平台的已知能力。

| 平台 | 正式入口 | 自动读取本地 Store | same-day correction | Phase 1 角色 |
| --- | --- | --- | --- | --- |
| Claude Code | `CLAUDE.md`、imports、hooks `additionalContext` | 否 | 支持 | 一等平台 |
| OpenClaw | `MEMORY.md`、`memory/YYYY-MM-DD.md`、memory tools | 否 | 支持 | 一等平台 |
| Codex local | `~/.codex/AGENTS.md`、repo `AGENTS.md`、repo files、MCP | 否 | 支持 | 一等平台 |
| ChatGPT | project instructions、project files、saved memory、project memory | 否 | 不支持自动 same-day local sync | projection consumer |

平台结论：

- Claude Code、OpenClaw、Codex local 可以做“本地 `Capture + Store + Projections`”这条链路
- ChatGPT 只能消费你已经放进去的内容
- 普通 ChatGPT 聊天不能自动看到你本地刚改的 `Store`

## 4. Capture / Store / Projections

Phase 1 的目录就做成这样：

```text
kb/
  profile/
    user.md
  projects/
    personal-memory-system.md
  decisions/
    phase-1-kb-first.md
  topics/
    memory-architecture.md
  procedures/
    weekly-consolidation.md
  lessons/
  daily/
    2026-04-03.md
  inbox/
    2026-04-03-writing-style.md
  archive/

projections/
  claude/
    CLAUDE.memory.md
  openclaw/
    MEMORY.md
  chatgpt/
    project-summary.md
```

这里的角色很明确：

- `kb/daily/` 和 `kb/inbox/` 属于 `Capture`
- `kb/profile/`、`kb/projects/`、`kb/decisions/`、`kb/topics/`、`kb/procedures/`、`kb/lessons/` 属于 `Store`
- `projections/` 属于 repo 内 `Projections`
- Codex 也属于 `Projections`，只是它的 projection 不放在 `projections/` 目录，而是落在它会发现的正式入口文件

仓库里已经放了一套真实例子：

- `examples/phase1-kb-first/`

后面第 7 节说的所有改动，都是按这组文件展开的。

## 5. Store 的节点

Phase 1 先固定 6 类节点：

- `profile`
- `project`
- `decision`
- `topic`
- `procedure`
- `lesson`

建议保留的最小 frontmatter：

```yaml
---
id: kb-decision-phase-1-kb-first
kind: decision
title: Phase 1 KB First
status: active
created_at: 2026-04-03
updated_at: 2026-04-03
source_refs: []
---
```

每类节点的最小例子：

`kb/profile/user.md`

```md
- 写作尽量简单直接
- 文档每节保留 1 个例子
```

`kb/projects/personal-memory-system.md`

```md
- 目标：做个人 memory system 的开源方案
- 当前阶段：把 knowledge base 先做扎实
```

`kb/decisions/phase-1-kb-first.md`

```md
- 决定：Phase 1 先做 knowledge base
- status: active
```

`kb/topics/memory-architecture.md`

```md
- 目录树是骨架，链接是增强层
```

`kb/procedures/weekly-consolidation.md`

```md
1. 清理 inbox
2. 合并稳定结论
3. 刷新 projections
```

## 6. 四个平台怎么落地

### Claude Code

交付物：

- `projections/claude/CLAUDE.memory.md`

落地方式：

- repo 里的 `CLAUDE.md` 用 `@import` 或直接引用这份 projection
- 当天新纠正通过 hook 的 `additionalContext` 进入会话

结果：

- Claude Code 用 projection 工作
- 当天纠正可以马上生效

### OpenClaw

交付物：

- `projections/openclaw/MEMORY.md`

落地方式：

- 同步到 OpenClaw workspace 的 `MEMORY.md`
- daily memory 继续走 `memory/YYYY-MM-DD.md`
- memory tools 用来搜补充信息

结果：

- OpenClaw 用 Markdown memory 工作
- 当天纠正可以马上生效

### Codex local

落地方式：

- 个人稳定偏好放 `~/.codex/AGENTS.md`
- 项目规则和当前结论放 repo 根目录 `AGENTS.md`
- 子目录需要覆盖时，放该目录下的 `AGENTS.override.md` 或 `AGENTS.md`
- repo 外的 KB 通过 `~/.codex/config.toml` 或项目级 `.codex/config.toml` 配置 MCP
- 如果要做生成器，生成结果必须写进这些可发现文件之一；只放在 `projections/` 里不会自动生效

结果：

- Codex local 按 `AGENTS.md` 发现规则工作
- 当天纠正可以在本地运行时里马上生效

### ChatGPT

交付物：

- `projections/chatgpt/project-summary.md`

落地方式：

- 放进 project files
- 必要时同步到 project instructions 或 project memory

结果：

- ChatGPT 只消费你已经上传或写入项目的内容
- 本地 KB 不会自动同步进去

## 7. 两条主流程

这版只保留两条主流程，不再引入别的概念。

### 流程 A：标准路径

适用内容：

- 普通新信息
- 主题知识
- 项目上下文
- 稳定偏好

路径：

1. 先写进 `Capture`
2. 做 `Consolidate`
3. 更新 `Store`
4. 做 `Project`
5. 刷新各平台的 `Projections`

### 流程 B：同天纠正

适用内容：

- 用户明确纠正
- 当天就要生效的规则
- 正在执行中的写作或行为约束

落地点：

- `kb/inbox/2026-04-03-writing-style.md`

最小例子：

```yaml
---
id: kb-inbox-writing-style-2026-04-03
kind: correction
apply_now: true
targets: [claude, openclaw, codex]
expires_at: 2026-04-04
status: open
---
文档少用抽象句式，每节保留 1 个例子。
```

路径：

1. 先写进 `kb/inbox/`
2. 立刻刷新目标平台的 `Projections`
3. 晚些时候 `Consolidate` 进 `Store`
4. 关闭 inbox 条目

ChatGPT 的处理：

- 生成新的 projection：`project-summary.md`
- 标记 `delivery_status: pending`
- 由用户手工更新项目文件或项目说明

## 8. 一个 solid 的真实例子

这个例子不是故事，是真实文件。

目录在：

- `examples/phase1-kb-first/`

要模拟的操作只有两句：

- `文档少用抽象句式，每节保留 1 个例子。`
- `这个项目 Phase 1 先做 knowledge base。`

### 第一步：当天立刻改什么

当天真正改动的文件是这几个：

1. 新建：
   `examples/phase1-kb-first/kb/inbox/2026-04-03-writing-style.md`
2. 更新：
   `examples/phase1-kb-first/kb/daily/2026-04-03.md`
3. 更新：
   `examples/phase1-kb-first/projections/claude/CLAUDE.memory.md`
4. 更新：
   `examples/phase1-kb-first/projections/openclaw/MEMORY.md`
5. 更新：
   `examples/phase1-kb-first/codex-repo/AGENTS.md`
6. 生成但不送达：
   `examples/phase1-kb-first/projections/chatgpt/project-summary.md`

注意：

- 第 1 步创建的 `inbox` 文件，在晚上 consolidate 后会移动到
  `examples/phase1-kb-first/kb/archive/2026-04-03-writing-style.md`
- 例子目录里保留的是 consolidate 后的最终状态
- Codex 这一侧放的是它实际会读取的 `AGENTS.md`

当天最关键的三处改动是：

`examples/phase1-kb-first/kb/inbox/2026-04-03-writing-style.md`

```yaml
kind: correction
status: open
apply_now: true
targets: [claude, openclaw, codex]
expires_at: 2026-04-04
```

`examples/phase1-kb-first/kb/daily/2026-04-03.md`

```md
- [candidate decision] 这个项目 Phase 1 先做 knowledge base。
```

`examples/phase1-kb-first/projections/chatgpt/project-summary.md`

```yaml
delivery_status: pending
```

这一步的真实含义只有一个：

- Claude Code、OpenClaw、Codex local 当天能用上这条纠正
- ChatGPT 当天只能生成新摘要，不能假装已经自动生效

### 第二步：晚上 consolidate 改什么

晚上真正改动的文件是这几个：

1. 更新：
   `examples/phase1-kb-first/kb/profile/user.md`
2. 新建：
   `examples/phase1-kb-first/kb/decisions/phase-1-kb-first.md`
3. 更新：
   `examples/phase1-kb-first/kb/projects/personal-memory-system.md`
4. 移动并更新：
   `examples/phase1-kb-first/kb/inbox/2026-04-03-writing-style.md`
   ->
   `examples/phase1-kb-first/kb/archive/2026-04-03-writing-style.md`
5. 重跑各平台 projection

晚上最关键的三处改动是：

`examples/phase1-kb-first/kb/profile/user.md`

```md
- 文档每节保留 1 个例子
```

`examples/phase1-kb-first/kb/decisions/phase-1-kb-first.md`

```yaml
kind: decision
status: active
```

`examples/phase1-kb-first/kb/projects/personal-memory-system.md`

```md
- 当前决策：[[../decisions/phase-1-kb-first]]
```

这一步说明：

- 写作纠正最终应该落进 `profile`
- 项目决定最终应该落进 `decision`
- `project` 文件里必须能看到当前 decision

### 这个例子逼出来的设计问题

这组实际改动把 4 个问题逼得很清楚。

1. `ChatGPT` 只有 export，没有自动送达  
所以 `generated_at` 不够，必须有 `delivery_status`

2. `project` 文件不能只写目标，必须写当前 decision  
不然项目文件打开时看不到当前生效的决定

3. `correction item` 不能只创建，不关闭  
不然 `inbox/` 会一直堆积

4. `same-day correction` 必须带目标平台  
不然你不知道这条纠正今天该推给谁

## 9. 已知问题

这版已经能落地，但有 4 个明确问题。

### 1. projection 会过期

解决：

- 每个 projection 记录 `generated_at`
- 每个 projection 记录 `source_nodes`

### 2. ChatGPT 的送达是手工动作

解决：

- 给 ChatGPT projection 加 `delivery_status`
- 区分 `generated` 和 `delivered`

### 3. 平台入口里的热修正会和主库分叉

解决：

- platform file 默认只当副本
- 所有长期改动都先回写 `Capture`，再并进 `Store`

### 4. same-day correction 只覆盖三类平台

解决：

- Phase 1 直接接受这个限制
- 不把 ChatGPT 当成 same-day runtime

## 10. Phase 1 交付物

Phase 1 交付物只保留这些：

- `Capture / Store / Projections` 的最小结构
- 节点类型和 frontmatter
- `daily/`、`inbox/`、`profile/`、`projects/`、`decisions/`、`topics/`、`procedures/`
- OpenClaw / Claude Code / ChatGPT 的 projection 模板
- Codex 的 `AGENTS.md` / `AGENTS.override.md` / `config.toml` 落地规则
- Claude / OpenClaw / Codex local 的 projection 刷新脚本
- ChatGPT 的 export 文件和 delivery status
- `Consolidate` 和 `Project` 规则

Phase 1 完成标准：

- 用户能在本地维护一份长期 `Store`
- 三个文件型平台能消费最新 projection
- ChatGPT 能稳定消费导出摘要
- 决策、主题知识、偏好不会混写
