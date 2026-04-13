# MVP Week 1

更新日期：`2026-04-13`

这篇文档是 [personal-os-design.md](../architecture/personal-os-design.md) 的落地计划，只覆盖 **Week 1 内必须跑通一条端到端闭环**的最小范围。

## 1. Week 1 的唯一目标

**跑通一条真实对话触发的 PR 流程，从 source 变动到下游 view 被 rebuild，全程不缺环节。**

这个目标不追求功能完整，只追求**链路完整**。跑通之后，其他事件类型、其他目录、自动化机制都是重复同一套模式的扩展，不是新设计。

## 2. Scope 裁剪

**MVP 只覆盖**：

- 1 个事件类型：`conversation`
- 1 个 view：`assist/view/claude-code/CLAUDE.md`
- 1 份 SP：`assist/sp/master.md`
- 1 份 section detail：`assist/section detail/me.md`
- 6 个顶层目录：`user/`、`conversation memory/`、`assist/{section detail, sp, view}/`、`system/{monitor-inbox, change-request, change-log, operating-rule, pr-review}/`

**MVP 显式不做**：

- `workspace/`、`knowledge base/`、`config store/`、`ingest src/`、`daily memo/`
- `assist/preference/`、`assist/tool/`
- 组合式 SP(master + role overlay)
- 除 `conversation` 之外的 event 类型
- 自动化 watcher(cron、launchd、git hook)
- cross-PR conflict resolution
- fact staleness / invalidation 机制

## 3. 交付物清单

### 3.1 仓库骨架

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
    ├── monitor-inbox/                    # agent 工作队列
    ├── change-request/                   # PR 索引(MVP 阶段可空)
    ├── change-log/                       # append-only 审计
    ├── pr-review/                        # comment / response 文件
    └── operating-rule/
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

### 3.2 `scripts/deps.py`

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

### 3.3 `scripts/watch.py`

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
4. 为每个未跳过的事件在 `system/monitor-inbox/` 产一个 TODO markdown
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

### 3.4 `scripts/dispatch.py`

**输入**：无
**行为**：
1. 扫 `system/monitor-inbox/*.md`，按 `id` 排序取最早的 `status: todo`
2. 把它改成 `status: running`，写回 main，并带 `System-owned-by: dispatch.py`
3. 读 frontmatter 的 `event_type`
4. 读 `global.md + events/<event_type>.md`，拼成 agent 的指令文本
5. 启动 Claude Code：`claude "<指令文本>\n当前任务：处理 <inbox path>"`
6. agent 跑完后：dispatcher 不直接改业务文件，只由脚本负责把 inbox 状态推进到 `done / skipped / unsure / waiting_rereview`
7. 如果 `event_type` 不在 MVP 范围内(`unclassified`、`daily_memo` 等)，直接标记 `status: skipped`，在 change log 写一行

预计行数：**60 行**以内。

### 3.5 `system/operating-rule/global.md`

内容大纲：

- 系统简介(1 段)
- agent 身份(你是 personal OS 的 operating agent，职责是根据事件产生高质量的变更提案)
- 全局硬约束：
  - 所有 source 改动必须走 PR，不能直接 commit 到 main
  - 所有 PR 的 commit message 必须带 `Trigger:`、`Category:`、`Affects-downstream:` trailer
  - 每个 PR 只能改一个 source 文件
  - 不许修改 `user/`、`knowledge base/`、`config store/`、`system/operating-rule/`、`assist/preference/current/`
  - 不许直接写 derived 文件(`kind: derived`)；derived 由 approve.py 自动 rebuild
  - 不许直接修改 `system/**`；`system/**` 只能通过固定脚本入口改动
- 出错时的 fallback：
  - 如果你不确定怎么处理一个 inbox 项 → 在 change log 写一行 "unsure: <reason>"，把 inbox 项标记为 `unsure` 状态，交给人决定
  - 如果你发现 guideline 本身有问题 → 不要自己改 `operating-rule/`，而是在 change log 写一行 "guideline-issue: <desc>"，人会来处理
- 出结束标记的约定：
  - agent 不直接在 `main` 上改 inbox 文件
  - 需要变更状态时，由 `dispatch.py` 或其他系统脚本代写，并带 `System-owned-by:` trailer

预计行数：**60 行**以内。

### 3.6 `system/operating-rule/events/conversation.md`

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

### 3.7 `system/operating-rule/events/pr_revision.md`

内容大纲：

- 触发条件：inbox 里出现 `event_type: pr_revision`
- 处理流程：
  1. 读 inbox 项的 `pr_branch` 和 `comment_file`
  2. `git checkout <pr_branch>`
  3. 读 `comment_file`(最新一轮)
  4. 读该 branch 上原始 PR 的 commit message(得到原始意图)
  5. 判断 comment 是否合理：
     - 合理且能满足 → 修改相关文件，`git commit` 一条 "Addresses: <comment_file>" 的新 commit
     - 不合理或和原意冲突 → 在 branch 上新建 `system/pr-review/pr-<id>-response-round<N>.md` 写 counter-argument，commit
  6. 回到 main 后，由系统脚本入队新 TODO `event_type: pr_ready_for_rereview`，frontmatter 带 `pr_branch`、`round`(递增)
- Round 上限约束：
  - 如果 `round >= 3`，response 文件里必须明确写 "我认为我们在原地打转，建议 reject 或明确改写成 ..."
- 允许改的文件：
  - 当前 pr branch 上的目标 source 文件
  - `system/pr-review/pr-<id>-*.md`
- 禁止改的文件：
  - 所有其他文件

预计行数：**60 行**以内。

### 3.8 `assist/sp/master.md` 初版

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

说明：MVP 第一次跑 `approve.py` 之前，这份文件可以手工初始化。`section detail/me.md` 同理，用手工初始化的方式填一个最小版本，upstream 指向 `user/about me/me.md`。

### 3.9 `scripts/approve.py`

**输入**：`pr/<branch-name>`
**行为**：
1. 断言当前 main 是 clean(没有 uncommitted changes)
2. `git checkout <branch>`
3. 检查这个 branch 相对 main 改了哪些文件，用 `deps.py` 拿到每个 source 文件的 `kind`
4. 断言最多只有 1 个 `kind: source` 文件被改(MVP 约束)
5. 用 `deps.py --downstream <source>` 算出所有要 rebuild 的 derived 文件
6. 对每个 derived 文件：
   - 读它的 `upstream:`
   - 根据 upstream 内容调用 rebuild 逻辑重新生成该 derived
   - MVP 里 rebuild 逻辑是**简单拼接**或**调用一次 Claude 做"基于 upstream 产出 downstream"**(由 guideline 决定)
   - 更新 frontmatter 的 `last_rebuild_at` 和 `generated_by`
7. `git add <all rebuilt derived files>`
8. `git commit -m "Rebuild derived files for pr/<id>\n\nRebuilt-by: approve.py pr/<id>"`
9. `git checkout main`
10. `git merge --squash <branch>`
11. `git commit -m "<原始 PR 的标题>\n\n<原始 PR 的正文>\n\nApproved-by: approve.py pr/<id>"`
12. `git branch -D <branch>`
13. 在 `system/change-log/` append 一行
14. 在 `system/monitor-inbox/` 把对应的 `pr_ready_for_rereview` 或原始 `conversation` TODO 标记为 done(如果还没被 agent 标记)

**rebuild 逻辑的 MVP 简化**：
- 对 `section detail/me.md`：读 `user/about me/me.md` 全文，直接复制进去(或用 Claude 做简短摘要)
- 对 `sp/master.md`：不自动 rebuild，因为 sp 的 "工作方式" 段落需要保留历史规则，PR 直接 commit 的新版就是最终版
- 对 `view/claude-code/CLAUDE.md`：读 `sp/master.md` 全文，按 CLAUDE.md 的格式包装

MVP 里 rebuild 逻辑不追求完美，追求"能跑完一次 demo 即可"。Phase 2 再设计合适的模板。

预计行数：**150 行**以内(含 rebuild 逻辑)。

### 3.10 `scripts/reject.py`

**输入**：`pr/<branch-name>` + `--reason "..."`
**行为**：
1. `git branch -D <branch>`
2. 在 change log 追加 "rejected: pr/<id> - <reason>"
3. 把相应的 inbox 项标记为 `rejected`

预计行数：**30 行**以内。

### 3.11 `scripts/request-changes.py`

**输入**：`pr/<branch-name>`
**行为**：
1. 起编辑器(`$EDITOR` 或 `vim`)让人写 comment
2. 把 comment 保存到 `system/pr-review/pr-<id>-comments-round<N>.md`，N 从现有文件推断
3. `git checkout <branch>`，`git add` comment 文件，`git commit -m "Review comments for pr/<id> (round <N>)"`
4. `git checkout main`
5. 在 `system/monitor-inbox/` 产一个新 TODO，`event_type: pr_revision`，frontmatter 带 `pr_branch`、`comment_file`、`round`

预计行数：**60 行**以内。

## 4. 验收闭环

**这一条闭环跑通 = MVP 成立**。

### 步骤

1. **(人工)** 和 Claude Code 做一段真实对话，对话里故意让 agent 犯一个小错(比如不先确认假设就直接回答)
2. **(人工)** 把 transcript 保存成 `conversation memory/2026-04-13/claude-code.md`，`git add && git commit -m "Save conversation 2026-04-13"`
3. **(人工)** 运行 `python3 scripts/watch.py`
   - 预期：`system/monitor-inbox/0001-conversation.md` 出现，`event_type: conversation`，指向刚才的 transcript 文件
4. **(人工)** 运行 `python3 scripts/dispatch.py`
   - 预期：Claude Code 启动，读 `global.md + events/conversation.md + inbox item`，读对话 transcript
   - 预期：agent 识别出 "没有先确认假设" 这个 pattern，判断这是 SP 层的问题
   - 预期：agent `git checkout -b pr/0001-add-assumption-check`，编辑 `sp/master.md`，commit
   - 预期：agent 回到 main，更新 inbox 项为 done，在正文注明 `pr/0001-add-assumption-check`
5. **(人工)** `git diff main...pr/0001-add-assumption-check` 查看改动
6. **(人工)** 运行 `python3 scripts/approve.py pr/0001-add-assumption-check`
   - 预期：`approve.py` 用 `deps.py` 算出 `view/claude-code/CLAUDE.md` 是 `sp/master.md` 的下游
   - 预期：`CLAUDE.md` 被 rebuild，branch 上出现 rebuild commit
   - 预期：branch squash merge 进 main，commit message 带 `Approved-by:`
   - 预期：branch 被删
   - 预期：change log 追加一行
7. **(人工)** 打开新 Claude Code session
   - 预期：session 读到的 `CLAUDE.md` 是新版，包含"先确认假设"的规则
   - 预期：在类似情境下，agent 的行为已经改变

### 验收红线(必须全部满足)

- [ ] 一次对话 → 一条 inbox TODO → 一个 PR → 一次 approve → 一次 merge → 一个新版 view
- [ ] 整条链路没有任何一步卡住
- [ ] 没有任何一个文件需要手工编辑才能让流程继续(除了第一步的 transcript 保存)
- [ ] 再跑一次 `watch.py` 不会把 approve 产生的 merge commit 当成新事件(trailer 机制生效)
- [ ] 再跑一次 `dispatch.py` 不会有残留 `todo` 状态的 inbox 项

### 允许 MVP 失败但要记录的情况

- agent 误判对话的 root cause，产出无意义的 PR → **接受**，你 reject 它，这说明 guideline 需要改进，而不是系统不 work
- `approve.py` rebuild 出的 `CLAUDE.md` 格式不好看 → **接受**，MVP 不追求 rebuild 模板完美
- commit message trailer 格式和预期有偏差 → **不接受**，trailer 是 watcher 的依据，必须严格

## 5. 时间预算

- 仓库骨架：30 分钟
- `global.md` + 两个 events 文件：1-2 小时
- `deps.py` + `watch.py` + `dispatch.py`：半天
- `approve.py`：半天
- `reject.py` + `request-changes.py`：1-2 小时
- 第一次端到端跑通 + 调试：1 小时到半天(看第一次跑遇到什么)
- **合计**：一个周末应该能完成。超过一周还没跑起来 = scope 太大，需要继续砍。

## 6. 第一次跑通之后

跑通之后，**预计 guideline 的 70% 内容需要重写**。这很正常，guideline 是"用出来的"不是"想出来的"。第一次跑通的价值是**验证链路完整**，不是**验证 guideline 完美**。

接下来的 Phase 2 优先顺序建议：

1. 加第二个 event 类型(`daily_memo` 或 `ingest`)——复制 conversation.md 的模板即可
2. 加 `workspace/` 相关的 event 处理
3. 加自动化 watcher(launchd 或 cron)
4. 加组合式 SP(master + role overlay)
5. 加 preference 完整闭环
6. 加 fact staleness 机制
