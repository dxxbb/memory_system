# Personal Memory System

`Personal Memory System` 是一个面向个人 AI assistant / agent 的 memory 研究与落地项目。

这个仓库的目标是沉淀一套适合个人场景的 memory 最佳实践：

- 调研截至 `2026-04-03` 的主流 memory 方案与官方实践
- 给出一套可解释、可审计、可演进的参考架构
- 提供一个本地优先、零依赖起步的开源参考实现
- 为后续接入 LLM、向量检索、图谱和个人数据源预留清晰扩展点

## 当前结论

`2026-04-13` 更新：项目范围从"memory 子系统"扩展到"personal OS"。当前主方案把整个个人 OS 设计成一个 **build system**：

- 所有变更都是 git diff，所有处理都走 PR，所有 view 都是预编译产物
- 顶层按角色切分：`user/`(身份)、`workspace/`(活动)、`knowledge base/`(知识)、`assist/`(给 AI 用的投影)、`ingest src/` + `conversation memory/`(原材料)、`system/`(治理)
- 外层管线(watcher / dispatcher / deps / approve)是确定性代码，内层判断由 agent + guideline 做
- 依赖关系声明在每个 derived 文件的 frontmatter 里(`kind:` / `upstream:`)，`deps.py` 反向算传播
- PR 支持三种出口：approve、reject、request-changes(带 comment 多轮往返)
- `system/**` 是 control plane，只能由固定脚本和 system agent 写
- watcher 只扫 main，并跳过带 `Approved-by:` / `Rebuilt-by:` / `System-owned-by:` 的系统提交

前几版(`knowledge base` 优先 + `Capture / Workspace / Store / Projections` 四层)的核心判断仍然有效，但作为 personal OS 里的一个子系统(memory 层)落在 `knowledge base/` + `user/` + `workspace/` 里。

详细设计见：

**当前主方案**

- [docs/architecture/personal-os-design.md](docs/architecture/personal-os-design.md) —— `2026-04-13` 起的整体运转机制
- [docs/implementation/mvp-week1.md](docs/implementation/mvp-week1.md) —— Week 1 具体交付物和验收闭环

**前置设计(仍活跃)**

- [docs/architecture/solution-design-v2.md](docs/architecture/solution-design-v2.md) —— memory 子系统 Phase 1
- [docs/architecture/reframed-architecture.md](docs/architecture/reframed-architecture.md) —— 4 层语义切分的推理过程
- [docs/architecture/platform-landing-review.md](docs/architecture/platform-landing-review.md) —— 各 AI 平台的 landing 能力对比

**研究资料**

- [docs/research/current-practices.md](docs/research/current-practices.md)
- [docs/research/community-operating-patterns.md](docs/research/community-operating-patterns.md)
- [docs/research/community-trends-2026.md](docs/research/community-trends-2026.md)
- [docs/research/andrej-karpathy-llm-wiki.md](docs/research/andrej-karpathy-llm-wiki.md)
- [docs/research/karpathy-thread-reactions.md](docs/research/karpathy-thread-reactions.md)
- [docs/research/personal-ai-os-practitioners.md](docs/research/personal-ai-os-practitioners.md)

**实施文档**

- [docs/implementation/roadmap.md](docs/implementation/roadmap.md)
- [docs/implementation/obsidian-kb-sop.md](docs/implementation/obsidian-kb-sop.md)
- [docs/implementation/x-thread-ingest.md](docs/implementation/x-thread-ingest.md)

**归档**(被取代但保留作历史参考)

- [docs/architecture/_archive/](docs/architecture/_archive/)

## 可视化方案页

页面源码和生成结果在：

- [site/content.md](site/content.md)
- [site/diagrams/](site/diagrams/)
- [site/index.html](site/index.html)

本地预览：

```bash
python3 -m http.server 8126 --bind 127.0.0.1 -d site
```

然后打开：

```text
http://127.0.0.1:8126
```

GitHub Pages 发布后，页面地址会是：

```text
https://dxxbb.github.io/memory_system/
```

## 仓库结构

```text
docs/
  research/           当前实践调研
  architecture/       目标架构与设计决策
  implementation/     分阶段落地路线
site/                 可视化方案页与同源内容
scripts/              站点生成和开发脚本
src/memory_system/    参考实现
tests/                基础测试
data/                 本地开发数据目录
```

## 参考实现包含什么

当前实现是一个可运行的本地优先 memory engine：

- `ProfileState`：结构化用户画像
- `MemoryRecord`：统一的 memory 记录模型
- `MemoryTemperature`：`hot / warm / cold` 加载温度
- `JsonMemoryRepository`：JSON 文件持久化
- `MemoryService`：写入、检索、上下文选择
- `CLI`：seed / remember / profile / search / context

生产架构不建议长期停留在 JSON 文件层；演进方向见架构文档。

## 快速开始

```bash
PYTHONPATH=src python3 -m memory_system seed --user demo
PYTHONPATH=src python3 -m memory_system search --user demo --query "东京 出差"
PYTHONPATH=src python3 -m memory_system context --user demo --query "下周东京行程和偏好"
PYTHONPATH=src python3 -m memory_system remember --user demo --content "默认回答保持简洁直接" --kind preference --tier semantic --source manual --temperature hot
```

运行测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

生成可视化方案页：

```bash
python3 scripts/build_site.py
```

这会根据：

- `site/content.md`
- `site/diagrams/*.json`

重新生成：

- `site/index.html`

## 设计原则

- Local-first by default
- Inspectable and editable memory
- Layered memory instead of single-store memory
- Separate memory type from serving temperature
- Event-sourced ingestion with provenance
- Consolidate raw sessions into a stable store
- Evolve repeated lessons into reusable skills and procedures
- Hybrid retrieval instead of vector-only retrieval
- Explicit privacy, retention, and deletion controls

## 下一步

当前重点是跑通 personal OS 的 Week 1 MVP，详见 [docs/implementation/mvp-week1.md](docs/implementation/mvp-week1.md)。

MVP 的最小闭环：

1. 一段真实对话 → 手工保存 transcript 到 `conversation memory/YYYY-MM-DD/`，git commit
2. `scripts/watch.py` 扫 git diff → inbox 产一条 TODO
3. `scripts/dispatch.py` 启动 Claude Code → agent 按 `events/conversation.md` 评估对话 → 产一个 PR branch 改 `assist/sp/master.md`
4. 人 `git diff main...pr/0001` review → `scripts/approve.py pr/0001`
5. `approve.py` 跑 `deps.py` → rebuild `assist/view/claude-code/CLAUDE.md` → squash merge 进 main
6. 新 Claude Code session 读到新版 `CLAUDE.md`

跑通后的 Phase 2 优先级：

- 加第二个 event 类型(`daily_memo` 或 `ingest`)
- 加 `workspace/` 相关事件处理
- 加自动化 watcher(launchd / cron)
- 加组合式 SP(master + role overlay)
- 加 preference 完整闭环
- 加 fact staleness 机制

## 参考资料

- LangChain / LangGraph Memory Overview: <https://docs.langchain.com/oss/python/concepts/memory>
- Mem0 Add Memory: <https://docs.mem0.ai/core-concepts/memory-operations/add>
- Letta Stateful Agents: <https://docs.letta.com/guides/core-concepts/stateful-agents>
- MemGPT paper: <https://openreview.net/forum?id=0Kk142lP62>
- CoALA paper: <https://arxiv.org/abs/2309.02427>
- Graphiti: <https://github.com/getzep/graphiti>
