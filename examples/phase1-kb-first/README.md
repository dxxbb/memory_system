# Phase 1 Solid Example

这个目录放一组真实文件，用来说明这套设计到底怎么落地。

场景只有一个：

- `2026-04-03` 用户说：`文档少用抽象句式，每节保留 1 个例子。`
- 同一天又确认：`这个项目 Phase 1 先做 knowledge base。`

## 这次操作实际改了哪些文件

### 第一步：当天立刻生效

当天先改 5 个地方。

1. 新建 `kb/inbox/2026-04-03-writing-style.md`
2. 更新 `kb/daily/2026-04-03.md`
3. 更新 `projections/claude/CLAUDE.memory.md`
4. 更新 `projections/openclaw/MEMORY.md`
5. 更新 `codex-repo/AGENTS.md`

当天不会自动改 ChatGPT 里的项目文件。
当天只会在本地生成新的 `projections/chatgpt/project-summary.md`，并标记 `delivery_status: pending`。

说明：

- 这个目录保留的是 consolidate 后的最终状态
- 所以当天创建的 `kb/inbox/2026-04-03-writing-style.md`，最后会出现在 `kb/archive/2026-04-03-writing-style.md`

### 第二步：晚上做 consolidate

晚上再改 5 个地方。

1. 更新 `kb/profile/user.md`
2. 新建 `kb/decisions/phase-1-kb-first.md`
3. 更新 `kb/projects/personal-memory-system.md`
4. 把当天的 correction item 从 `inbox/` 移到 `archive/`
5. 重跑四个平台的 projection

## 第一步要改成什么

### 1. 新建 correction item

路径：

- `kb/inbox/2026-04-03-writing-style.md`

内容：

```yaml
---
id: kb-correction-writing-style-2026-04-03
kind: correction
status: open
apply_now: true
targets: [claude, openclaw, codex]
expires_at: 2026-04-04
source_refs:
  - chat:2026-04-03:writing-style
---
文档少用抽象句式，每节保留 1 个例子。
```

这个文件的作用很单一：

- 让 Claude Code、OpenClaw、Codex local 当天就能看到这条纠正

### 2. 在 daily 里记候选决策

路径：

- `kb/daily/2026-04-03.md`

新增一行：

```md
- [candidate decision] 这个项目 Phase 1 先做 knowledge base。
```

### 3. 当天先改三个文件型平台的 projection

`projections/claude/CLAUDE.memory.md` 新增：

```md
- 文档少用抽象句式，每节保留 1 个例子
```

`projections/openclaw/MEMORY.md` 新增：

```md
- 文档少用抽象句式，每节保留 1 个例子
```

`codex-repo/AGENTS.md` 新增：

```md
- 文档少用抽象句式，每节保留 1 个例子
```

这里要注意一条硬规则：

- 这份内容必须落到 Codex 会自动发现的 `AGENTS.md`
- 只生成一个 `projections/codex/*.md`，Codex 默认不会自动读到

### 4. 生成 ChatGPT export，但不假装它已经送达

路径：

- `projections/chatgpt/project-summary.md`

关键元数据：

```yaml
delivery_status: pending
```

这一步说明了一个硬边界：

- 本地生成了新 summary
- 不等于 ChatGPT 已经用上了它

## 第二步要改成什么

### 1. 把纠正写进 profile

路径：

- `kb/profile/user.md`

新增一行：

```md
- 文档每节保留 1 个例子
```

### 2. 把候选决策变成正式 decision

路径：

- `kb/decisions/phase-1-kb-first.md`

内容：

```yaml
---
id: kb-decision-phase-1-kb-first
kind: decision
status: active
created_at: 2026-04-03
updated_at: 2026-04-03
source_refs:
  - daily:2026-04-03
---
Phase 1 先做 knowledge base。
```

### 3. 在 project 文件里引用 decision

路径：

- `kb/projects/personal-memory-system.md`

新增一行：

```md
- 当前决策：[[../decisions/phase-1-kb-first]]
```

### 4. 关闭 correction item

这一步不要直接删文件。

做法：

- 把 `kb/inbox/2026-04-03-writing-style.md` 移到 `kb/archive/2026-04-03-writing-style.md`
- 把 `status` 改成 `resolved`
- 加上 `resolved_to: kb/profile/user.md`

## 这组文件暴露出来的设计问题

这个例子跑完之后，设计里有 4 个问题是确定存在的。

### 1. ChatGPT 只能 export，不能自动送达

所以 `generated_at` 不够，必须有：

- `delivery_status`
- `delivered_at`

### 2. decision 不能只写在 daily 里

否则项目运行几天后，谁都不知道当前有效决策是什么。

### 3. correction item 必须有关闭动作

否则 `inbox/` 会越堆越多，same-day correction 会污染主视图。

### 4. project 文件必须引用当前 decision

不然用户打开项目文件时，看不到当前生效的决策。

## 目录说明

这个目录里放的是 consolidate 后的稳定状态。

你可以直接打开这些文件看最终落地长什么样：

- `kb/profile/user.md`
- `kb/projects/personal-memory-system.md`
- `kb/decisions/phase-1-kb-first.md`
- `kb/topics/memory-architecture.md`
- `kb/procedures/weekly-consolidation.md`
- `kb/daily/2026-04-03.md`
- `kb/archive/2026-04-03-writing-style.md`
- `projections/claude/CLAUDE.memory.md`
- `projections/openclaw/MEMORY.md`
- `codex-home/AGENTS.md`
- `codex-home/config.toml`
- `codex-repo/AGENTS.md`
- `projections/chatgpt/project-summary.md`
