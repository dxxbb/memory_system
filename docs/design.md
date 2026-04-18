# Forge Design

更新日期：`2026-04-17`

本文档是 forge 项目的**单一设计文档**，合并自：

- `docs/architecture/personal-os-design.md`（`2026-04-13`，整体运转机制）
- `docs/implementation/mvp-week1.md`（`2026-04-13`，Week 1 交付物与验收）
- 以及一节新写的 §13「Obsidian 作为前端」

原始文档已归档至 `docs/architecture/_archive/`。元原则（可解释性）见 `dxy_OS` vault 的 `workspace/project/forge/onepage.md`。

> **说明**：§14 (MVP Week 1 落地) 保留了 `2026-04-13` 当时的交付清单原文，其中 §14.3.8 的 `assist/sp/master.md` 结构示例是旧版（三段中文骨架），当前实际结构已切换为四段英文骨架——三段 vs 四段的设计本身尚在讨论中，故此节不改，留待后续 PR 单独讨论。

---

## 0. TL;DR

**一句话**：把个人 OS 做成一个 build system，所有变更都是 git diff，所有处理都走 PR，所有 view 都是预编译产物，所有判断由 agent + guideline 做，所有管线由代码做。

**核心组件**：

- 真相源：人或 agent 手写的 `kind: source` 文件
- 产出：由依赖图自动重建的 `kind: derived` 文件
- 触发：watcher 扫 main 的 git diff，按 frontmatter 分类
- 调度：agent（Claude Code）定期 monitor OS（默认每天 1 次），运行 watch.py 扫描变更，读 inbox + guideline 直接处理
- 判断：agent 产 PR，commit 到 `pr/*` branch
- Review：人 `git diff` 看 PR，三种出口(approve / reject / request-changes)
- 落盘：`approve.py` squash merge + 写 change log（rebuild 已在 PR branch 由 agent 完成）

## 1. 为什么是 build system 而不是 storage system

之前几版方案(reference-architecture、solution-design v1/v2)都是在设计"把什么东西存到哪里"。这是 storage 视角。

这一版的转折是：**存储结构不是最关键的问题，运转机制才是**。

原因：

1. 个人 OS 的价值不在"沉淀了多少东西"，而在"每一条沉淀物都能被准确送到 AI 端被用起来"。后者是一条**传播链**，不是一个**仓库**。
2. 传播链上的每一步(identity → section detail → SP → view)都是**上游变化时下游必须跟着变**的关系，这正好是 build system 的语义。
3. 个人 OS 的事件空间是无限的(新对话、新 memo、新 clipping、新 PR 评论……)，事件驱动的 build system 比周期性全量扫描的 storage system 更能处理这种高频 + 不均匀的事件流。

**类比**：这个系统和 Make/Bazel 的关系，等于 Karpathy wiki 和他那份 `CLAUDE.md` 的关系 —— 前者是形式，后者是灵魂。我们只是把形式从"wiki 编译器"扩展到"整个个人 OS 编译器"。

## 2. 运转模型

```
┌────────────┐      ┌───────┐     ┌────────────┐     ┌──────┐     ┌─────────┐     ┌──────────┐
│ source     │──┬──▶│watcher│────▶│monitor inbox│──▶│dispatcher│──▶│agent+rule│──▶│ pr branch│
│ 变更       │  │   └───────┘     └────────────┘     └──────┘     └─────────┘     └──────────┘
│ (git diff) │  │                                                                        │
└────────────┘  │                                                                        ▼
                │                                                                   ┌────────┐
                │                                                                   │ human  │
                │                                                                   │ review │
                │                                                                   └───┬────┘
                │                                                                       │
                │                                        ┌──────────────────────────────┤
                │                                        │approve / reject / request-changes
                │                                        │
                │                                        ▼
                │                                   ┌──────────┐
                └───────────────────────────────────│approve.py│
                                                    └──────────┘
                                                         │
                                                         ▼
                                                   ┌──────────┐
                                                   │squash→main│
                                                   └──────────┘

注：rebuild downstream（section detail → sp → view）已在 PR branch 上
    由 agent 完成，PR diff 已包含完整下游改动。approve.py 只做 squash merge。
```

> **注意**：上图中的 `dispatcher` 组件已取消。当前模型中 agent（Claude Code）定期 monitor OS（默认每天 1 次），直接承担扫描、调度、处理三个角色，使用 `watch.py` 等脚本作为工具。

**数据流**：

1. 人或 agent 写一个 `kind: source` 文件并 commit 到 main
2. Agent（Claude Code）定期 monitor OS（默认每天 1 次），运行 `watch.py` 扫 `git log main`，按 frontmatter 给每个 diff 分类，在 `system/monitor inbox/` 产 TODO
3. Agent 读 inbox 里最早的 `status: todo` 项，加载 `global.md + events/<event_type>.md` 作为处理规则
4. Agent 按 guideline 处理：在 `pr/<id>-...` branch 上按依赖传播链依次调用 section-rebuild → sp-rebuild → view-rebuild，commit 跨三层的完整改动
5. Agent 更新 inbox 状态（done / skipped / unsure / waiting_rereview），在 change log 写一行
6. 人看 inbox 里的 "ready for review"，`git diff main...pr/<id>`（一个 diff 里能看到 source → section → sp → view 的完整影响）
7. 人三选一：approve / reject / request-changes
8. approve 的话，`approve.py` 做纯 squash merge 进 main，删 branch，写 change log。**不再跑 rebuild**——rebuild 已经在 PR diff 里了

## 3. 文件层面的约定

### 3.1 Frontmatter `kind:`

每个被系统管理的 markdown 文件必须能被分类为 source 或 derived。分类靠 frontmatter：

```yaml
---
kind: source
---
```

或：

```yaml
---
kind: derived
upstream:
  - user/about me/me.md
  - user/about me/philosophy.md
generated_by: pr-0042
last_rebuild_at: 2026-04-13T10:23:00
---
```

### 3.2 无 frontmatter 时的默认

**没有 `kind:` 字段 → 视为 `source`**。

理由：

- 原材料层(手工保存的对话 transcript、clipper 抓的网页、daily memo 里的随手笔记)是最常见的情况，要求它们都写 frontmatter 会劝退 capture
- derived 文件 100% 由代码产出，代码写 frontmatter 的成本是零
- **沉默失败比明显失败可怕** —— 如果默认视为 derived，漏处理的 source 会静悄悄被系统忽略，人根本发现不了

watcher 每次把无 frontmatter 的文件视为 source 时，要在 log 里记 `defaulted to source: <path>`。这是未来排查"某类文件反复触发事件"的追溯入口。

### 3.3 依赖声明在 derived 文件的 frontmatter 里

依赖图的真相源是分散的(每个 derived 文件自己声明依赖谁)，不是集中的(一份 deps.yaml)。

理由：

- 改文件时顺手改依赖，不会漂移
- 新加下游文件不需要动中心索引
- 每个 derived 文件自带一份"我是从谁来的"的追溯信息，打开文件就能看到
- 想要全局视图时，代码扫一次所有 frontmatter 即可生成(零成本)

反向查询("改这个 source 会影响谁")由 `scripts/deps.py` 执行：扫全库 frontmatter，构建反向依赖图，秒级返回。

## 4. Agent 写入权限

### 4.1 `system/**` 是受控写入区

`system/**` 不属于普通 source event 流，而属于 **control plane**。

这意味着两条硬规则：

1. `system/**` 默认不被 watcher 当作事件源
2. `system/**` 只能由固定脚本和 `system agent` 写

固定写入入口只有这些：

- `watch.py` 写 `system/monitor inbox/`（由 agent 调用）
- Agent 在处理 inbox 项后直接更新其状态
- `approve.py` / `reject.py` / `request-changes.py` 写 `system/change log/`、`system/PR review/`
- `request-changes.py` 在需要时入队 `pr_revision`

普通 agent、普通工作流、人工日常内容都不应该直接改 `system/**`。

### 4.2 可直写（无需 review）

这些目录是"人还没消化过的原材料"或"系统自己的工作队列"，agent 可以直接写文件并 commit 到 main：

- `conversation memory/` —— 对话原始回流
- `knowledge base/src/` —— 外部原材料捕获(clipper、book 摘录等)
- `assist/preference/improve/learning inbox/` —— 待审的偏好观察

这里要注意：

- `system/monitor inbox/` 和 `system/change log/` 虽然也写在 main 上，但它们不属于"普通 agent 可直写"
- 它们只属于 `system-owned`

### 4.3 必须走 PR

其他一切都必须经过 PR。关键列表：

- `user/` —— 身份真相源，agent 不能改
- `knowledge base/` —— 长期知识
- `assist/section detail/`、`assist/sp/`、`assist/view/` —— 依赖传播链的中转和终点
- `assist/preference/current/` —— 生效中的偏好(`learning inbox` 是 agent 可写的，`current` 不可)
- `workspace/` —— 灰色地带但取严格态度：**workspace 也要 review**
- `system/operating rule/` —— agent 不能自己改游戏规则
- `config store/` —— 秘钥和配置，agent 碰都不该碰

### 4.4 设计原则

**凡是下游有依赖传播或对 AI 行为有直接影响的文件，必须走 PR；凡是纯粹的 inbox / scratch / log 性质的文件，agent 可以直接写。**

这条原则不允许例外。workspace 看起来像 scratch，但它是你的活跃工作区，agent 悄悄修改会污染你的判断 —— 所以归到 PR 侧。

再补一条更硬的规则：

**凡是 `system/**` 下的控制面文件，必须走固定脚本入口，不能靠普通 agent 自由写。**

## 5. PR 工作流

### 5.1 PR 不是 CR

CR(change request)只有两种出口(通过/不通过)，PR 有三种：approve / reject / request-changes。personal OS 的 review 需要第三种，因为很多情况下 agent 的提案方向对但细节不对，这时需要"按我的 comment 再改一版"，而不是"整个拒掉重来"。

### 5.2 PR 的物理形态

一个 PR = 一个 git branch + 若干 commit。branch 命名：`pr/<自增编号>-<短描述>`，例如 `pr/0001-add-assumption-check`。

**不维护任何自定义的 CR 文件格式**。review 看的是 `git diff main...pr/0001`，review 工具是 `git diff` / `gh pr view` / VS Code source control / Obsidian Git 插件，任选。

### 5.3 Commit message 约定

每个 PR 的第一个 commit 的 message 包含三部分：

1. **标题**：一句话说清楚改什么
2. **正文**：root cause、why、how
3. **Trailers**：机器可读的元数据

示例：

```
Add "clarify assumptions before answering" rule to master SP

Why: 2026-04-13 的对话里 agent 在两处直接基于猜测的上下文回答，
没有先问用户。root cause 是当前 SP 没有"先确认假设"的硬约束，
agent 默认走"直接回答"分支。

How: 在 sp/master.md 的"工作方式"章节新增一条规则。

Trigger: conversation memory/2026-04-13/claude-code.md@a1b2c3d
Category: preference
Affects-downstream: yes
```

Trailers 的约定：

- `Trigger: <path>@<commit>` —— 触发这条 PR 的 source event
- `Category: <event_type>` —— 用于 `git branch --list pr/*` 等 one-liner 对 PR 分组统计
- `Affects-downstream: yes|no` —— 是否影响下游（section detail / sp / view）；为 yes 时 PR 必须在 branch 上已经包含完整下游 rebuild

### 5.4 MVP 约束：一个 PR 只改一个 source 文件

多个 source 改动拆成多个 PR。理由：每条 PR 的 review 焦点窄，决策可控；跨文件的原子性改动在 MVP 阶段遇不到。

`approve.py` 开头有一条断言强制执行这条约束，实现大致是 `git diff main...HEAD` 后检查有 `kind: source` 的文件数量不超过 1。

### 5.5 三种 review 出口对应三个脚本

- `scripts/approve.py pr/0001` —— 纯 squash merge：读 PR 首个 commit message 作 squash 标题、带 `Approved-by:` trailer 合进 main、删 branch、更新 change log、把对应 inbox TODO 标 done。**不再跑 rebuild**，rebuild 已由 agent 在 PR branch 上完成
- `scripts/reject.py pr/0001 --reason "..."` —— `git branch -D`、reason 写进 change log
- `scripts/request-changes.py pr/0001` —— 起编辑器让人写 comment，把 comment commit 到 branch 上的 `system/PR review/pr-0001-comments-round<N>.md`，然后**直接入队**一条 `event_type: pr_revision` 的 TODO

### 5.6 Comment 往返机制

**载体**：comment 文件 commit 在 PR 的 branch 上，路径为 `system/PR review/pr-<id>-comments-round<N>.md`。

**为什么 commit 在 branch 上而不是 branch 外**：comment 是 PR 历史的一部分，应该和 PR 的 commits 一起存活、死亡。reject → branch 删 → comment 也一起消失。approve → squash merge → comment 不进 main。生命周期由 git branch 本身管理，零手工清理。

**轮次**：**每轮 comment 新建一个文件**，不 append。追溯清晰，`round1` / `round2` / `round3` 的命名一眼看出时序。

**agent 的 counter-argument**：允许。agent 读 comment 后，如果认为 comment 不合理或和原意冲突，可以在 branch 上新建 `system/PR review/pr-<id>-response-round<N>.md` 说明 counter-argument，然后把 inbox ball 踢回人。

**Round 上限**：没有硬上限。guideline 要求 agent 在 `round >= 3` 时主动喊停，在 response 里明确说"我认为我们在原地打转，建议 reject 或明确改写成 ..."，强迫 agent 在多轮无果时停。

**request-changes 路径**：

1. 人跑 `request-changes.py pr/0001`，写 comment
2. 脚本 commit comment 文件到 branch，然后直接在 `system/monitor inbox/` 入队一条 `event_type: pr_revision` 的 TODO，frontmatter 带 `pr_branch: pr/0001`、`comment_file: system/PR review/pr-0001-comments-round1.md`、`round: 1`
3. Agent 下次 monitor 时，取到这条 TODO，加载 `events/pr_revision.md` 作为处理规则
4. Agent checkout 到 `pr/0001` branch，读 comment、读原始 commit message、按 comment 修改或产 response
5. Agent 处理完成后更新 inbox 状态

### 5.7 Squash merge

approve 时 PR 的所有 commit（agent 产出的跨层 rebuild + comment 文件 + response 文件）**被 squash 合成一个 commit 进 main**。主库保留：干净的 source 改动 + rebuilt derived，不保留 comment 文件、response 文件等 review 过程产物。

PR 的完整历史(multi-round 的 comment、agent response、amend)只活在 branch 的 reflog 和 git 历史中，main 上看不到。这是有意的：main 是 canonical state，不是 discussion archive。

## 6. Watcher 规则

### 6.1 只扫 main

watcher 只看 `git log main`，pr/* 分支上的 agent 工作对 watcher 不可见。

理由：

1. **避免无限循环**。agent 在 branch 上反复 commit，watcher 如果看 branch 会被无限触发
2. **只看已稳定的状态**。main 是 canonical state，branch 是 WIP。监控应该监控 canonical
3. **语义和 git 对齐**。branch = proposal，main = truth，watcher 只关心 truth 层的变化

### 6.2 从 last_seen_commit 扫到 HEAD

watcher 在 `system/.watcher-state`(或 `.watcher-state.json`)里维护一个 `last_seen_commit` 字段。每次启动时从那个 commit 扫到 `HEAD`，处理完所有新 commit 后把 state 更新为新的 `HEAD`。

这个 state 文件不进 git，`.gitignore` 排除。

### 6.3 跳过系统自产生的 commit

watcher 对每个新 commit 检查 commit message 的 trailer：

- 有 `Approved-by: approve.py pr/<id>` —— 跳过
- 有 `System-owned-by: watch.py` —— 跳过
- 有 `System-owned-by: agent-monitor` —— 跳过
- 有 `System-owned-by: request-changes.py` —— 跳过
- 否则 —— 按正常规则处理

`approve.py` 在产 squash merge commit 时必须带 `Approved-by:` trailer。

其他系统脚本写到 main 的 commit，也必须带 `System-owned-by:` trailer。

### 6.4 事件分类

watcher 对不跳过的 commit，遍历 diff 里涉及的每个文件：

1. 如果路径在 `system/**` —— 直接跳过
2. 打开文件读 frontmatter，获取 `kind:`
3. 如果 `kind: derived` —— 跳过(derived 改动是下游，不触发新事件)
4. 如果 `kind: system` —— 跳过
5. 如果 `kind: source` 或无 frontmatter —— 继续分类
6. 按路径前缀决定 `event_type`：

   | 路径前缀 | event_type |
   |---|---|
   | `conversation memory/**` | `conversation` |
   | `user/daily memo/**` | `daily_memo` |
   | `user/**` (其他) | `identity_change` |
   | `workspace/project/**` | `project_update` |
   | `workspace/topic/**` | `topic_update` |
   | `workspace/reading/**` | `reading_update` |
   | `workspace/writing/**` | `writing_update` |
   | `knowledge base/src/**` | `ingest` |
   | 其他 | `unclassified` |

7. 在 `system/monitor inbox/` 写一个 TODO 文件

MVP 阶段 guideline 只覆盖 `conversation` 和 `pr_revision` 两类，其他类别的 TODO 由 agent 按 guideline 判定为 `unclassified`，直接记一条 log 然后 skip。

这里的 `pr_revision` 不是 watcher 扫出来的，而是 `request-changes.py` 直接入队的。

## 7. PR 队列的组织

PR 本身就是 git branch，不需要单独的元数据目录。`system/PR review/` 是 review round-trip 的载体：comment 和 response 文件按 `pr-<id>-comments-round<N>.md` / `pr-<id>-response-round<N>.md` 落盘在各自 PR 的 branch 上，approve 时随 squash 消失。

列 active PR 的需求可以靠 `git branch --list 'pr/*'` + 读每个 branch 的 first commit message（有 Trigger / Category trailer）实时算，不做缓存。MVP 阶段不写 `ls-prs.py`，命令行 one-liner 够用。

## 8. Guideline 的结构

### 8.1 目录布局

```
system/operating rule/
├── global.md                    # 跨事件的硬约束 + agent 身份
└── events/
    ├── conversation.md          # MVP 唯一的事件处理规则
    ├── pr_revision.md           # (MVP 第二份，处理 comment 回合)
    ├── daily_memo.md            # Phase 2
    ├── identity_change.md       # Phase 2
    ├── project_update.md        # Phase 2
    └── ...
```

### 8.2 agent 的 guideline 载入

```python
def load_guideline(event_type: str) -> str:
    return read("global.md") + "\n\n" + read(f"events/{event_type}.md")
```

Agent 在处理每个 inbox 项时，直接读取 `global.md + events/<event_type>.md` 作为处理规则，加上 inbox TODO 的内容作为当前任务。载入过程发生在 agent session 内部，不需要外部脚本拼接。

### 8.3 global.md 的内容范围

- 这个系统是什么、为什么存在(简短)
- 不可违反的硬约束：source 必须走 PR、frontmatter 必须完整、依赖用 `deps.py` 算、每个 PR 一个 source 文件
- agent 的身份：你是 OS 的 operating agent，你的判断质量决定系统质量
- 出错时的 fallback：不确定就停下来产 `unsure` 类型的 PR 描述困惑

### 8.4 events/*.md 的内容范围

每份 event 文件包含：

- 触发条件(哪些路径会产生这类事件)
- 处理流程(按步骤)
- 评估维度(agent 判断时考虑什么)
- 允许改的文件清单
- 不允许改的文件清单
- 成功和失败的结束标记怎么写
- Commit message 模板

### 8.5 为什么不用 YAML schema

因为 guideline 的灵魂是"灵活的 convention，由 agent 自由判断"，不是"硬编码的规则，由代码强制执行"。用 YAML 会把它变成半程序半规范的混合物，失去 agent 做判断的空间。

agent 可能偶尔越界，这是成本。修复方法是改 guideline 或在 Claude Code 的 permission 机制里加限制，不是把 guideline 本身变成程序。

## 9. 外层代码 vs 内层 agent

这个系统的实现边界是一条明确的横线：

| 属于代码 | 属于 agent + guideline |
|---|---|
| watcher 扫 git diff | 评估对话是否达成目的 |
| 路由 inbox 分类 | 决定是否需要改 SP |
| 读/写 frontmatter | 决定改 section detail / sp / view 的哪里、怎么改 |
| `deps.py` 算依赖图 | 执行跨层 rebuild（section → sp → view）并 commit 到 PR branch |
| `approve.py` squash merge | 写 PR 的 commit message |
| 写 change log | 读 comment、决定怎么回应 |
| 更新 `.watcher-state` | 产出 counter-argument 或修订 |

**原则**：凡是不依赖模型判断的，都用代码实现。凡是需要模型判断的，都交给 agent + guideline。这条边界如果守不住，要么系统过度依赖 LLM 导致成本高不可靠，要么过度用代码导致失去 agent 的灵活性优势。

## 10. 被显式推迟的问题

以下问题在今天的讨论中被提出但**明确推迟到 Phase 2+**，不影响 MVP 运转：

- **Fact staleness / 冲突失效机制**。MVP 阶段靠 git history 兜底，写错了 `git revert`。Phase 2 加 `invalid_at` 或 tombstone 约定
- **并发 PR 冲突**。MVP 量低，遇到再说
- **Lifecycle 和归档**。`workspace/` 不在 MVP 里，等 Phase 2 再设计 "project done → 提炼进 knowledge base" 的规则
- **非 conversation 的 ingest 源处理规则**。daily memo、clipper、book 等都是 Phase 2 加 event 类型
- **Preference 完整闭环**。MVP 里"改 SP" 已覆盖最小偏好改进，不做独立的 preference 闭环
- **组合式 SP (master + role overlay)**。MVP 只有一个 view 一个 SP，master 和 role 是同一个东西。开第二个 view 时再拆
- **自动化 watcher**。MVP `watch.py` 手动跑，cron/launchd/git hook 是 Phase 2
- **跨 PR 的 conflict resolution**。两个 pending PR 改同一个下游文件时，approve 第二个需要自动 rebase 或 abort；MVP 里一次只跑一个 PR，不会遇到

## 11. 被忽略但值得记住的风险

即使今天的设计处理了大部分风险，仍有几条没被完全堵住：

### 11.1 guideline 膨胀

当事件类型增多时，`global.md + events/*.md` 的总字数会膨胀。单个 event 文件不会太长(per-event 隔离)，但 `global.md` 容易成为"所有 event 的共同知识仓库"，慢慢变长。

**监控**：每月检查 `global.md` 行数，超过 300 行时强制重构。

### 11.2 agent 误判产生的污染

agent 在 `events/conversation.md` 的规则下产 PR，如果 agent 误判一次对话的目的(例如把用户的玩笑话当真要求)，会产生错误的 PR。人 review 时可能漏审，最终污染 SP。

**缓解**：`request-changes.py` 的 round 机制就是用来处理这种情况的。多轮 comment 让你有机会把 agent 拉回正道。同时 change log 保留所有 merged PR，`git revert` 随时可用。

### 11.3 watcher state 丢失

`system/.watcher-state` 不在 git 里，如果机器换了或文件被删了，watcher 不知道从哪里扫起。

**缓解**：watcher 在 state 丢失时的 fallback 是"扫最近 N 个 commit"(N = 50 或配置项)，并在 log 里 warn。完全重建 inbox 是不现实的。

### 11.4 PR branch 的陈旧

某些 PR 开了之后人忘了 review，branch 留在 repo 里几周甚至几个月。git log 会越来越乱。

**缓解**：`ls-prs.py` 按 branch age 排序列出 active PR，超过 N 天的加 `[stale]` 标记提醒人处理。

### 11.5 依赖图的环

`deps.py` 必须检测 frontmatter `upstream:` 构成的有向图是否有环。理论上 derived → derived → derived 是合法的(一层传播)，但循环依赖会让 rebuild 死循环。

**缓解**：`deps.py` 用 DFS 检测环，发现环直接报错。Agent 在执行 rebuild 前应先跑 `deps.py --check-cycles`，报错则把 inbox TODO 标 `unsure` 交给人。

## 12. 和其他方案的横向对比

| 维度 | Karpathy wiki | Mem0/Zep | Letta MemFS | memory_system v2 | Personal OS (本文) |
|---|---|---|---|---|---|
| 核心定位 | 知识编译器 | 对话记忆服务 | agent 运行时 | 本地 memory core | 个人 OS build system |
| 真相源形态 | 目录 + 文件 | 数据库 | file-system | 文件 | 文件 + git |
| 检索 | index.md + LLM | vector/graph | file read | token overlap | **预编译 view** |
| 触发机制 | 人工指令 | 对话 hook | LLM 工具 | 手工 | **git diff + watcher** |
| 判断层 | LLM | 内置 extract | agent | 手工 | **agent + guideline** |
| Review gate | 无 | 无 | 无 | Workspace | **PR workflow** |
| 下游传播 | 无(wiki lint) | 自动 | 无 | 手工 | **依赖图 + rebuild** |
| 失效机制 | 无 | Mem0g 自动 | 无 | invalid_at | **git revert** |
| 事件回路 | 无 | 无 | 无 | 无 | **comment round** |
| 范围 | 知识 | 记忆 | agent 状态 | memory 子系统 | **个人 OS 全部** |
| 落地门槛 | 低 | 零(SDK) | 中 | 中 | **中(需要代码)** |

**personal OS 相对别人的独特点**：

1. **把 build system 完整应用到个人知识管理**。没有别的方案把 Make/Bazel 的依赖图 + 重建机制 + 变更 review 这一整套拿过来
2. **把 git 作为整个系统的底层数据总线**。不是"用 git 保存文件"，而是"git commit 就是事件、git branch 就是 PR、git log 就是 audit、git revert 就是 undo"
3. **身份 / 知识 / 活动三分**，顶层目录就分开(`user/` / `knowledge base/` / `workspace/`)，其他方案都混在一起
4. **Preference 有独立的 learning 闭环**(`learning inbox → PR → history`)，比把 preference 混进 memory 层更干净
5. **外层代码 + 内层 agent 的明确边界**。别人要么全 agent 要么全代码，这是第一个明确把边界画出来的

**personal OS 的劣势也要写清楚**：

1. **实现复杂度明显高于 Karpathy wiki 和 Mem0**。需要写 watcher、dispatcher、deps.py、approve.py，加起来几百行代码
2. **没有真正的自动化** —— 所有 watcher 都是手动跑，不像 Mem0 是 SDK 内嵌自动化
3. **依赖 git 熟练度**。对非程序员不友好
4. **guideline 的质量完全决定系统质量**，而 guideline 的初始版本一定是错的，需要多轮迭代

## 13. Obsidian 作为前端

vault（`dxy_OS/`）是一个独立 git repo，日常由 **Obsidian 作为人机交互前端**。Obsidian 在本系统里的职责边界是严格的：

**Obsidian 负责**：

- 查看 / 编辑 markdown 文件
- 文件间 wiki-link 导航
- review（读 `git diff`、看文件历史）
- 局部搜索、tag 浏览

**Obsidian 不负责**：

- 生成 projection（即 `section detail → sp → view` 的 rebuild 链路）—— 由 agent + scripts 做
- 派生索引 —— 由 `scripts/deps.py` 做
- 平台同步 —— 由 agent 写 `view/` 完成
- 任何自动化判断

换言之，Obsidian 是一个**纯展示 + 纯编辑**的 shell。vault 不使用 Obsidian-specific 的 Bases、Dataview 或 Templater 功能来承担系统职责；这些功能即使启用，也只能作为辅助浏览手段，不能进入 `kind: source / derived / system` 的真相链。

**目录可见性**：vault 顶层目录对 Obsidian 都是可见的（`user/`、`knowledge base/`、`workspace/`、`assist/`、`system/`、`conversation memory/`、`knowledge base/src/`、`config store/` 等）。系统产物目录（`system/**`、`.watcher-state`）通过 Obsidian 的排除设置可以从侧栏隐藏，但仍在 git 管辖内。

**frontmatter 约定**：vault 内所有受管文件的 frontmatter 只依赖三个顶层字段：`kind: source | derived | system`，以及 derived 文件的 `upstream:` 列表。**不使用**过去某个早期方案里讨论过的 `id / family / status / cleanliness / persistence / grounding / project_refs / view_refs / origin_author_*` 等复杂字段——那套设计属于 04-13 之前的 KB-first 阶段，已被 build-system 模型取代。

## 14. MVP Week 1 落地

本节对应 `2026-04-13` 当时为"Week 1 跑通端到端闭环"起草的交付清单（原 `docs/implementation/mvp-week1.md`）。内容保留原样，作为项目启动里程碑的历史记录；部分代码路径、SP 骨架已在后续 PR 中演化。

### 14.1 Week 1 的唯一目标

**跑通一条真实对话触发的 PR 流程，从 source 变动到下游 view 被 rebuild，全程不缺环节。**

这个目标不追求功能完整，只追求**链路完整**。跑通之后，其他事件类型、其他目录、自动化机制都是重复同一套模式的扩展，不是新设计。

### 14.2 Scope 裁剪

**MVP 只覆盖**：

- 1 个事件类型：`conversation`
- 1 个 view：`assist/view/claude-code/CLAUDE.md`
- 1 份 SP：`assist/sp/master.md`
- 1 份 section detail：`assist/section detail/me.md`
- 6 个顶层目录：`user/`、`conversation memory/`、`assist/{section detail, sp, view}/`、`system/{monitor inbox, change log, operating rule, PR review}/`

**MVP 显式不做**：

- `workspace/`、`knowledge base/`、`config store/`、`knowledge base/src/`、`daily memo/`
- `assist/preference/`、`assist/tool/`
- 组合式 SP(master + role overlay)
- 除 `conversation` 之外的 event 类型
- 自动化 watcher(cron、launchd、git hook)
- cross-PR conflict resolution
- fact staleness / invalidation 机制

### 14.3 交付物清单

#### 14.3.1 仓库骨架

```
vault/
├── user/
│   └── about me/
│       └── me.md                         # kind: source, 极简身份三五段
├── conversation memory/
│   └── 2026-04-13/
│       └── .gitkeep                      # 空目录占位
├── assist/
│   ├── section detail/
│   │   └── me.md                         # kind: derived, upstream: user/about me/me.md
│   ├── sp/
│   │   └── master.md                     # kind: derived, upstream: section detail/me.md
│   └── view/
│       └── claude-code/
│           └── CLAUDE.md                 # kind: derived, upstream: sp/master.md
└── system/
    ├── monitor inbox/                    # agent 工作队列（终态 TODO 立即删除，不保留）
    ├── change log/                       # append-only 审计
    ├── PR review/                        # comment / response 文件（review round-trip 载体）
    └── operating rule/
        ├── global.md                     # 全局硬约束
        └── events/
            ├── conversation.md           # conversation 事件处理规则
            └── pr_revision.md            # PR 修订事件处理规则
```

`.gitignore`：

```
system/.watcher-state
.DS_Store
```

#### 14.3.2 `scripts/deps.py`

**输入**：一个文件路径
**输出**：
- `--downstream <path>`：列出所有直接或间接依赖该文件的下游文件
- `--upstream <path>`：列出该文件的所有上游
- `--check-cycles`：检测依赖图是否有环

**实现要点**：
- 扫 vault 根目录下所有 `*.md`
- 读每个文件的 frontmatter，解析 `upstream:` 字段
- 构建反向索引 `{upstream_path: [downstream_paths]}`
- `--downstream` 用 DFS 传递闭包
- `--check-cycles` 用 DFS + 三色标记法

预计行数：**80 行**以内。

#### 14.3.3 `scripts/watch.py`

**输入**：无(或 `--dry-run`)
**行为**：
1. 读 `system/.watcher-state` 的 `last_seen_commit`，默认 `HEAD~50`
2. `git log <last_seen_commit>..HEAD --format=...` 取所有新 commit
3. 对每个 commit：
   - 读 commit message，如果 trailer 里有 `Approved-by:`、`Rebuilt-by:` 或 `System-owned-by:`，跳过
   - 取 diff 涉及的文件列表
   - 对每个文件：如果路径在 `system/**`，直接跳过
   - 否则打开读 frontmatter，判断 `kind:`
   - `kind: derived` 或 `kind: system` → 跳过
   - `kind: source` 或无 frontmatter → 按路径前缀分类
4. 为每个未跳过的事件在 `system/monitor inbox/` 产一个 TODO markdown
5. 更新 `last_seen_commit` 到 HEAD

**TODO 文件的 frontmatter**：

```yaml
---
kind: system
id: 0001
status: todo
event_type: conversation
source_path: conversation memory/2026-04-13/claude-code.md
source_commit: a1b2c3d
created_at: 2026-04-13T14:20:00
---
```

正文留空或简短描述(比如第一行 diff summary)。

预计行数：**120 行**以内。

#### 14.3.4 Agent monitor 流程（取代 `scripts/dispatch.py`）

Agent（Claude Code）是 OS 的主调度者，不是被脚本启动的。默认每天 monitor 1 次。

**触发方式**：
- MVP 阶段：人手动对 Claude Code 说 "monitor OS"（或等价指令）
- Phase 2+：通过 cron / launchd 定时触发

**Agent monitor 时的行为**：
1. 运行 `python3 scripts/watch.py` 扫描新 commit，产生 inbox TODO
2. 读 `system/monitor inbox/*.md`，按 `id` 排序取最早的 `status: todo`
3. 把它改成 `status: running`
4. 读 frontmatter 的 `event_type`，加载 `global.md + events/<event_type>.md` 作为处理规则
5. 按 guideline 执行：读触发源、评估、判断、在 `pr/<id>-...` branch 上产 commit（如果需要）
6. 更新 inbox 状态为 `done / skipped / unsure / waiting_rereview`
7. 如果 `event_type` 不在 MVP 范围内(`unclassified`、`daily_memo` 等)，直接标记 `status: skipped`，在 change log 写一行
8. 如果 inbox 里还有 `status: todo` 的项，继续处理下一条

**注意**：`scripts/dispatch.py` 不再作为独立脚本存在。Agent 直接读写 inbox 文件，使用 `watch.py` 和 `deps.py` 作为工具。

#### 14.3.5 `system/operating rule/global.md`

内容大纲：

- 系统简介(1 段)
- agent 身份(你是 personal OS 的 operating agent，职责是根据事件产生高质量的变更提案)
- 全局硬约束：
  - 所有 source 改动必须走 PR，不能直接 commit 到 main
  - 所有 PR 的 commit message 必须带 `Trigger:`、`Category:`、`Affects-downstream:` trailer
  - 每个 PR 只能改一个 source 文件
  - 不许修改 `user/`、`knowledge base/`、`config store/`、`system/operating rule/`、`assist/preference/current/`
  - 不许直接写 derived 文件(`kind: derived`)；derived 由 approve.py 自动 rebuild
  - 不许直接修改 `system/**`；`system/**` 只能通过固定脚本入口改动
- 出错时的 fallback：
  - 如果你不确定怎么处理一个 inbox 项 → 在 change log 写一行 "unsure: <reason>"，把 inbox 项标记为 `unsure` 状态，交给人决定
  - 如果你发现 guideline 本身有问题 → 不要自己改 `operating rule/`，而是在 change log 写一行 "guideline-issue: <desc>"，人会来处理
- 出结束标记的约定：
  - Agent 在处理完 inbox 项后，直接更新其 frontmatter 状态（`done / skipped / unsure / waiting_rereview`）
  - inbox 状态变更的 commit 带 `System-owned-by: agent-monitor` trailer

预计行数：**60 行**以内。

#### 14.3.6 `system/operating rule/events/conversation.md`

内容大纲：

- 触发条件：`conversation memory/**` 下有新 commit
- 处理流程：
  1. 读 `source_path` 指向的 conversation memory 文件(整份对话 transcript)
  2. 评估这次对话：
     - 用户的目的是什么？达成了吗？
     - 有没有明显不符合预期的回答？
     - 如果有问题，root cause 是什么？是 SP 缺少规则，还是 agent 能力问题，还是对话输入本身不清晰？
  3. 决策：
     - 如果 root cause 是 SP 缺少规则 → 走"创建 PR"分支
     - 如果 root cause 是 agent 能力问题(模型限制) → skip，change log 记一行
     - 如果 root cause 是输入不清晰 → skip，change log 记一行
     - 如果对话完全符合预期 → skip，change log 记一行 "nothing to improve"
  4. 创建 PR(如果需要)：
     - `git checkout -b pr/<自增id>-<短描述>`
     - 编辑 `assist/sp/master.md`
     - `git commit` 用下面的 template
     - 回到 main 后，由系统脚本更新 inbox 状态为 `done`，并记录 PR branch
- Commit message template：

  ```
  <短标题>

  Why: <root cause 分析>

  How: <这次改动干了什么>

  Trigger: <source_path>@<source_commit>
  Category: preference
  Affects-downstream: yes
  ```

- 允许改的文件：
  - `assist/sp/master.md`(唯一)
- 禁止改的文件：
  - 所有其他文件
- 评估的 anti-pattern(避免)：
  - 不要因为一次对话就产生大改，保持 SP 改动的最小原则
  - 不要提议规则会和现有 SP 规则冲突；冲突时优先修正现有规则而不是叠加新规则
  - 不要把对话中的一次性意见当成偏好固化；只提炼反复出现或明确表达的模式

预计行数：**80 行**以内。

#### 14.3.7 `system/operating rule/events/pr_revision.md`

内容大纲：

- 触发条件：inbox 里出现 `event_type: pr_revision`
- 处理流程：
  1. 读 inbox 项的 `pr_branch` 和 `comment_file`
  2. `git checkout <pr_branch>`
  3. 读 `comment_file`(最新一轮)
  4. 读该 branch 上原始 PR 的 commit message(得到原始意图)
  5. 判断 comment 是否合理：
     - 合理且能满足 → 修改相关文件，`git commit` 一条 "Addresses: <comment_file>" 的新 commit
     - 不合理或和原意冲突 → 在 branch 上新建 `system/PR review/pr-<id>-response-round<N>.md` 写 counter-argument，commit
  6. 回到 main 后，由系统脚本入队新 TODO `event_type: pr_ready_for_rereview`，frontmatter 带 `pr_branch`、`round`(递增)
- Round 上限约束：
  - 如果 `round >= 3`，response 文件里必须明确写 "我认为我们在原地打转，建议 reject 或明确改写成 ..."
- 允许改的文件：
  - 当前 pr branch 上的目标 source 文件
  - `system/PR review/pr-<id>-*.md`
- 禁止改的文件：
  - 所有其他文件

预计行数：**60 行**以内。

#### 14.3.8 `assist/sp/master.md` 初版

> **说明**：此处示例的三段中文骨架（身份 / 工作方式 / 边界）是 `2026-04-13` 当时的设计；后续 PR 中已改为四段英文骨架（Identity / Context / Working Style / Boundaries）。三段 vs 四段的取舍本身尚在讨论中，本节保持原文以忠实记录启动时的决策。

frontmatter：

```yaml
---
kind: derived
upstream:
  - assist/section detail/me.md
generated_by: manual-init
last_rebuild_at: 2026-04-13T00:00:00
---
```

正文结构：

```markdown
# Master System Prompt

## 身份
(从 section detail/me.md 投影的身份段落)

## 工作方式
(空，等第一条 PR 来填)

## 边界
- 不要伪造引用或数据
- 不确定的事先说不确定
```

说明：MVP 第一次闭环之前，这份文件和 `section detail/` 的各 fragment 手工初始化为空占位即可。第一次真正的 conversation PR 由 agent 在 branch 上填充实际内容。

#### 14.3.9 `scripts/approve.py`

**重要**：approve.py 是**纯 squash merge 工具**，不跑 rebuild。Rebuild 由 agent 在 PR branch 上按 `section-rebuild.md` / `sp-rebuild.md` / `view-rebuild.md` 的步骤完成，PR diff 已经包含从 section detail 到 view 的完整改动。

**输入**：`pr/<branch-name>`
**行为**：
1. 断言当前 base 分支（master 或 main，自动检测）是 clean
2. 断言 pr branch 存在且有 commits ahead of base
3. 读 PR 第一个 commit 的 title/body（agent 写的带 Trigger/Category/Affects-downstream trailer 的 message）
4. `git merge --squash <branch>`
5. `git commit -m "<title>\n\n<body>\n\nApproved-by: approve.py pr/<id>"`
6. `git branch -D <branch>`
7. 在 `system/change log/<YYYY-MM>.md` append 一行
8. 把对应 inbox TODO 的 `status` 改为 `done`、加 `pr_branch` 和 `merged_at` 字段
9. Commit 上述 system 改动，带 `System-owned-by: approve.py pr/<id>` trailer

预计行数：**~230 行**（含 yaml 解析、错误提示、auto-detect 默认分支）。

#### 14.3.10 `scripts/reject.py`

**输入**：`pr/<branch-name>` + `--reason "..."`
**行为**：
1. `git branch -D <branch>`
2. 在 change log 追加 "rejected: pr/<id> - <reason>"
3. 把相应的 inbox 项标记为 `rejected`

预计行数：**30 行**以内。

#### 14.3.11 `scripts/request-changes.py`

**输入**：`pr/<branch-name>`
**行为**：
1. 起编辑器(`$EDITOR` 或 `vim`)让人写 comment
2. 把 comment 保存到 `system/PR review/pr-<id>-comments-round<N>.md`，N 从现有文件推断
3. `git checkout <branch>`，`git add` comment 文件，`git commit -m "Review comments for pr/<id> (round <N>)"`
4. `git checkout main`
5. 在 `system/monitor inbox/` 产一个新 TODO，`event_type: pr_revision`，frontmatter 带 `pr_branch`、`comment_file`、`round`

预计行数：**60 行**以内。

### 14.4 验收闭环

**这一条闭环跑通 = MVP 成立**。

#### 步骤

1. **(人工)** 和 Claude Code 做一段真实对话，对话里故意让 agent 犯一个小错(比如不先确认假设就直接回答)
2. **(人工)** 把 transcript 保存成 `conversation memory/2026-04-13/claude-code.md`，`git add && git commit -m "Save conversation 2026-04-13"`
3. **(人工)** 运行 `python3 scripts/watch.py`
   - 预期：`system/monitor inbox/0001-conversation.md` 出现，`event_type: conversation`，指向刚才的 transcript 文件
4. **(人工)** 对 Claude Code 说 "monitor OS"（或等价指令）
   - 预期：Agent 运行 `watch.py`（如果步骤 3 未手动运行），扫到新 commit，inbox 里出现 TODO
   - 预期：Agent 读 `global.md + events/conversation.md + inbox item`，读对话 transcript
   - 预期：Agent 识别出 "没有先确认假设" 这个 pattern，判断这是 SP 层的问题
   - 预期：Agent `git checkout -b pr/0001-add-assumption-check`，编辑 `sp/master.md`，commit
   - 预期：Agent 回到 main，更新 inbox 项为 done，在正文注明 `pr/0001-add-assumption-check`
5. **(人工)** `git diff main...pr/0001-add-assumption-check` 查看改动
6. **(人工)** 运行 `python3 scripts/approve.py pr/0001-add-assumption-check`
   - 预期：PR 已包含 section detail / sp / view 跨层改动（agent 在 step 4 完成）
   - 预期：`approve.py` 做纯 squash merge，commit message 带 `Approved-by:`
   - 预期：branch 被删
   - 预期：change log 追加一行
   - 预期：对应 inbox TODO 被标 `done`
7. **(人工)** 打开新 Claude Code session
   - 预期：session 读到的 `CLAUDE.md` 是新版，包含"先确认假设"的规则
   - 预期：在类似情境下，agent 的行为已经改变

#### 验收红线(必须全部满足)

- [ ] 一次对话 → 一条 inbox TODO → 一个 PR → 一次 approve → 一次 merge → 一个新版 view
- [ ] 整条链路没有任何一步卡住
- [ ] 没有任何一个文件需要手工编辑才能让流程继续(除了第一步的 transcript 保存)
- [ ] 再跑一次 `watch.py` 不会把 approve 产生的 merge commit 当成新事件(trailer 机制生效)
- [ ] 再对 Claude Code 说 "monitor OS" 时，inbox 里没有残留 `todo` 状态的项

#### 允许 MVP 失败但要记录的情况

- agent 误判对话的 root cause，产出无意义的 PR → **接受**，你 reject 它，这说明 guideline 需要改进，而不是系统不 work
- agent 在 PR branch 上生成的 `CLAUDE.md` 格式不好看 → **接受**，MVP 不追求 rebuild 模板完美
- commit message trailer 格式和预期有偏差 → **不接受**，trailer 是 watcher 的依据，必须严格

### 14.5 时间预算

- 仓库骨架：30 分钟
- `global.md` + 两个 events 文件：1-2 小时
- `deps.py` + `watch.py`：3-4 小时
- `approve.py`：半天
- `reject.py` + `request-changes.py`：1-2 小时
- 第一次端到端跑通 + 调试：1 小时到半天(看第一次跑遇到什么)
- **合计**：一个周末应该能完成。超过一周还没跑起来 = scope 太大，需要继续砍。

### 14.6 第一次跑通之后

跑通之后，**预计 guideline 的 70% 内容需要重写**。这很正常，guideline 是"用出来的"不是"想出来的"。第一次跑通的价值是**验证链路完整**，不是**验证 guideline 完美**。

接下来的 Phase 2 优先顺序建议：

1. 加第二个 event 类型(`daily_memo` 或 `ingest`)——复制 conversation.md 的模板即可
2. 加 `workspace/` 相关的 event 处理
3. 加自动化 watcher(launchd 或 cron)
4. 加组合式 SP(master + role overlay)
5. 加 preference 完整闭环
6. 加 fact staleness 机制
