# Obsidian KB SOP

## 目的

这份文档定义：

- 如果用 Obsidian 作为前端，vault 应该怎么组织
- 平时怎么记、怎么整理、怎么确认
- agent / 系统应如何和这套 vault 配合

Obsidian 在这里的角色很明确：

- `human-facing workspace and knowledge frontend`

它适合做：

- 查看
- 编辑
- 导航
- review

它不负责替代：

- projection 构建
- 派生索引
- 平台同步逻辑

## 基本原则

1. `Path` 只表达主归属。
2. 多维度信息写进 properties，不塞进目录。
3. 多视图靠 `links / Bases / tags`，不靠复制文件。
4. generated / candidate 内容先进入 `workspace/`。
5. confirmed / clean / persistent 内容才进入 `store/`。
6. projection 和 indexes 默认不放进主要浏览区。

一句话：

- `single home, multiple views`

## 推荐 vault 结构

如果把 Obsidian 作为主前端，推荐这样组织：

```text
capture/
  inbox/
  daily/
  imports/
  feedback/

workspace/
  candidates/
  ephemeral/
  reviews/
  promote/

store/
  evidence/
    sources/
    clips/
    observations/
    extracts/
  knowledge/
    topics/
    entities/
    syntheses/
    comparisons/
  state/
    profile/
    goals/
    projects/
    decisions/
    procedures/
    lessons/
    reviews/
    people/
    routines/

_system/
  projections/
  indexes/
  templates/
```

### 目录职责

- `capture/`
  放原始输入、当天记录、平台回流
- `workspace/`
  放待 review 的整理稿、candidate summary、临时工作页
- `store/evidence/`
  放可追溯来源和原始证据
- `store/knowledge/`
  放 topic / entity / synthesis
- `store/state/`
  放 profile / project / decision / procedure / lesson / review / people / routine
- `_system/projections/`
  放平台 projection，可在 Obsidian 里弱可见，或直接放 vault 外
- `_system/indexes/`
  放派生索引，不当真相源
- `_system/templates/`
  放 note 模板和 projection 模板

## 路径、properties、views 怎么分工

### 路径

路径只回答一个问题：

- 这份 note 本体是什么

例如：

- `store/knowledge/topics/karpathy-llm-wiki.md`

这表示：

- 它是一个 `knowledge/topic`

### Properties

下面这些都应该进 properties：

- 属于哪个项目
- 属于哪个领域
- 是谁生成的
- 是否已确认
- 需要出现在什么视图里

例如：

- `project_refs: [ai-os]`
- `domain_refs: [memory, knowledge-compiler]`
- `origin_author_id: codex`
- `status: confirmed`
- `confirmed_by: user`

### Views

同一篇 note 可以同时出现在：

- `AI OS` 项目页
- `memory` 主题页
- `confirmed` 的 Bases 视图
- `origin_author_id = codex` 的 Bases 视图

这些都不需要复制文件。

更直接地说：

- `memory.md`、`ai-os.md`、`project.md` 这类普通文件，本身就可以兼做索引页

## 推荐 frontmatter

在 Obsidian 里，frontmatter 建议尽量扁平。

```yaml
---
id: kn_karpathy_llm_wiki
family: knowledge
kind: topic
title: Karpathy LLM Wiki
summary: Karpathy 的 LLM Wiki 方案研究笔记。

status: confirmed
cleanliness: clean
persistence: persistent
grounding: source-backed

project_refs:
  - ai-os
domain_refs:
  - memory
  - knowledge-compiler
view_refs:
  - ai-os
  - memory

origin_author_type: agent
origin_author_id: codex
origin_mode: generated

confirmed_by: user
confirmed_at: 2026-04-09

source_refs:
  - https://x.com/karpathy/status/2039805659525644595
  - https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

tags:
  - ai-os
  - research
  - knowledge-compiler

created_at: 2026-04-09
updated_at: 2026-04-09
---
```

### 公共字段

必须有：

- `id`
- `family`
- `kind`
- `title`
- `status`
- `created_at`
- `updated_at`

推荐有：

- `summary`
- `cleanliness`
- `persistence`
- `grounding`
- `project_refs`
- `domain_refs`
- `view_refs`
- `source_refs`
- `origin_author_type`
- `origin_author_id`
- `origin_mode`
- `confirmed_by`
- `confirmed_at`
- `tags`

### 推荐枚举

`status`

- `candidate`
- `confirmed`
- `superseded`
- `archived`
- `invalid`

`cleanliness`

- `generated`
- `clean`

`persistence`

- `ephemeral`
- `persistent`

`grounding`

- `source-backed`
- `synthesized`
- `mixed`

### family-specific 字段

按需要补少量专用字段，例如：

`store/state/decisions/`

- `decision_status: proposed | active | superseded`
- `effective_from`
- `supersedes`

`store/state/projects/`

- `project_status: active | paused | done | archived`

## Property 和 Tag 的分工

这条规则要固定下来：

- `property` 用来做模型
- `tag` 用来做视图

适合做 property 的：

- `family`
- `kind`
- `status`
- `project_refs`
- `origin_author_id`
- `confirmed_by`

适合做 tag 的：

- `#research`
- `#memory`
- `#ai-os`
- `#generated`

不要把下面这些只写成 tag：

- confirmed
- origin
- project
- decision status

## 节点命名规范

建议：

1. 文件名短、清晰、可读
2. 文件名服务人类，不放 UUID
3. `id` 才是稳定 identity
4. 标题和文件名尽量接近

示例：

- `store/knowledge/topics/karpathy-llm-wiki.md`
- `store/state/projects/personal-memory-system.md`
- `store/state/decisions/phase-1-store-first.md`
- `store/knowledge/topics/memory.md`

## 日常使用 SOP

## 1. 新信息怎么进来

规则：

- 零散信息先写 `capture/inbox/`
- 当天工作记录写 `capture/daily/`
- 大体量导入写 `capture/imports/`
- 平台侧新纠正写 `capture/feedback/`
- 不确定的总结不要直接写 `store/`

## 2. agent 整理稿放哪

规则：

- agent 产出的 summary / merge draft / synthesized note 先放 `workspace/`
- 需要 review 的内容放 `workspace/reviews/`
- 待 promote 的内容放 `workspace/promote/`

这一步的目标是：

- 允许 agent 大量工作
- 但不直接污染主库

## 3. 什么内容可以进 store

只有满足下面条件，才写进 `store/`：

1. 内容比较稳定
2. 后面还会复用
3. 来源基本清楚
4. 经过了人的确认，或者确认规则已经明确

常见例子：

- 长期偏好
- 项目决策
- 可复用 procedure
- 稳定的 topic synthesis

## 4. 怎么做多视图

推荐先做 2 种视图：

1. 普通文件里的相关链接
   例如 `memory.md`、`personal-memory-system.md`
2. `Bases`
   例如：
   - `status = candidate`
   - `project_refs contains ai-os`
   - `origin_author_id = codex`

## 5. 每日流程

建议每天做一次轻量操作：

1. 打开当天 `capture/daily/`
2. 把零散输入记入 `capture/inbox/`
3. 把 agent 新产出的候选稿放进 `workspace/`
4. 给值得长期保留的内容补上 `project_refs` / `domain_refs`
5. 如有需要，在相关文件里补一组相关链接

## 6. 每周整理

建议每周做一次 consolidate：

1. 清理 `capture/inbox/`
2. review `workspace/reviews/`
3. 把可确认内容 promote 到 `store/`
4. 更新关键文件里的相关链接和 Bases
5. 刷新 projection
6. 归档低活跃或失效内容

## 7. 月度回顾

建议每月做一次结构回顾：

1. 看哪些 lessons 反复出现
2. 看哪些 procedures 可以升级
3. 看哪些主题页或项目页已经失去入口作用
4. 看哪些 generated 内容应该清理或合并

## Agent / 系统 SOP

## 1. 读取顺序

agent 默认先读：

1. 对应平台的 projection
2. 当前任务相关的 `store/state/projects/`
3. 相关 `store/state/decisions/` 和 `store/state/procedures/`
4. 相关 `store/knowledge/`
5. 必要时再补 `workspace/` 和当天 `capture/`

## 2. 写入顺序

agent 默认按下面顺序写：

1. 原始观察写 `capture/`
2. candidate summary 写 `workspace/`
3. 经过 review 的稳定结果才写 `store/`
4. projection 统一由 `Project` 步骤刷新

## 3. 移动与重命名

规则：

- 可以移动文件
- 可以重命名文件
- `id` 必须保持不变
- 必要时补 `aliases` 或 redirect note

路径变化不代表新对象。

## 4. 不建议的用法

- 把项目、来源、确认状态都塞进目录名
- 把所有 generated 内容直接写进 `store/`
- 让 `_system/` 充满用户日常要看的页面
- 只靠 tag 记录关键治理字段
- 把 `capture/daily/` 直接当长期知识库
