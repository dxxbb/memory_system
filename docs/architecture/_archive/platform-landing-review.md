# Platform Landing Review

更新时间：`2026-04-03`

这篇只回答一个问题：

- 这套 KB 方案，具体怎么落到 OpenClaw、Claude Code、Codex、ChatGPT 上？

不再讲抽象层级，只讲 3 件事：

1. 平台自己会读哪些文件
2. 我们的 KB 该映射到哪
3. 实际要改哪些文件

## 1. 先说结论

四个平台不是一种结构。

- OpenClaw：workspace 本身就是 agent 的 home 和 memory，最接近“文件就是 memory”
- Claude Code：核心是 `CLAUDE.md` 体系，分 user memory 和 project memory，还支持 imports 和 hooks
- Codex：核心是 `AGENTS.md` 两层作用域、`config.toml` 和 MCP
- ChatGPT：核心是 project files / instructions / saved memory / project memory，不是文件系统产品

所以这套方案的落地方式应该是：

- OpenClaw：同步 projection 到 agent workspace
- Claude Code：同步 projection 到 `~/.claude/CLAUDE.md` 和 repo `CLAUDE.md` 体系
- Codex：同步 projection 到它会自动发现的 `AGENTS.md` 和 `config.toml`
- ChatGPT：生成 project summary，再由用户送达

## 2. OpenClaw

参考：

- [Agent workspace](https://docs.openclaw.ai/agent-workspace)
- [agents](https://docs.openclaw.ai/cli/agents)
- [memory](https://docs.openclaw.ai/zh-CN/cli/memory)

### OpenClaw 自己会读什么

OpenClaw 的工作单元是一个 agent workspace。

workspace 里常见的文件就是：

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `MEMORY.md`
- `memory/YYYY-MM-DD.md`

另外它还有 memory tools，可以搜和读 memory 文件。

这意味着：

- OpenClaw 本身就是文件型 agent
- memory 放进 workspace 就能被它消费

### 我们的 KB 怎么映射

推荐映射：

- 个人或 agent 的长期结论 -> `MEMORY.md`
- 当天的记录和纠正 -> `memory/YYYY-MM-DD.md`
- agent 角色、做事方式 -> `AGENTS.md` / `SOUL.md` / `USER.md`

在 OpenClaw 这一侧，最简单的落地不是再发明新结构，而是把 projection 直接同步进 workspace。

### 实际要改哪些文件

假设今天新增两条信息：

- `文档少用抽象句式，每节保留 1 个例子。`
- `这个项目 Phase 1 先做 knowledge base。`

当天会改：

- `workspace/MEMORY.md`
- `workspace/memory/2026-04-03.md`

最小例子：

`workspace/MEMORY.md`

```md
- 当前项目 Phase 1 先做 knowledge base
- 目录树是骨架，链接是增强层
```

`workspace/memory/2026-04-03.md`

```md
- 文档少用抽象句式，每节保留 1 个例子
```

### 结论

OpenClaw 最简单。

对 OpenClaw 来说，platform landing 基本就是：

- 把 projection 写进 workspace

## 3. Claude Code

参考：

- [Manage Claude's memory](https://docs.anthropic.com/en/docs/claude-code/memory)
- [Hooks](https://code.claude.com/docs/en/hooks)

### Claude Code 自己会读什么

Claude Code 有明确的 memory 文件体系。

官方文档里最重要的三个位置是：

- `~/.claude/CLAUDE.md`
  用户级 memory，跨项目生效
- `./CLAUDE.md`
  项目级 memory，当前 repo 生效
- `@import`
  可以把额外文件引入 `CLAUDE.md`

另外：

- Claude Code 会递归读取当前目录向上的 `CLAUDE.md`
- 还支持 hooks，在特定时机加 `additionalContext`
- 可以用 `/memory` 看当前加载了哪些 memory 文件

所以 Claude Code 的关系不是“一个 memory.md”，而是：

- user memory
- project memory
- imported files
- hooks 追加上下文

### 我们的 KB 怎么映射

这里不能把个人 KB 全塞进 repo 的 `CLAUDE.md`。

正确映射应该是：

- 个人稳定偏好 -> `~/.claude/CLAUDE.md`
- 项目共享规则 -> `./CLAUDE.md`
- 生成的项目 memory slice -> `./.claude/generated/project-memory.md`
- 当天临时纠正 -> hook 的 `additionalContext` 或直接更新对应的 memory 文件

也就是说，Claude Code 不是“再造一个新文件系统”，而是：

- 用它自己的 memory hierarchy
- 把我们 KB 里的内容同步到这几个位置

### 实际要改哪些文件

假设今天新增两条信息：

- `文档少用抽象句式，每节保留 1 个例子。`
- `这个项目 Phase 1 先做 knowledge base。`

推荐改这三个文件：

1. `~/.claude/CLAUDE.md`
2. `./CLAUDE.md`
3. `./.claude/generated/project-memory.md`

关系是这样的：

`~/.claude/CLAUDE.md`

```md
- 文档尽量简单直接
- 每节保留 1 个例子
```

`./CLAUDE.md`

```md
# Project Memory

@.claude/generated/project-memory.md

- 这里保留项目共享规则，不放个人全量偏好
```

`./.claude/generated/project-memory.md`

```md
- 当前决策：Phase 1 先做 knowledge base
- 当前架构结论：目录树是骨架，链接是增强层
```

### hooks 在这里做什么

hooks 不是主存储。

在 Claude Code 里，hooks 最适合做两件事：

- 把当天新纠正临时加进本次会话
- 把会话里确认的新信息写回 `daily/` 或 `inbox/`

它不适合承担：

- 个人主库
- 项目长期 memory 主文件

### 结论

Claude Code 的关键不是“再做一个 `memory.md`”，而是把关系理清楚：

- `~/.claude/CLAUDE.md` 管个人长期偏好
- `./CLAUDE.md` 管当前项目共享规则
- `./.claude/generated/project-memory.md` 放项目 projection
- hooks 只做临时补充和 capture

## 4. Codex

参考：

- [Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Docs MCP](https://platform.openai.com/docs/docs-mcp)
- [MCP docs](https://developers.openai.com/api/docs/mcp)
- [Agent internet access](https://platform.openai.com/docs/codex/agent-network)

### 先说清楚 `AGENTS.md` 是什么

Codex 官方现在已经把这点写得比较明确了。

Codex 会在开始工作前读取 `AGENTS.md` 文件，而且是分两层：

1. `global scope`
   在 Codex home 目录里读取：
   `~/.codex/AGENTS.override.md`
   或
   `~/.codex/AGENTS.md`
2. `project scope`
   从项目根目录开始，沿着目录一路走到当前工作目录
   每一级都检查：
   `AGENTS.override.md`
   `AGENTS.md`
   以及 `project_doc_fallback_filenames` 里配置的备选文件名

官方还明确写了：

- global scope 只用 home 目录里第一个非空文件
- project scope 每个目录最多读取一个文件
- `CODEX_HOME` 可以改变 home 目录
- 指令总大小受 `project_doc_max_bytes` 限制，默认 `32 KiB`

所以这里的正确结论是：

- Codex 有个人域 `AGENTS.md`
- Codex 也有项目域 `AGENTS.md`
- 它不是我之前说的“只有项目域”

### Codex 自己会读什么

目前能明确依赖的是：

- `~/.codex/AGENTS.md` 或 `~/.codex/AGENTS.override.md`
- repo 根目录和子目录里的 `AGENTS.md` / `AGENTS.override.md`
- `~/.codex/config.toml` 里的 MCP 和项目指令配置
- 当前任务运行环境

这说明 Codex 的 memory / instructions 结构更接近：

- 个人级 AGENTS
- 项目级 AGENTS
- 子目录 override
- MCP 作为外部知识入口

### 我们的 KB 怎么映射

对 Codex，推荐映射是：

- 个人稳定偏好 -> `~/.codex/AGENTS.md`
- 项目级规则和当前项目结论 -> repo 根目录 `AGENTS.md`
- 子目录特有规则 -> 子目录下的 `AGENTS.override.md`
- repo 外的个人 KB -> 通过 `~/.codex/config.toml` 里配置的 MCP 提供只读访问
- cloud task 所需内容 -> 必须进 repo 或 MCP，不能假设能读你本地 vault

所以对 Codex，不能再把它理解成“只有一个 repo 里的 `AGENTS.md`”。

正确做法是：

- `~/.codex/AGENTS.md` 放跨项目工作习惯
- `<repo-root>/AGENTS.md` 放项目规则和当前项目结论
- 必要时在子目录放 `AGENTS.override.md`
- repo 外的长期 KB 通过 MCP 提供

### 实际要改哪些文件

推荐改这三个地方：

1. `~/.codex/AGENTS.md`
2. `<repo-root>/AGENTS.md`
3. `~/.codex/config.toml`

关系是这样的：

`~/.codex/AGENTS.md`

```md
- 默认先读测试和 lint 规则
- 修改文档时保持简单直接
```

`<repo-root>/AGENTS.md`

```md
- 当前决策：Phase 1 先做 knowledge base
- 当前写作要求：每节保留 1 个例子
- 当前架构结论：目录树是骨架，链接是增强层
- 需要 repo 外笔记时，使用 `personal_kb` MCP
```

`~/.codex/config.toml`

```toml
[mcp_servers.personal_kb]
command = "kb-server"
args = ["serve", "--root", "/path/to/kb"]
```

### 目录关系

Codex 这边我建议固定成这样：

- 个人域：
  `~/.codex/AGENTS.md`
- 项目域：
  `<repo-root>/AGENTS.md`
- 子目录域：
  `<repo-root>/<subdir>/AGENTS.override.md`
- 个人机器配置域：
  `~/.codex/config.toml`

也就是说：

- `~/.codex/AGENTS.md` 是个人级指导
- `<repo-root>/AGENTS.md` 是项目级指导
- 子目录的 `AGENTS.override.md` 会覆盖更上层规则
- `~/.codex/config.toml` 才是个人目录下的全局配置

这里再补一条硬规则：

- Codex 官方文档写的是自动发现 `AGENTS.md` / `AGENTS.override.md` 和配置过的 fallback filename
- 官方文档没有写 `AGENTS.md` 支持像 Claude Code 那样的导入层
- 所以生成器如果产出摘要，最后也得写进这些可发现文件，而不是只放在 `projections/codex/*.md`

### local 和 cloud 的区别

Codex local：

- 会加载 global 和 project 两层 `AGENTS.md`
- 可以直接读 repo 文件
- 可以用本地 MCP
- 可以当天改 `~/.codex/AGENTS.md` 或 repo `AGENTS.md`

Codex cloud：

- 任务跑在 sandbox 里
- 只能用任务里可见的 repo 快照和允许的网络 / MCP
- 不能假设它看得到你本地 `~/.codex/AGENTS.md` 或本地磁盘上的 KB

所以 cloud 版要成立，必须满足下面二选一：

- 需要的项目 guidance 已经进 repo
- 需要的 memory 通过 MCP 或网络接口可读

### 结论

Codex 的关键不是复制 Claude Code 的 `CLAUDE.md` 体系，而是按它自己的官方结构来：

- `~/.codex/AGENTS.md` 管个人工作习惯
- `<repo-root>/AGENTS.md` 管项目规则和当前结论
- `AGENTS.override.md` 管子目录覆盖
- `~/.codex/config.toml` 管 MCP 和 discovery 配置
- repo 外的长期 KB 通过 MCP 提供
- 生成出来的摘要要同步进这些正式入口，不能只停在 `projections/`

## 5. ChatGPT

参考：

- [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt)
- [Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)
- [What is Memory?](https://help.openai.com/en/articles/8983136-what-is-memory%3F.midi)

### ChatGPT 自己会读什么

ChatGPT 当前可依赖的是：

- project instructions
- project files
- saved memory
- project memory

普通聊天不会自动读取你本地的 `kb/` 目录。

### 我们的 KB 怎么映射

对 ChatGPT，最稳的做法只有一个：

- 把本地 KB 导出成 `project-summary.md`
- 由用户放进 project files 或 project instructions

### 实际要改哪些文件

本地只需要生成：

- `projections/chatgpt/project-summary.md`

并记录：

```yaml
generated_at: 2026-04-03
delivery_status: pending
```

### 结论

ChatGPT 在这套系统里的角色很明确：

- 它是 consumer
- 不是主库
- 也不是 same-day correction runtime

## 6. 一个统一的 projection 规则

这套方案真正要落地，projection 规则必须统一。

### 先更新 Capture / Store

先改：

- `kb/profile/*.md`
- `kb/projects/*.md`
- `kb/decisions/*.md`
- `kb/topics/*.md`
- `kb/procedures/*.md`
- `kb/daily/*.md`
- `kb/inbox/*.md`

### 再刷新 projections

生成：

- `projections/openclaw/MEMORY.md`
- `projections/claude/CLAUDE.memory.md`
- `projections/chatgpt/project-summary.md`

### 最后同步到平台

- OpenClaw：同步到 workspace
- Claude Code：同步到 `~/.claude/CLAUDE.md` / repo `CLAUDE.md` / generated import file
- Codex：同步到 `~/.codex/AGENTS.md` / repo `AGENTS.md` / `~/.codex/config.toml` 或项目级 `.codex/config.toml`
- ChatGPT：用户手工送达

## 7. 这篇文档对应的真实例子

真实例子在：

- `examples/phase1-kb-first/`

建议配合这几个文件一起看：

- `examples/phase1-kb-first/kb/profile/user.md`
- `examples/phase1-kb-first/kb/projects/personal-memory-system.md`
- `examples/phase1-kb-first/kb/decisions/phase-1-kb-first.md`
- `examples/phase1-kb-first/projections/claude/CLAUDE.memory.md`
- `examples/phase1-kb-first/codex-home/AGENTS.md`
- `examples/phase1-kb-first/codex-repo/AGENTS.md`
- `examples/phase1-kb-first/projections/chatgpt/project-summary.md`

## 8. 最后的判断

这套设计到 Phase 1 为止，可以明确落地成下面这件事：

- 本地维护一份平台无关的 KB
- OpenClaw 用 workspace projection
- Claude Code 用 `~/.claude/CLAUDE.md + ./CLAUDE.md + imported generated file`
- Codex 用 `~/.codex/AGENTS.md + repo AGENTS.md + MCP`
- ChatGPT 用 project summary export

这就是当前最稳的落地方式。
