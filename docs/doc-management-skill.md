---
kind: source
status: draft-v3
intended_target: vault assist/tool/skills/doc-management.md
---

# Skill Draft: Document Management

> v2 草稿。目标：**项目无关** 的文档管理 skill。任何软件 / 研究项目的 docs 树都适用。forge 只是一个应用 case，不是 skill 的主体。

## What this skill is

管理项目文档的通用 craft：文档该在哪、怎么演进、怎么不腐烂。

适用于任何有 docs 树的项目，不限语言 / 栈 / 规模。

## 4 Principles

1. **Single source of truth** — 任何 fact / 设计 / 状态不允许出现在两个 doc 里。发现重复 = 立刻合并。
2. **Consolidate before create** — 要写新 doc 前先 grep：已有 doc 能吸收它吗？能就吸收，不能再新建。
3. **Outcome landed = archive source** — proposal / design / plan 一旦实现 ship，原 doc 立即进对应 `_archive/`。活跃目录只放"当前真实"的 doc，不放"历史参考"。历史靠 git history + `_archive/` 索引表。
4. **Journal-grade or clearly Scratch** — 活跃目录的 doc 要么达到 share-grade（永久），要么在 `scratch/` 并带明确退出路径（临时）。不允许"半永久的中等质量 doc"在活跃目录里滞留。

## 6 Generic Doc Types

每个项目都有这 6 类，名字可变，角色固定：

| Type | Role | 典型路径 |
|---|---|---|
| **Entry** | 新人 / agent 的入口索引 | 仓库根 `README.md` / `AGENTS.md` / `CLAUDE.md` |
| **Design** | 当前方案的架构与决策 | `docs/design.md` 或 `docs/architecture/` |
| **Reference** | API / schema / runbook / how-to | `docs/reference/` 或 `docs/ops/` |
| **Journal** | 关键发现 / 思考 / 洞见 / 决策记录（share-grade） | `docs/journal/` 或 `journal/` |
| **Scratch** | 在途思考 / drafts / 一次性演算（任务范围，临时） | `scratch/` 或 `drafts/`（命名醒目，entry doc 不索引） |
| **Archive** | 被取代的旧 doc（按 type 分） | `<parent>/_archive/` + `_archive/README.md` 索引表 |

**Scratch 的硬约束**：每份 scratch doc 写入时就要有明确**退出路径** —— 要么 graduate 到 Journal / Design / Reference 对应位置，要么 `rm`。不允许长期滞留。

## 4 Triggers (when skill fires)

1. **新 doc 要写** — 任何 `.md` 新建前
2. **现有 doc 要改** — 改动前先看有没有第二份 doc 讲同一件事
3. **实现 ship / 任务关闭** — 某个 proposal / design 对应的东西已 landed；或一个 scratch doc 对应的任务已结束
4. **健康扫描** — 周期性或按需，查 findability / consistency / freshness / scope / scratch 清零

## Procedures

### P1: Consolidate（两份 doc 合并 / 新 doc 被已有 doc 吸收）

1. 确定 target doc 和合入 section
2. 把 source 内容 embed 进 target，renumber section（如有冲突）
3. `git rm` source
4. `grep -rl "<source-path>" .` 更新所有仍指向 source 的引用
5. Commit `"Consolidate <source> into <target>.md §<section>"`

### P2: Archive（outcome landed / doc 被取代）

1. 目的地 = source 所在 type 的 `_archive/`（Design 的旧版进 `docs/architecture/_archive/`，Journal 的归档进 `docs/journal/_archive/`，以此类推）
2. `git mv <source> <archive-dir>/`
3. 在 `<archive-dir>/README.md`（索引表）加一行：`file | origin-path | date | reason-or-replacement`
4. `grep -rl "<old-path>" .` 更新引用
5. Commit `"Archive <file> (<reason: outcome landed / superseded by X>)"`

### P3: Scratch graduate or delete（任务关闭 / PR merge 时）

1. 列出 `scratch/` 下所有文件
2. 每份 scratch doc 二选一：
   - **Graduate**：内容已沉淀到值得长期保存 → `git mv` 到对应 type 目录（Journal / Design / Reference），按目标 type 的命名与结构整理
   - **Delete**：任务结束、内容已 outdated 或已被代码 / 其他 doc 吸收 → `git rm`
3. **不允许第三种结果**（"再放放看"= 违反 Principle 4）
4. Commit `"Scratch cleanup at <task/pr>: graduate <X>, drop <Y>"`

## Health Scan Checklist (Trigger 4)

按顺序跑，每条有明确 detector：

1. **Findability** — 陌生人从 `README.md` 出发能否 5 分钟定位任意 doc？
2. **Duplicates** — 多份 doc 讲同一主题？（信号：文件名有 v1/v2/new/draft/reframed 后缀，或同名文件在两处）
3. **Orphan refs** — `grep` 仓库里还有没有指向已移动 / 已删除 doc 的链接
4. **Empty dirs** — `find . -type d -empty -not -path "./.git/*"`
5. **Stale `_archive/` 索引** — 索引表每行对应的文件都要存在
6. **Unshipped proposals in active dirs** — Journal / Design 里的 proposal 是否已实现但还在活跃目录
7. **Entry-index drift** — 仓库根的 README / AGENTS / CLAUDE 里的 "Docs structure" 段是否反映当前目录
8. **Scratch backlog** — `scratch/` 下任何文件都要有对应的 open task / open PR；找不到关联的就跑 P3

## Pitfalls

1. **Archive ≠ delete** — 内容进 git history + `_archive/` 索引，随时可回查；不要 `rm`（除非是明确的临时 scratch）。
2. **Skill 不替代判断** — "是否 outcome 已 landed" / "是否重复主题" 这类判断仍需具体 context。Skill 给触发条件 + 机械步骤，不给决策。
3. **移动后必须 grep 引用** — 漏掉引用 = 制造孤儿 = 违反 Findability 原则。
4. **别过度细分目录** — 3 份 similar doc 不够开子目录；真的到 5+ 份 + 子主题稳定时再分层。
5. **别把项目特殊性当通用规则** — Skill 升级时，每条新增规则问："这在 >=3 个不同项目都成立吗？"不成立就不进 skill。

## Verification（任何操作后跑）

1. `git status` 干净
2. `grep -rl "<old-path>" .` 无结果（移动 / 删除后）
3. `find . -type d -empty -not -path "./.git/*"` 无结果
4. `<archive-dir>/README.md` 每行对应真实文件
5. 仓库根 entry doc 的 "Docs structure" 反映当前状态

## Anti-patterns（收录实际纠正过的）

- **双份 doc**：同一事实出现在两处，权威模糊
- **Ephemeral notes 堆积**：`notes/` 里留着 outcome 已 landed 的 proposal
- **新建 doc 不先 grep**：忽略已有 doc，制造 duplicate
- **移动后不 grep**：留下孤儿引用
- **空目录遗留**：`git mv` 最后一个文件后忘 `rmdir`
- **Scratch 没退出路径**：写时没说 graduate-or-delete 的判断条件，最后变成"半永久中等质量 doc"
- **Scratch 藏在普通目录**：起名 `notes/` `tmp/` `wip/` 又混在活跃 doc 里 —— 必须命名醒目（`scratch/` / `drafts/`）且 entry doc 不索引
