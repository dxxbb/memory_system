---
kind: source
---

# 设计：knowledge base → SP 接入 + Benchmark 系统

日期：2026-04-17
状态：proposed（等 dxy review）
作者：agent（Builder 模式）

---

## 1. 目标与约束（重述）

**目标**：积累 dxy 的所有 context（info / knowledge / preferences），并且**让 model 真的能用到**——不利用的 context 等于不存在。

**约束**：
- 要考虑 model 能力（目标：Claude Code / Opus 为主）
- 要考虑 model 在哪个 context 长度下表现最好（合理，不求极致长短）
- 不得滥用 SP 预算（一篇文章直接塞进去是反例）

**"知道"的判定标准**（dxy 确认 Q1）：
- **a**：内容直接在 SP 里
- **b**：内容通过明确的 Read 路径可达，且 agent 知道去找

**最不能接受的失败**（dxy 确认 Q2）：**忘了**（FN）—— agent 不知道、也不知道去找。

---

## 2. 目标架构

### 2.1 Knowledge base topic 模型

**结构**（一级扁平）：

```
knowledge base/
├── index.md              # topic 列表，只有这个进 SP
├── ai-policy.md          # topic 合成页，多来源
├── agent-memory.md
├── llm-training.md
├── ...
└── log.md
```

**Topic 粒度**：dxy 未来 6-12 个月会持续追踪的关注点。单篇文章不是 topic。

**Topic 页**：多来源合成，frontmatter `sources:` 追加式增长。

**为什么扁平一级**：MVP 简单，数据量小。等 topic > 20 且单 topic 子主题 > 3 时再分层。

### 2.2 Knowledge base index 进 SP

**机制**：

- `knowledge base/index.md` 成为 `assist/sp/master.md` 的 `upstream:` 之一
- sp-rebuild 时把 index 内容**原样**嵌入 master.md 的某个 section（如 `## Knowledge base`）
- Topic 页**不进 SP**——agent 需要时按 index 里的路径 `Read`

**SP 预算**（dxy 确认参数 2）：

- `assist/sp/master.md` 整体 ≤ 2500 tokens（宽松 3500）
- `knowledge base/index.md` ≤ 30 行 / 1500 字符
- 当前 master.md 约 400 行，需检查并压缩

### 2.3 依赖图变化

**Ingest 事件**（原 `Affects-downstream: no`）→ 改为 `yes`：

- 受影响路径：`knowledge base/index.md` 变 → `assist/sp/master.md` rebuild → `assist/view/claude code/CLAUDE.md` rebuild
- 注意：topic 页本身不进 SP，所以 topic 页变化不触发 rebuild，只有 index 变化才触发
- 实现：master.md 的 `upstream:` 加上 `knowledge base/index.md`（不加 topic 页）

### 2.4 关于已有 section detail 层

Section detail 保留现状——它是从**对话 / 项目**提炼的碎片，用于 me / project / preference 子结构。**Knowledge base 是独立并行的层**，不与 section detail 混。

两层的区别：

| 维度 | section detail | knowledge base |
|---|---|---|
| 来源 | 对话 memory、workspace | ingest src（外部素材） |
| 内容 | dxy 自身的身份 / 项目 / 偏好 | dxy 追踪的外部知识 |
| 粒度 | fragment-level | topic-level |
| SP 进入 | master.md 按 selection_criterion 选择 fragment | index.md 整体嵌入 |

冲突检测（ingest 事件规则里）：新 ingest 发现与 section detail fragment 矛盾时 flag 到 `system/for-you/suggestions.md`，不自动改对方。

---

## 3. Benchmark 系统设计

### 3.1 文件布局

**forge repo**（脚本）：

- `scripts/bench.py` —— runner

**dxy_OS vault**（数据）：

- `system/bench/questions.md` —— 题库（`kind: system`）
- `system/bench/judge-prompt.md` —— judge system prompt 模板（`kind: system`）
- `system/bench/reports/YYYY-MM-DD-<change-label>.md` —— 每次运行报告（`kind: system`）

### 3.2 bench.py 运行流程

```
1. 读 questions.md，解析出问题列表（按 tier 分组）
2. 读当前 assist/view/claude code/CLAUDE.md（实际注入 CC 的 SP）
3. 对每个问题：
   a. 构造 Claude API 请求：system = CLAUDE.md 内容 + judge instructions；user = 问题
   b. Phase 1（先实现）：不开 tool use，只看 model 能否从 SP 直接答
   c. Phase 2（后续）：开 tool_use（给 Read/Grep 的 mock 实现），看 model 能否识别要读哪个文件
4. 把 {question, expected, actual, reach-attempts} 喂给 judge model，让它输出 rating + reason
5. 聚合分数，按 tier pass/fail 判定
6. 写报告到 reports/<date>-<label>.md，并 console 彩色输出
```

**Phase 1 vs Phase 2**（MVP 决策）：

先实现 Phase 1（只测 SP 直接覆盖，rating 里只分 PASS / FAIL-FORGOT / FAIL-WRONG）。

Phase 2（tool-use 模拟）留到第一次 bench 跑完、看到多少题需要 reach-path 再实现。

### 3.3 questions.md schema

```markdown
---
kind: system
---

# Benchmark questions

## Tier: identity (必须 100% PASS/PASS-REACH)

### Q1.1
**问**：What's my GitHub handle?
**期望**：dxxbb
**来源**：user/about me/me.md

### Q1.2
**问**：What's my primary work language?
**期望**：Simplified Chinese
**来源**：assist/section detail/me/identity.md
...

## Tier: preferences (必须 100%)
...

## Tier: project (≥ 90%)
...

## Tier: knowledge (≥ 80%)
...

## Tier: reach-path (≥ 80%，Phase 2 才测)
...

## Tier: noise (0 FAIL-NOISE)
...
```

每题必带：**问**、**期望的核心答案**、**来源路径**（供 judge 对照）。

### 3.4 judge prompt 设计

judge 收到：

- 问题文本
- 期望答案（事实或关键点）
- 来源路径（可选参考）
- agent 的实际答案

输出 JSON：

```json
{
  "rating": "PASS | PASS-REACH | FAIL-FORGOT | FAIL-WRONG | FAIL-NOISE",
  "reason": "一句话解释"
}
```

Rating 含义：

- **PASS**：答对，不问用户
- **PASS-REACH**（Phase 2 才有）：SP 里没有直接答案，但 agent 正确地识别出要 Read 哪个文件并给出正确答案
- **FAIL-FORGOT**：答不上，也没试着去找——**最严重**（违背目的）
- **FAIL-WRONG**：答了但错（编、hallucinate）
- **FAIL-NOISE**：答对但夹带大段无关 context（预防 SP 过载）

### 3.5 Pass 门槛（dxy 确认参数 4）

| Tier | 门槛 |
|---|---|
| identity | 100% PASS/PASS-REACH，0 FAIL-FORGOT |
| preferences | 100% PASS/PASS-REACH |
| project | ≥ 90% |
| knowledge | ≥ 80% |
| reach-path | ≥ 80%（Phase 2） |
| noise | 0 FAIL-NOISE |

**总体判定**：全部 tier 达标 = PASS；任一 identity/preferences 有 FAIL-FORGOT = **FAIL HARD**；其他情况按 tier 分项看。

### 3.6 报告格式（dxy 确认参数 5）

- **Markdown 文件**：写入 `system/bench/reports/<date>-<label>.md`，方便 git diff 看趋势
- **Console 输出**：彩色（绿 PASS、黄 PASS-REACH、红 FAIL-*），末尾打总分与 HARD FAIL 明显标记
- **每次 bench**：绑定一个 change-label（如 `kb-sp-integration`、`add-observability-topic`），对应本次架构变更

### 3.7 Seed 题库（dxy 确认参数 3 = 我 propose 初版）

建议 **22 题**（可调），按 tier 分布：identity 5 / preferences 4 / project 5 / knowledge 4 / reach-path 2 / noise 2。

我会在实施阶段把第一版 `questions.md` 写出来让你 review。

---

## 4. Operating-rule 修改

### 4.1 `system/operating-rule/events/ingest.md`

**主要改动**：

- Step 2（评估素材）加第 4 个问题：**"这份素材属于哪个 existing topic？没有则是否值得开新 topic？"**
  - 匹配已有 → 合并到现有 topic 页
  - 开新 topic → 必须说明理由（现有 topic 都不合适）
- Step 4 Flow 扩展：
  - Step 4.1：更新或新建 `knowledge base/<topic>.md`
  - Step 4.2：更新 `knowledge base/index.md`（如果新增 topic）
  - Step 4.3：更新 `knowledge base/log.md`
  - **Step 4.4（新）**：如果 index.md 有变 → 调 `sp-rebuild.md` 重建 `assist/sp/master.md`
  - **Step 4.5（新）**：如果 master.md 有变 → 调 `view-rebuild.md` 重建 `assist/view/claude code/CLAUDE.md`
  - Step 4.6：冲突 flag（原 4.4）
  - Step 4.7：commit + 回 main
- Commit template：`Affects-downstream: yes`（如果有新 topic 或 index 变动），否则 no
- 允许改的文件加：`assist/sp/**`、`assist/view/**`

**Topic 匹配的指导**：

- 标题相似度
- tags 重叠
- 读现有 topic 页的 `## 子主题` 列表看是否有容纳空间
- 不确定 → `status: unsure`，交给 dxy 判断

### 4.2 `system/operating-rule/global.md`

**§条件性可写（item 8）扩展**：

原：
> 只有 `ingest` 事件可以写，且 PR 只能改 `knowledge base/**` 和 `system/for-you/suggestions.md`，不触发 section → sp → view 链式 rebuild

改为：
> 只有 `ingest` 事件可以写 `knowledge base/**`。Ingest PR 可以改：`knowledge base/**`、`assist/sp/**`、`assist/view/**`、`system/for-you/suggestions.md`。当 index.md 有变动时**必须**触发 sp 和 view rebuild；topic 页内容变动但 index 不变时不触发。

### 4.3 新规则：benchmark 触发条件

在 global.md 加一段 `## Benchmark 触发`：

列出哪些**架构变更**必须跑 bench（dxy 确认 Q5）：

- SP 结构变化（master.md 的 selection_criterion 或 upstream 列表变化）
- 新 event 类型上线
- Knowledge base index 格式或语义变化
- Section detail 子结构变化
- 新 target tool 上线（assist/view/ 新文件）

**流程**：变更 PR merge 前跑 bench；未达标不合并。

---

## 5. 现有数据迁移

现有：`knowledge base/tech/ai/policy/jensen-vs-dwarkesh-chip-export.md`

迁移目标：

- 新路径：`knowledge base/ai-policy.md`（一级扁平）
- 标题：`# AI policy`
- frontmatter：
  ```yaml
  kind: source
  sources:
    - ingest src/clipping/Thread by @DanielMiessler.md@8e36d845
  tags: [ai-policy]
  status: active
  created: 2026-04-17
  ```
- 正文：
  - `## Summary`（顶层 topic 描述：为什么关注 AI policy、当前关注点）
  - `## 子主题` section——每个子主题一段：
    - `### 对华 AI 芯片出口（2026-04）` —— 把原 Jensen/Dwarkesh note 内容移进来
  - `## Key claims across subtopics`（空，待积累）
  - `## My take`（空或移入）
  - `## Connections`（空）
  - `## Conflicts`（空）
- 删除：`knowledge base/tech/` 整个子树

更新 `knowledge base/index.md`：

```
# Knowledge Base · Index

按 topic 组织。每行 = 一个 topic。详见 topic 页。

- [AI policy](ai-policy.md) — 对华芯片出口、AI 监管、产业政策
```

（未来 index 格式还可能再演化；MVP 用这个）

---

## 6. 执行顺序（按 PR 列出）

**[Builder PR 1]**（在 forge 这边直接 commit 到 dxy_OS）

- 改 `events/ingest.md`（§4.1）
- 改 `global.md`（§4.2 + §4.3）
- 说明：规则更新，尚无实施

**[Builder PR 2]**（forge 这边）

- 创建 `dxy_OS/system/bench/questions.md`（seed 题库）
- 创建 `dxy_OS/system/bench/judge-prompt.md`
- 创建 `forge/scripts/bench.py`（Phase 1 runner）
- 说明：bench 基础设施

**[Migration PR 3]**（User 模式 CC 在 dxy_OS 下处理，当成一次 ingest 事件的 follow-up 或手工 PR）

- 迁移 jensen-vs-dwarkesh → ai-policy.md
- 更新 index.md
- 删除 tech/ 目录
- **这是第一次 ingest 事件升级版的端到端验证**：走完 knowledge → sp → view rebuild
- 产出 master.md + CLAUDE.md 的 diff

**[Bench run 1]**（在 PR 3 合并前跑）

- 用 bench.py 跑一次 PR 3 的 sp 和 view
- 报告目标：identity/preferences 维持 100%，knowledge 新增的 "AI policy" 相关问题应该能答

**[以后的 PR]**（新 topic 进来、section detail 有大变化等场景）

- 每次架构变动配套跑 bench，报告存 reports/ 目录

---

## 7. 开放问题 / 风险

1. **bench.py 如何"模拟 CC session"**
   - Phase 1：纯 Anthropic API + message-only（不带 tool use）。成本低。不测 reach-path
   - Phase 2：加 tool_use，mock Read/Grep。需要更多工作，但能覆盖 b-type 判定
   - 建议：先跑 Phase 1，看 FAIL-FORGOT 率再决定 Phase 2 优先级
2. **judge 的 hallucination 风险**
   - judge 自己可能判错。对策：judge 输出带 reason，dxy 看报告时 spot-check 分数边界的题
3. **SP 长度压力**
   - master.md 现在约 400 行。加 index 30 行不算多。但 section detail 本身有无压缩空间？需要和 kb 接入一起审视
4. **问题库老化**
   - 系统演化，旧问题可能失效（比如 dxy 换工作了）。定期（季度）review questions.md
5. **Topic 粒度跑偏**
   - Agent 可能倾向开太多新 topic 或塞进不匹配的 topic。对策：events/ingest.md 里 anti-pattern 强调 + 跑一段时间后人工整顿
6. **多 model 兼容**
   - 当前只测 CC。未来若加 Haiku / codex / other，每个 target tool 的 view 都需要独立 bench

---

## 8. 我需要 dxy 确认的点（批量，尽量一次过）

1. **topic 粒度**："AI policy" 作为迁移目标 OK 吗？还是更窄（"us-china-chip-export"）？
2. **seed 题库 22 题的分布**（5/4/5/4/2/2）合理吗？或者你有偏重？
3. **PR 3 的身份**：属于一次特殊的 "migration 事件" 还是当作 "改造 bug" 走 Builder 直接 commit？我建议 Builder 直接改，因为本质是 Architecture 迁移不是新知识消化
4. **Bench reports 的长期归档策略**：全量 git 追踪？还是保留最近 N 份？我建议全量，文件不大
5. **questions.md 初版是我全写还是先 propose 一半让你补**？我建议全写，你修

你回这 5 条我就开始 PR 1 和 PR 2 的实施。
