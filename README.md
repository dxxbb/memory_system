# forge

**forge** 是一个 Personal OS 的构建工具：把身份、偏好、知识这些原料在 `dxy_OS` 这样的个人 vault 里打造成预编译好的 system prompt 和 view。名字取自打铁的 forge —— 原料进、成品出，靠反复敲打收敛。

本仓库存放 forge 的设计文档和脚本；vault 是独立的 git repo。

## 当前方案

把个人 OS 做成一个 **build system**：所有变更都是 git diff，所有处理都走 PR，所有 view 都是预编译产物。

- Agent（Claude Code）是主调度者，定期 monitor OS（默认每天 1 次）
- 外层管线（watch.py / deps.py / approve.py）是确定性代码，内层判断由 agent + guideline 做
- 依赖关系声明在每个 derived 文件的 frontmatter 里（`kind:` / `upstream:`），`deps.py` 反向算传播
- PR 支持三种出口：approve、reject、request-changes（带 comment 多轮往返）
- `system/**` 是 control plane，只能由固定脚本和 agent 写
- vault 是独立 git repo，本仓库存放设计文档和脚本

## 文档索引

### 当前主方案

- [docs/design.md](docs/design.md) — **唯一设计文档**（整体运转机制 + MVP Week 1 落地 + Obsidian 前端约定）
- onepage — 见 vault `workspace/project/forge/onepage.md`（权威版本，不在本仓库）

### 研究资料

- [current-practices.md](docs/research/current-practices.md)
- [community-operating-patterns.md](docs/research/community-operating-patterns.md)
- [community-trends-2026.md](docs/research/community-trends-2026.md)
- [andrej-karpathy-llm-wiki.md](docs/research/andrej-karpathy-llm-wiki.md)
- [karpathy-thread-reactions.md](docs/research/karpathy-thread-reactions.md)
- [personal-ai-os-practitioners.md](docs/research/personal-ai-os-practitioners.md)

> 研究资料后续将整体迁往 vault 的 `knowledge base/`（待另一 PR 执行）。

### 归档（被取代但保留作历史参考）

- [docs/architecture/_archive/](docs/architecture/_archive/) — 旧架构与实施文档（personal-os-design, mvp-week1, platform-landing-review, roadmap, obsidian-kb-sop, reference-architecture, solution-design v1/v2, reframed-architecture, x-thread-ingest）
- [_archive/](_archive/) — 旧代码原型（JSON memory engine, tests, data, pyproject.toml, fetch_x_thread.py）
- [examples/_archive/](examples/_archive/) — 旧示例（phase1-kb-first）

## 仓库结构

```text
docs/
  design.md           单一设计文档（当前主方案）
  research/           调研文档（6 篇，待迁往 vault knowledge base/）
  architecture/_archive/   历史设计与实施文档归档
scripts/              工具脚本（站点生成；MVP 脚本待写）
site/                 可视化方案页
_archive/             归档的旧代码原型
examples/_archive/    归档的旧示例
```

## 可视化方案页

```bash
python3 scripts/build_site.py        # 重新生成 site/index.html
python3 -m http.server 8126 --bind 127.0.0.1 -d site   # 本地预览
```

GitHub Pages: <https://dxxbb.github.io/forge/>

## MVP 最小闭环

1. 一段真实对话 → 手工保存 transcript 到 `conversation memory/YYYY-MM-DD/`，git commit
2. 对 Claude Code 说 "monitor OS" → Agent 运行 `watch.py` → inbox 产一条 TODO
3. Agent 读 guideline → 评估对话 → 产一个 PR branch 改 `assist/sp/master.md`
4. 人 `git diff main...pr/0001` review → `python3 scripts/approve.py pr/0001`
5. `approve.py` 跑 `deps.py` → rebuild `assist/view/claude-code/CLAUDE.md` → squash merge 进 main
6. 新 Claude Code session 读到新版 `CLAUDE.md`

## 设计原则

- Local-first by default
- Git 是数据总线（commit = 事件，branch = PR，log = 审计，revert = 撤销）
- Agent 是主角，scripts 是工具
- 外层代码 + 内层 agent 的明确边界
- Review gate 防止 agent 污染主库
- 依赖图 + rebuild 保证下游一致性

## 参考资料

- LangChain / LangGraph Memory Overview: <https://docs.langchain.com/oss/python/concepts/memory>
- Mem0 Add Memory: <https://docs.mem0.ai/core-concepts/memory-operations/add>
- Letta Stateful Agents: <https://docs.letta.com/guides/core-concepts/stateful-agents>
- MemGPT paper: <https://openreview.net/forum?id=0Kk142lP62>
- CoALA paper: <https://arxiv.org/abs/2309.02427>
- Graphiti: <https://github.com/getzep/graphiti>
