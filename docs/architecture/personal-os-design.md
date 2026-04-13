# Personal OS Design

更新日期：`2026-04-13`

这篇文档落的是 `2026-04-13` 对话中敲定的 **personal OS 运转机制**。

它和前面几版文档的关系：

- [reframed-architecture.md](reframed-architecture.md) 给出 4 层分类(Capture / Workspace / Store / Projections)的**语义切分**
- [solution-design-v2.md](solution-design-v2.md) 给出 memory_system 子系统的 **Phase 1 目录与交付物**
- 这篇 personal-os-design 给出**整个 OS 的运转机制**：文件怎么流动、事件怎么触发、agent 怎么改动、人怎么 review

这三层互不取代：reframed 是"怎么切分"，v2 是"memory 子系统落地什么"，personal-os 是"整个 OS 作为一个 build system 怎么跑起来"。

## 0. TL;DR

**一句话**：把个人 OS 做成一个 build system，所有变更都是 git diff，所有处理都走 PR，所有 view 都是预编译产物，所有判断由 agent + guideline 做，所有管线由代码做。

**核心组件**：

- 真相源：人或 agent 手写的 `kind: source` 文件
- 产出：由依赖图自动重建的 `kind: derived` 文件
- 触发：watcher 扫 main 的 git diff，按 frontmatter 分类
- 调度：dispatcher 从 inbox 取 TODO，启动 agent + 相关 guideline
- 判断：agent 产 PR，commit 到 `pr/*` branch
- Review：人 `git diff` 看 PR，三种出口(approve / reject / request-changes)
- 落盘：`approve.py` 跑 rebuild、squash merge、写 change log

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
│ source     │──┬──▶│watcher│────▶│monitor-inbox│──▶│dispatcher│──▶│agent+rule│──▶│ pr branch│
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
                │                                   ┌──────────┐    rebuild downstream
                └───────────────────────────────────│approve.py│────────────────────────┐
                                                    └──────────┘                        │
                                                         │                               │
                                                         ▼                               ▼
                                                   ┌──────────┐                   ┌───────────┐
                                                   │squash→main│                  │ derived   │
                                                   └──────────┘                   │ rebuilt   │
                                                                                  └───────────┘
```

**数据流**：

1. 人或 agent 写一个 `kind: source` 文件并 commit 到 main
2. `watch.py` 扫 `git log main`，按 frontmatter 给每个 diff 分类，在 `system/monitor-inbox/` 产一个 TODO
3. `dispatch.py` 从 inbox 取最早一条 TODO，启动 agent(Claude Code)，加载 `global.md + events/<event_type>.md`
4. agent 按 guideline 的规则处理：读触发源、判断、可能在 `pr/<id>-...` branch 上产 commit
5. agent 在 inbox 写结束标记，或直接将 inbox 项从 todo 改为 done
6. 人看 inbox 里的 "ready for review"，`git diff main...pr/<id>`
7. 人三选一：approve / reject / request-changes
8. approve 的话，`approve.py` 跑 `deps.py` 算下游，rebuild derived 文件，squash merge 进 main，删 branch，写 change log

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

- `watch.py` 写 `system/monitor-inbox/`
- `dispatch.py` 改 inbox 状态
- `approve.py` / `reject.py` / `request-changes.py` 写 `system/change-log/`、`system/change-request/`
- `request-changes.py` 在需要时入队 `pr_revision`

普通 agent、普通工作流、人工日常内容都不应该直接改 `system/**`。

### 4.2 可直写（无需 review）

这些目录是"人还没消化过的原材料"或"系统自己的工作队列"，agent 可以直接写文件并 commit 到 main：

- `conversation memory/` —— 对话原始回流
- `ingest src/` —— 外部原材料捕获(clipper、book 摘录等)
- `assist/preference/improve/learning inbox/` —— 待审的偏好观察

这里要注意：

- `system/monitor-inbox/` 和 `system/change-log/` 虽然也写在 main 上，但它们不属于“普通 agent 可直写”
- 它们只属于 `system-owned`

### 4.3 必须走 PR

其他一切都必须经过 PR。关键列表：

- `user/` —— 身份真相源，agent 不能改
- `knowledge base/` —— 长期知识
- `assist/section detail/`、`assist/sp/`、`assist/view/` —— 依赖传播链的中转和终点
- `assist/preference/current/` —— 生效中的偏好(`learning inbox` 是 agent 可写的，`current` 不可)
- `workspace/` —— 灰色地带但取严格态度：**workspace 也要 review**
- `system/operating-rule/` —— agent 不能自己改游戏规则
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
- `Category: <event_type>` —— 用于 `system/change-request/` view 分组
- `Affects-downstream: yes|no` —— 是否需要 `approve.py` 跑 rebuild

### 5.4 MVP 约束：一个 PR 只改一个 source 文件

多个 source 改动拆成多个 PR。理由：每条 PR 的 review 焦点窄，决策可控；跨文件的原子性改动在 MVP 阶段遇不到。

`approve.py` 开头有一条断言强制执行这条约束，实现大致是 `git diff main...HEAD` 后检查有 `kind: source` 的文件数量不超过 1。

### 5.5 三种 review 出口对应三个脚本

- `scripts/approve.py pr/0001` —— 跑 `deps.py`、rebuild 所有下游 derived 文件、在 branch 上加一个 "Rebuild derived files" 的 commit、squash merge 进 main、删 branch、更新 change log
- `scripts/reject.py pr/0001 --reason "..."` —— `git branch -D`、reason 写进 change log
- `scripts/request-changes.py pr/0001` —— 起编辑器让人写 comment，把 comment commit 到 branch 上的 `system/pr-review/pr-0001-comments-round<N>.md`，然后**直接入队**一条 `event_type: pr_revision` 的 TODO

### 5.6 Comment 往返机制

**载体**：comment 文件 commit 在 PR 的 branch 上，路径为 `system/pr-review/pr-<id>-comments-round<N>.md`。

**为什么 commit 在 branch 上而不是 branch 外**：comment 是 PR 历史的一部分，应该和 PR 的 commits 一起存活、死亡。reject → branch 删 → comment 也一起消失。approve → squash merge → comment 不进 main。生命周期由 git branch 本身管理，零手工清理。

**轮次**：**每轮 comment 新建一个文件**，不 append。追溯清晰，`round1` / `round2` / `round3` 的命名一眼看出时序。

**agent 的 counter-argument**：允许。agent 读 comment 后，如果认为 comment 不合理或和原意冲突，可以在 branch 上新建 `system/pr-review/pr-<id>-response-round<N>.md` 说明 counter-argument，然后把 inbox ball 踢回人。

**Round 上限**：没有硬上限。guideline 要求 agent 在 `round >= 3` 时主动喊停，在 response 里明确说"我认为我们在原地打转，建议 reject 或明确改写成 ..."，强迫 agent 在多轮无果时停。

**request-changes 的 dispatcher 路径**：

1. 人跑 `request-changes.py pr/0001`，写 comment
2. 脚本 commit comment 文件到 branch，然后直接在 `system/monitor-inbox/` 入队一条 `event_type: pr_revision` 的 TODO，frontmatter 带 `pr_branch: pr/0001`、`comment_file: system/pr-review/pr-0001-comments-round1.md`、`round: 1`
3. 下次 `dispatch.py` 跑，取到这条 TODO，启动 agent 并加载 `events/pr_revision.md`
4. agent checkout 到 `pr/0001` branch，读 comment、读原始 commit message、按 comment 修改或产 response
5. `dispatch.py` 或专门脚本更新 inbox 状态；agent 不直接在 main 上改队列文件

### 5.7 Squash merge

approve 时 PR 的所有 commit(包括 comment 文件、response 文件、rebuild derived 文件)**被 squash 合成一个 commit 进 main**。主库保留：干净的 source 改动 + rebuilt derived，不保留 comment 文件、response 文件等 review 过程产物。

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
- 有 `Rebuilt-by: approve.py pr/<id>` —— 跳过
- 有 `System-owned-by: watch.py` —— 跳过
- 有 `System-owned-by: dispatch.py` —— 跳过
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
   | `ingest src/**` | `ingest` |
   | 其他 | `unclassified` |

7. 在 `system/monitor-inbox/` 写一个 TODO 文件

MVP 阶段 guideline 只覆盖 `conversation` 和 `pr_revision` 两类，其他类别的 TODO 被 dispatcher 路由到 `unclassified` handler(规则是"记一条 log 然后 skip")。

这里的 `pr_revision` 不是 watcher 扫出来的，而是 `request-changes.py` 直接入队的。

## 7. Change request 队列的组织

### 7.1 单一真相源 + materialized view

所有 PR metadata 住在 `system/change-request/`(虽然 PR 本身是 git branch，但 inbox 里的 PR-related TODO 都归这里)。`assist/preference/improve/change request/` 是一个**自动生成的 view**(软链接或代码生成的索引)，只列 `Category: preference` 的 PR。

这个 view 的存在是为了让 `preference/improve/` 的 `learning inbox → change request → history` 闭环在视觉上完整，实际真相源唯一。

### 7.2 和 PR branch 的关系

`system/change-request/` 不存放 PR 的 diff 或 commit(那些在 branch 上)，只存放 PR 的**索引和索引元数据**：

- 列出所有 active PR 及其 branch 名
- 记录每个 PR 的状态(pending / under-review / merged / rejected)
- 记录每个 PR 的 category、trigger、round 数

这些元数据可以由 `scripts/ls-prs.py`(或类似)实时从 git 读出来，也可以作为缓存文件维护。MVP 里用"实时读 git"就够了，不做缓存。

## 8. Guideline 的结构

### 8.1 目录布局

```
system/operating-rule/
├── global.md                    # 跨事件的硬约束 + agent 身份
└── events/
    ├── conversation.md          # MVP 唯一的事件处理规则
    ├── pr_revision.md           # (MVP 第二份，处理 comment 回合)
    ├── daily_memo.md            # Phase 2
    ├── identity_change.md       # Phase 2
    ├── project_update.md        # Phase 2
    └── ...
```

### 8.2 dispatcher 的载入逻辑

```python
def load_guideline(event_type: str) -> str:
    return read("global.md") + "\n\n" + read(f"events/{event_type}.md")
```

dispatcher 把这份组合文本作为 agent 启动时的 system prompt(或放进 `CLAUDE.md` 的临时覆盖)，加上 inbox TODO 的内容作为当前任务。

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
| 读/写 frontmatter | 决定改 SP 的哪里、怎么改 |
| `deps.py` 算依赖图 | 写 PR 的 commit message |
| `approve.py` 跑 rebuild | 读 comment、决定怎么回应 |
| `approve.py` squash merge | 产出 counter-argument 或修订 |
| 写 change log | |
| 更新 `.watcher-state` | |

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

**缓解**：`deps.py` 用 DFS 检测环，发现环直接报错并拒绝 rebuild。

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

## 13. 下一步

见 [docs/implementation/mvp-week1.md](../implementation/mvp-week1.md)。
