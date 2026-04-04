# Obsidian KB SOP

## 目的

这份文档定义：

- 如果把 Obsidian 作为 knowledge base 前端，应该怎么组织 vault
- 用户日常如何使用
- agent / 系统后续应如何在这个基础上工作

目标不是把所有事情都交给 Obsidian，而是把它作为：

- `human-facing knowledge base frontend`

## 基本原则

1. 用户读写的是 Markdown knowledge nodes。
2. 目录树优先，链接增强其次。
3. 文件名面向人类，`id` 面向机器。
4. 原始输入先进入 `inbox/` 或 `daily/`，不要直接覆盖稳定节点。
5. consolidate / evolve 的产物最终仍应落回 vault。

边界补充：

- `daily/` 是按天记录的人类工作台
- `inbox/` 是待整理的原始输入池
- 大体量 raw imports 应优先放在 vault 外
- `_system/` 不是用户主要编辑区

## 推荐 vault 结构

```text
kb/
  profile/
    user.md
  inbox/
  daily/
  topics/
  people/
  projects/
  domains/
  procedures/
  decisions/
  lessons/
  archive/
  _system/
```

目录职责：

- `profile/`: 全局稳定画像
- `inbox/`: 尚未整理的输入
- `daily/`: 每日捕获和工作记录
- `topics/`: 长期主题知识
- `people/`: 重要人物
- `projects/`: 项目长期上下文
- `domains/`: 领域长期知识
- `procedures/`: 稳定可复用流程
- `decisions/`: 重要决策
- `lessons/`: 教训、纠偏、经验
- `archive/`: 低活跃长期保留
- `_system/`: 模板、迁移、内部弱可见状态

推荐放在 vault 外的内容：

- `.kb-raw/`: 原始导入
- `.kb-indexes/`: 派生索引

## Note 模板

推荐所有长期节点都使用统一 frontmatter。

```yaml
---
id: kb-topic-memory-architecture-001
kind: topic
title: Memory Architecture
status: active
temperature: warm
tags:
  - memory
  - architecture
aliases: []
created_at: 2026-04-03
updated_at: 2026-04-03
source_refs: []
links: []
---
```

字段解释：

- `id`: 稳定 identity，不随文件重命名变化
- `kind`: 节点类型
- `title`: 人类标题
- `status`: `active / archived / invalid`
- `temperature`: `hot / warm / cold`
- `tags`: 辅助检索
- `aliases`: 重命名兼容
- `source_refs`: 来源
- `links`: 结构化链接列表

## 节点命名规范

建议：

- 文件名短、清晰、可读
- 标题与文件名大体一致
- 不把 UUID 放进文件名

示例：

- `topics/memory-architecture.md`
- `projects/personal-memory-system.md`
- `procedures/weekly-review.md`

## 日常使用 SOP

## 1. 新信息进入系统

默认规则：

- 零散内容先写 `inbox/`
- 当天工作流、会议、观察写 `daily/`
- 已经非常稳定的长期结论才直接写入目标节点
- 大体量导入不要一条条变成普通 note

作用区别：

- `daily/` 用来保留“今天发生了什么”
- `inbox/` 用来收纳“还没决定放哪的东西”
- `.kb-raw/` 用来保存原始导出，不直接暴露给日常知识视图

适用场景：

- 聊天中的新偏好
- 笔记里的碎片观察
- 一次临时决策
- 一段待确认结论

## 2. 写入稳定知识节点

只有在满足以下条件时，才直接写入 `topics/`、`projects/`、`procedures/` 等长期节点：

- 内容已经足够稳定
- 来源明确
- 不只是一次性上下文
- 后续大概率会再次复用

常见例子：

- 用户长期偏好
- 项目核心架构结论
- 稳定流程
- 重复出现的纠错规则

## 3. 建立链接

建议在写长期节点时至少做一层轻链接：

- topic -> project
- topic -> person
- lesson -> procedure
- decision -> related project

Phase 1 不要求全量强互链，但要求：

- 关键节点之间能跳转
- agent 能据此做范围召回

## 4. 每日流程

建议每天做一次轻量整理：

1. 打开当天 `daily/`
2. 把零散输入记入 `inbox/` 或 `daily/`
3. 标记哪些内容值得进入长期节点
4. 如已明确，补一个链接到相关 topic / project

目标：

- 不丢信息
- 不强迫当天就全部整理完

## 5. 每周整理

建议每周做一次 consolidate：

1. 清空或减少 `inbox/`
2. 把重复 observations 合并进 topic / project / procedure
3. 把相对日期改成绝对日期
4. 删除或标记已失效结论
5. 调整 `temperature`
6. 归档低活跃内容

这一步是 knowledge base 质量的关键，不建议长期跳过。

## 6. 月度回顾

建议每月做一次 evolve：

1. 看哪些 lessons 反复出现
2. 看哪些 procedures 已经稳定
3. 看哪些 project / domain 节点结构需要重组
4. 把高频经验提升为 procedure 或 profile constraint 候选

## Agent / 系统 SOP

## 1. 读取顺序

agent 默认按以下顺序读取：

1. `profile/user.md`
2. `procedures/` 中的 `hot` 节点
3. 当前 project / domain 相关节点
4. 相关 topics
5. 必要时再补最近 daily / lesson 片段

## 2. 写入顺序

agent 默认按以下顺序写入：

1. 新观察先写 `inbox/` 或 `daily/`
2. 明确的长期偏好可更新 `profile/`
3. 明确稳定流程可写 `procedures/`
4. 不确定内容不要直接覆盖长期节点

## 3. 移动与重命名

规则：

- 允许重命名文件
- 允许移动目录
- 必须保留 `id`
- 如有必要补 `aliases`

不要把“路径变化”视为“新知识对象”。

## 4. 归档

当节点满足以下条件时，可以归档：

- 长期低活跃
- 不再需要默认加载
- 仍保留追溯价值

归档动作：

- 移入 `archive/`
- `status` 改为 `archived`
- `temperature` 改为 `cold`

## 5. 不建议的用法

- 把所有聊天原文直接堆进 topic 节点
- 把 `daily/` 直接当长期知识库
- 让机器索引文件充斥主要目录
- 把文件名当唯一 identity
- 每次小改都新建一个重复 topic

## Phase 1 的最小可用 SOP

如果要用最小方式启动，建议只做以下动作：

1. 建好 vault 目录结构
2. 建立 `profile/user.md`
3. 每天把碎片写进 `daily/` 或 `inbox/`
4. 每周把稳定内容合并到 `topics/` / `projects/` / `procedures/`
5. 只维护少量 `hot` 节点供 agent 默认读取

这已经足够支撑后面的 consolidate 和 evolve。
