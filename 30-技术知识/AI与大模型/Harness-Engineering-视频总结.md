---
status: draft
updated: 2026-05-13
confidence: medium
source_type: bilibili_video
content: full
sources:
  - "[[80-raw-原始资料/Cubox/技术/AI/Harness Engineering 到底是什么？概念、实战与争议，一次全部讲清楚-2026-05-06]]"
  - "[[80-raw-原始资料/Cubox/技术/AI/对谈楼天城：AI是匹脱缰野马，Harness是这个时代最关键的能力_哔哩哔哩_bilibili-2026-05-06]]"
  - "80-raw-原始资料/Cubox/技术/AI/extracted/BV12LR1B3EUt/BV12LR1B3EUt_transcript.txt"
  - "80-raw-原始资料/Cubox/技术/AI/extracted/LHzkk0n/BV15CRsBaEfg_p1_transcript.txt"
---

# Harness Engineering 视频总结

本页基于两条 B 站视频的 metadata 与机器转写稿整理。ASR 中存在明显错词，专有名词、文章名和数字仍需二次核验。

## 一句话结论

Harness Engineering 可以先理解为：围绕大模型搭建一整套让 Agent 稳定工作的外部系统，包括上下文组织、工具、权限、运行环境、验证反馈、任务拆解、评估器和长期维护机制。它不是全新的底层技术，但它把一批已有工程方法组织成了适合 Agent 时代的系统框架。

## 概念边界

视频给出的核心公式是：

`Agent = Model + Harness`

换句话说，把模型本体拿掉以后，剩下用于控制、约束、赋能、验证模型行为的部分，都可以视为 Harness。

它和 Prompt Engineering、Context Engineering 的关系是递进的：

| 层级 | 关注点 | 典型问题 |
|---|---|---|
| Prompt Engineering | 怎么问 | 指令是否清楚、约束是否明确 |
| Context Engineering | 给什么信息 | 何时放入哪些文件、历史、工具列表 |
| Harness Engineering | 怎么搭系统 | Agent 如何规划、执行、验证、迭代、恢复 |

## 工程实践

视频中把 OpenAI 的实践概括为三类：

- 上下文管理：不要把所有规则塞进一个巨大说明文件，而是保留一个短入口，再让 Agent 按任务读取分层文档。重要决策要进入仓库，仓库成为事实来源。
- 验证与反馈：给 Codex 类 Agent 接入浏览器、截图、DOM 检查、日志、指标、lint 和测试，使它能在任务中自证结果。
- 技术债清理：让后台 Agent 周期性扫描代码和文档，发现过时、重复、违规或与实现不一致的内容，并提交修复。

Anthropic 的实践则更像多 Agent 流程设计：

- Planner：把模糊需求拆成清晰功能列表。
- Generator：按功能点实现。
- Evaluator：作为独立第三方评估产出，避免生成者自评偏差。

这套流程效果更好，但成本更高。视频中提到的对比是：单 Agent 模式耗时约 20 分钟、成本约 9 美元；多 Harness 流程耗时约 6 小时、成本约 200 美元。该数字来自视频转写，需核验原文。

## 争议

支持方认为，Harness Engineering 的价值在于它把模型能力转化为稳定生产力。今天模型仍会犯错、偏航、遗漏上下文，因此谁能设计更稳的 Harness，谁就更早获得可用的 AI 生产力。

质疑方认为，这只是旧工程方法的新包装：lint、测试、任务拆解、评估器、工具权限这些都不是新东西。随着模型能力增强，一部分 Harness 可能会被模型本身吸收。

更稳妥的判断是：Harness Engineering 不是噱头，但也未必是终局。它是当前模型能力尚不稳定阶段的关键过渡工程。

## 楼天城访谈中的 Harness 视角

楼天城访谈不是纯 Harness 教程，而是从自动驾驶和世界模型角度讨论类似问题。可迁移出的观点是：

- 当 AI 能力超过普通人类时，继续依赖人类数据和人类判断会遇到上限。
- 世界模型 1.0 更像训练范式变化，重点是让系统在环境中自我训练。
- 世界模型 2.0 更像开发范式变化，重点是让 AI 参与发现问题、提出改进、验证结果。
- L2 到 L4 不能只靠收集人类驾驶数据；越接近高阶自动驾驶，越需要强化学习、仿真环境、评价体系和 AI 自我改进能力。
- Harness 的价值不只在自动驾驶，也可能扩展到研发、商业化、传播等更广的人机协作场景。

## 对 ClayMore 的启发

- `AGENTS.md` 和 `00-meta-规则/00-快速入口` 就是 ClayMore 的 Harness 入口。
- 规则不应堆成一个巨大文件，而应保持“短入口 + 专项规则 + 整理日志 + 验证流程”。
- AI 资料整理不能停在标题层，要形成 `metadata -> transcript -> summary -> wiki` 的闭环。
- 对复杂任务，应把“提取者、总结者、审查者”拆成不同阶段，而不是让同一个临场提示词完成全部工作。
- 对高风险资料，应强制拆分“来源声称 / 已核验事实 / 待核验”。

## 待核验

- OpenAI 文章标题、发布时间、100 万行代码、5 个月、3 到 7 人、10 倍效率等数字。
- Anthropic 文章名、Planner / Generator / Evaluator 的原始术语和实验成本。
- 楼天城访谈中“世界模型 1.0 / 2.0”的准确表达，以及 VLA、L2/L4 判断的上下文。
