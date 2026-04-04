# Personal Memory System

`Personal Memory System` 是一个面向个人 AI assistant / agent 的 memory 研究与落地项目。

这个仓库的目标是沉淀一套适合个人场景的 memory 最佳实践：

- 调研截至 `2026-04-03` 的主流 memory 方案与官方实践
- 给出一套可解释、可审计、可演进的参考架构
- 提供一个本地优先、零依赖起步的开源参考实现
- 为后续接入 LLM、向量检索、图谱和个人数据源预留清晰扩展点

## 当前结论

基于官方文档、论文和社区实践，这个项目采用以下判断：

- `knowledge base` 是当前最适合作为 Phase 1 的基础层
- `Capture + Store + Projections` 是当前的核心架构
- 不把 memory 等同于向量库；memory 至少应拆成 `working/profile/semantic/episodic/procedural`
- memory 是一个持续循环：`capture -> consolidate -> project -> evolve`
- knowledge base 更像一个带语义约束的文件系统：可以先以树形目录为骨架，再逐步长出链接网络
- 写入分成 `hot path` 和 `background` 两条链路，不能所有记忆都阻塞主响应
- 对个人场景，`profile` 必须结构化且可编辑，不能只靠 embedding 检索
- `HOT/WARM/COLD` 是和 memory type 正交的第二层分类，用来决定哪些内容常驻、按需加载、归档
- 事件日志必须保留原始来源与时间语义，方便追溯、纠错和重建
- vector、graph、database 更适合作为 derived indexes
- 系统默认应是 `local-first`，用户可以查看、修改、删除自己的 memory

详细研究见：

- [docs/research/current-practices.md](docs/research/current-practices.md)
- [docs/research/community-operating-patterns.md](docs/research/community-operating-patterns.md)
- [docs/architecture/reference-architecture.md](docs/architecture/reference-architecture.md)
- [docs/architecture/platform-landing-review.md](docs/architecture/platform-landing-review.md)
- [docs/implementation/obsidian-kb-sop.md](docs/implementation/obsidian-kb-sop.md)
- [docs/implementation/roadmap.md](docs/implementation/roadmap.md)

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

当前仓库还是 private，而这个账号计划不支持 private repo 的 GitHub Pages。
所以现在这套 workflow 已经准备好了，但要等仓库改成 public，或者账号升级到支持 private Pages 的计划后，才能真正启用。

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

- 先明确 `kb/` 目录结构、节点类型和 frontmatter
- 明确 Obsidian-compatible vault schema 和使用 SOP
- 从 KB 直接做 create / update / link / archive
- 接入 inbox / daily / source reference
- 在 KB 之上做 organize / dream pipeline
- 再增加 evolve pipeline，把重复 lesson 提炼成 skills / commands / agents
- 最后再补 vector / graph / database enhancement 和评测

## 参考资料

- LangChain / LangGraph Memory Overview: <https://docs.langchain.com/oss/python/concepts/memory>
- Mem0 Add Memory: <https://docs.mem0.ai/core-concepts/memory-operations/add>
- Letta Stateful Agents: <https://docs.letta.com/guides/core-concepts/stateful-agents>
- MemGPT paper: <https://openreview.net/forum?id=0Kk142lP62>
- CoALA paper: <https://arxiv.org/abs/2309.02427>
- Graphiti: <https://github.com/getzep/graphiti>
