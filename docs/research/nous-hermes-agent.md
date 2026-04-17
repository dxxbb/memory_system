# Nous Research: Hermes Agent 调研

更新日期：`2026-04-16`

主源：
- <https://github.com/nousresearch/hermes-agent>
- <https://hermes-agent.nousresearch.com/docs/>

## 1. 一句话定位

Hermes 是 **"能跑在任何地方的、带闭环学习的、多平台 agent 运行时"**。它不是一个 memory system，也不是一个 framework，而是一个**长期运行的、自改进的 agent 服务**——目标是让 agent 脱离单机、跨 session 累积知识。

核心主张：**agent 是一个长期存活的实体，不是一次性的推理函数。**

## 2. 核心机制

### 2.1 记忆层（三层架构）

| 层 | 文件/存储 | 作用 |
|---|---|---|
| **语义/事实记忆** | `MEMORY.md` | 环境事实、学到的教训、用户偏好。条目用 `§` 分隔 |
| **用户画像** | `USER.md` | 身份、偏好、沟通风格、技术水平 |
| **情景记忆** | SQLite + FTS5 | 所有 CLI / 消息 session 的历史对话，自动索引 |
| **程序记忆** | `~/.hermes/skills/` | SKILL.md 格式，带 frontmatter，agent 可自主创建 |

### 2.2 闭环学习机制（核心差异化）

Hermes 最独特的一点是**自主创建 skill**：

触发条件：
- 完成一个 5+ 工具调用的复杂任务
- 遇到错误后找到可用方案
- 用户纠正 agent 方向之后
- 发现非平凡 workflow

动作：agent 通过 `skill_manage` 工具自己写一个 SKILL.md 到 `~/.hermes/skills/`，下次类似场景可以通过 `/skill-name` 复用。

**"Self-improve during use" 不是 online learning**——它是 agent 在使用过程中 patch 已有 skill 文件（`patch` action 是推荐方式），本质还是"把成功的模式显式写进文件"。

### 2.3 Skills 的渐进式加载（progressive disclosure）

- Level 0：`skills_list()` 只返回元数据（~3k token）
- Level 1：`skill_view(name)` 加载完整内容
- Level 2：`skill_view(name, path)` 读取引用文件

这解决了**"skill 太多导致 SP 超长"** 的问题——不是全部加载，而是按需。

### 2.4 写入策略

- **主动写 MEMORY.md**：agent 发现值得记住的内容就直接写，不需要用户要求
- **立即落盘，下次 session 生效**：避免破坏当前 session 的 prefix cache
- **精确去重**：自动拒绝完全重复的条目
- **substring 匹配的 replace/remove**：安全更新

### 2.5 多平台部署

- 单个 agent 实例可以同时接入 CLI / Telegram / Discord / Slack / Signal / WhatsApp / Email
- 共享状态和对话连续性
- 部署选项：本地、VPS、Docker、serverless（Daytona/Modal 可休眠省成本）
- Provider 无关：`acp_adapter` 抽象 LLM 调用，支持 200+ 模型切换

## 3. 关键差异化

相对其他 agent 框架（LangChain / AutoGen / AutoGPT）：

| 维度 | 传统框架 | Hermes |
|---|---|---|
| Agent 生命周期 | 每次调用新实例 | 长期存活，跨 session 共享状态 |
| 学习机制 | 无内建 | skill 自动创建 + 自我 patch |
| 平台耦合 | 通常只在 CLI | 多平台单实例 |
| Provider 锁定 | 强 | `hermes model <provider:model>` 一行切换 |
| Memory 治理 | 外挂 RAG | 内建 MEMORY.md + FTS5 + Honcho |
| 部署形态 | 本地笔记本 | VPS / serverless，可休眠 |

## 4. 与 forge 的对比

这是最重要的部分。两者**目标有重叠但方法论差异巨大**。

### 4.1 共同点

- 都相信 agent 需要**长期、可积累、可演化的记忆**
- 都用**文件系统 + markdown** 作为主存储，避免 vector-only 黑盒
- 都认为**skill/procedural memory** 是比纯事实记忆更关键的资产
- 都有**预编译/准备好的知识**直接进 SP 的思路（Hermes 的 MEMORY.md + USER.md 在系统提示中，forge 的 section detail → SP → view）

### 4.2 核心差异

| 维度 | Hermes | forge |
|---|---|---|
| **写入门槛** | 低——agent 主动判断并写 | 高——必须经过 triage → PR → human review |
| **信任模型** | 信任 agent 的判断 | 不信任 agent，每次写入都要 review gate |
| **审计** | 靠 git log（MEMORY.md 是源文件）+ SQLite FTS | git PR workflow，diff + change-log |
| **冲突处理** | substring dedup + replace | 原地改写，triage 阶段分类（covered/new/conflict/narrow） |
| **回滚** | 手动编辑 MEMORY.md | `git revert` + 依赖图 rebuild |
| **传播** | 单层（写进 MEMORY.md 就生效） | 多层（source → section detail → SP → view） |
| **多 agent 统一** | 单 agent 多平台，一份 memory | 每个工具（CC / codex / claude.ai）独立 view，统一 source |
| **自动化程度** | 高——闭环自己跑 | 低——人是必经环节 |
| **冷启动** | 从零开始，边用边长 | 需要先人工填 user/about me 等基础 |
| **Skill 自创建** | agent 自己写 SKILL.md | 当前 MVP 不支持，skill 是人写的 |

### 4.3 哲学层的区别

- **Hermes = 自主 agent 哲学**：agent 应该像员工一样，越用越懂你，自己决定学什么、记什么。Nous Research 的整体方向就是 AGI-flavored autonomous agent。
- **forge = 受约束 agent 哲学**：agent 是能力强但不被信任的实习生，所有影响长期状态的改动都要人 review。把判断和执行分离。

用一个比喻：Hermes 像是给你雇了一个自学能力强的私人助理，他自己做笔记、自己总结经验；forge 像是给你建了一个知识管理系统，所有改动都要你签字。

## 5. 新的输入（forge 值得吸收的点）

这是这次调研最有价值的部分。

### 5.1 MEMORY.md 作为"快记"层（强建议考虑）

forge 目前只有**正式层**（section detail → SP → view），没有**快记层**。Hermes 的 MEMORY.md 填补的是"来不及走 PR，但值得马上记下来"的空间。

**可能的 forge 适配**：在 `assist/` 下新增 `memory.md`（或复用 `conversation memory/claude code memory/` 里 CC 已经写的 MEMORY.md）作为快记，triage 时从快记提升到正式层。**这其实就是当前的 cc_memory 事件类型在做的事**——可以把它看作 Hermes MEMORY.md 模型的具象化。

### 5.2 Progressive disclosure（强建议考虑）

Hermes 的 Level 0/1/2 加载机制非常值得借鉴。**forge 当前所有 fragment 都全量注入 SP**，随着 fragment 增多会遇到 token 压力。

可以引入：
- SP 只加载 fragment 的 header（name + description），~100 token per fragment
- agent 按需调用 `fragment_view(name)` 获取全文

这是一个**架构级的优化**，但需要 view 层支持按需加载（Claude Code 的 subagent / MCP 机制可以做到）。

### 5.3 Skill 作为 first-class citizen（建议考虑）

forge 当前的 `assist/section detail/` 只有三类：me / preference / project。没有 **procedural memory**——"做某类任务的标准流程"。

Hermes 的 skill 系统提供了一个模板：
- SKILL.md 格式：frontmatter + When to Use / Procedure / Pitfalls / Verification
- 通过 `/skill-name` 激活
- 支持子目录放脚本和资源

可以考虑在 `assist/skill/` 下加一层，作为第四类 fragment。

### 5.4 触发时机的显式化（建议借鉴）

Hermes 明确定义了"什么情况下该写记忆/创建 skill"：
- 5+ 工具调用的复杂任务
- 错误后找到方案
- 用户纠正之后
- 发现非平凡 workflow

forge 的 `operating-rule/events/conversation.md` 目前是模糊的"evaluate the conversation"。**可以把 Hermes 的触发条件直接抄进来作为具体指引**，降低 agent 的判断负担。

### 5.5 对 forge 的反向印证

- **不能自己 review 的 agent 不可信**：Hermes 主动写入的代价是不可审计的污染风险。forge 的 PR gate 是正确选择，不需要改
- **"一份 memory 多平台共享"**：Hermes 的模型。forge 通过"一份 source 多份 view"实现了类似效果，方向是对的
- **文件系统 + markdown 是主流共识**：不只是 Karpathy，Hermes 也是同样选择，验证了 forge 的存储决策

## 6. 不建议借鉴的点

- **agent 自主判断写入**：和 forge 哲学冲突，放弃 review gate 不划算
- **单 agent 多平台**：forge 的工具是 CC / codex / claude.ai，本来就多平台，目前靠各自 view 解决，不需要 Hermes 那种 gateway 抽象
- **自动 skill 创建**：在 forge 模型下，skill 创建应该是 PR 产物，不是 agent 主动的自动化

## 7. 一句话结论

**Hermes 和 forge 在"agent 需要长期记忆"这件事上达成共识，但在"谁来决定记什么"这件事上完全对立。** Hermes 是自主 agent 路线的代表，forge 是受约束 agent 路线的代表。两者不存在谁更对，服务的场景不同：Hermes 适合高频、快节奏、可容忍污染的个人助理场景；forge 适合低频、高标准、需要审计追溯的长期 OS 治理场景。

值得 forge 吸收的主要是三个战术级点：**快记层、progressive disclosure、skill 作为第四类 fragment**，都不冲突于 forge 的核心哲学。
