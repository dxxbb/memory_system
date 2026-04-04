# Current Practices in Personal Long Memory

更新时间：`2026-04-03`

这份文档只讨论 `personal long memory`。

这里的 `long memory` 指跨 session、跨线程、跨时间持续存在，并能被后续 agent 反复使用、整理、纠错和演化的 memory asset。

不在本文重点内的内容：

- thread state
- 临时上下文拼接
- 会话级 scratchpad
- 短时 working memory 本身的实现细节

社区工作流另见 [community-operating-patterns.md](community-operating-patterns.md)。

## 结论先行

截至 `2026-04-03`，个人 long memory 的主流实践可以概括为：

1. long memory 不是聊天历史存档，而是可持续服务 agent 的长期资产。
2. long memory 不能只做成 vector store，至少要同时包含 `profile` 和可增长的 memory collection。
3. long memory 需要区分 `facts`、`episodes`、`procedures`，而不是把所有内容混成同一种记忆。
4. 写入 long memory 不能只是 append，通常需要 `extract -> dedupe -> conflict-resolve -> store`。
5. long memory 的主链路不是只有 `save/use`，还必须有 `organize/consolidate`，更进一步还会有 `evolve`。
6. context serving 应该按活跃度和稳定性分层，而不是每次把全部历史塞进 prompt。
7. graph、vector、knowledge base 都更适合作为增强层或投影层，而不是唯一真相源。

## 为什么这里只轻提 short memory

这个项目的主体是 `long memory`，不是 short memory。

但 short memory 仍然要被提一下，因为它只负责一件事：定义边界。

它的意义不是让我们去设计 thread memory，而是帮我们明确：

- 哪些内容只应该停留在 session 内
- 哪些内容值得从 session 抽取到 long memory
- long memory 之后怎样重新注入 agent 上下文

所以在本项目里，short memory 只是：

- long memory 的上游输入来源之一
- long memory 的下游服务位置之一

不是研究中心。

## 1. Long memory 的核心对象是 cross-session user memory

LangGraph 官方文档虽然从 thread memory 讲起，但真正对这个项目有价值的是它明确区分了：

- thread-scoped state
- cross-session long-term memory

这个区分的意义在于：

- session 记录本身不能替代长期画像
- 单线程上下文不能承担长期偏好和长期知识
- long memory 必须有独立于线程的持久化存储

对个人场景，真正要建设的是后者，也就是：

- 用户长期偏好
- 长期目标和约束
- 历史事件和项目状态
- 长期可复用的行为规则

来源：

- <https://docs.langchain.com/oss/python/concepts/memory>

## 2. Long memory 已经不是单一存储，而是 profile + collection

LangGraph 对长期 memory 的拆分里，最有价值的不是 taxonomy 本身，而是它给出了两种长期语义记忆形态：

- 持续更新的 `profile`
- 持续增长并可更新的 `collection`

同时它把长期 memory 进一步拆成：

- `semantic memory`
- `episodic memory`
- `procedural memory`

CoALA 论文也支持这种模块化拆分，而不是一个大一统 memory bucket。

这对个人 long memory 的直接含义是：

- `profile` 必须单独建模，并允许人工编辑
- `facts` 不应该和 `episodes` 混在一起
- `procedures` 应单独作为“以后怎么做”的长期资产

来源：

- <https://docs.langchain.com/oss/python/concepts/memory>
- <https://arxiv.org/abs/2309.02427>

## 3. Active core 和 archival long memory 需要分层服务

Letta 和 MemGPT 都支持一个很重要的长期记忆模式：

- 少量高价值 memory 需要靠近上下文窗口
- 大量历史 memory 保存在外部存储，需要时再召回

这件事对个人 long memory 很关键，因为长期资产本身也有活跃度差异：

- 有些是强稳定偏好，应该常驻
- 有些是近期项目事实，应按需加载
- 有些是历史 archive，只在追溯时使用

因此，long memory 的核心问题不只是“存在哪”，还包括“怎样服务”。

这也是为什么社区里会自然出现：

- core memory
- topic memory
- archive
- `HOT / WARM / COLD`

这类分层模型。

来源：

- <https://docs.letta.com/guides/core-concepts/stateful-agents>
- <https://openreview.net/forum?id=0Kk142lP62>

## 4. Long memory 写入已经演化成抽取、去重和冲突处理

Mem0 官方文档最值得吸收的不是某个 API，而是它隐含的写入观：

- 先抽取 memory
- 再处理重复和冲突
- 最后存储

这说明 long memory 的写入目标不是“什么都存”，而是：

- 判断值不值得成为长期资产
- 判断应更新旧事实还是新增一条 episode
- 判断是否需要纠错或失效旧内容

个人 long memory 如果没有这一层，就很容易退化成：

- 低质量日志堆积
- 自相矛盾
- 历史污染
- 越用越不可信

来源：

- <https://docs.mem0.ai/core-concepts/memory-operations/add>

## 5. Long memory 需要 organize / consolidate，而不只是 retrieve

官方资料更强调 `save` 和 `use`，但真正进入个人长期使用后，问题会迅速转向：

- 原始 session 怎么整理成稳定知识
- 相对日期怎么变成绝对日期
- 被证伪的旧事实怎么失效
- 分散 observations 怎么合并成 topic memory

这也是为什么社区里会出现：

- dream
- consolidate
- prune
- re-index
- topic files

这类后台流程。

对本项目，这一结论很关键：

- raw event 不是最终 long memory
- long memory 需要后台整理和重建能力
- `knowledge base` 更适合作为 long memory 的投影，而不是本体

详细见：

- [community-operating-patterns.md](community-operating-patterns.md)

## 6. Long memory 还会继续 evolve 成 procedures / skills

个人场景里，长期资产不只包括“知道什么”，还包括“以后怎么做”。

社区实践已经明显走向这一步：

- 从 repeated corrections 里抽 lesson
- 从 lesson 中形成 trigger-action 规则
- 再进一步合成为可复用 skill / command / agent

这意味着：

- `procedural memory` 不能被视为附属品
- 自我改进不应该只靠 prompt 手搓
- long memory 的终点之一是沉淀成稳定能力

所以这个项目后续不仅要做 retrieval，也要做：

- lesson extraction
- instinct formation
- skill synthesis

## 7. Graph 和 knowledge base 都是增强层，不是唯一真相源

Graphiti 这类方案说明，图结构对 long memory 很有帮助，尤其是在：

- 动态关系
- 时间有效性
- 多实体关联
- episode 到 fact 的追溯

但图谱更像是 projection / enhancement layer，而不是唯一 canonical store。

同理，Obsidian、Markdown topic files、`MEMORY.md` 这类知识库形态也很有价值，但它们更适合作为：

- 用户可读写界面
- topic projection
- 长期知识视图

而不是唯一真相源。

一个更稳的 personal long memory 结构通常是：

- canonical event / memory store
- structured profile
- optional vector / graph index
- file / markdown knowledge projections

来源：

- <https://github.com/getzep/graphiti>

## 对本项目的含义

基于这些实践，这个项目的研究和实现应该明确聚焦：

- long memory asset，而不是 thread memory
- profile、facts、episodes、procedures 的长期管理
- consolidate / dream / project / evolve 这些后台能力
- hot / warm / cold 这类 serving policy
- projection 和 canonical store 的关系

换句话说，这个项目真正要做的不是：

- “怎么把聊天存下来”

而是：

- “怎么把个人长期信息沉淀成可持续使用、可整理、可演化的 memory asset”

## 不建议的路线

- 把 long memory 等同于聊天历史归档
- 只存 embedding，不保留结构化 profile
- 只有 summary，没有原始来源和失效机制
- 没有 consolidate，长期依赖原始 session 直接检索
- 把 knowledge base 或图谱当唯一真相源
- 不区分稳定偏好、事件记忆和行为规则
