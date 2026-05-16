---
status: seed
updated: 2026-05-11
confidence: medium
sources:
  - [[30-技术知识/AI与大模型/Cubox-AI资料索引]]
  - [[30-技术知识/AI与大模型/Claude-Code-Skills推荐]]
  - [[00-log-整理日志/2026-05-11-Cubox整理报告]]
---

# Claude Code 工作流框架

本页用于把 Claude Code、Codex、Skills、多 Agent 和 Obsidian/LLM Wiki 相关资料沉淀成可复用工作流。

## 当前结论

Claude Code 相关资料已经足够形成一个长期主题。下一步不应只继续收藏视频，而应提炼为：安装配置、项目规则、Skills、自动化整理、代码协作、知识库维护六个模块。

## 核心框架

| 模块 | 用途 | 当前状态 |
|---|---|---|
| 环境配置 | 编辑器、终端、模型、权限 | 有多条视频线索，待整理 |
| 项目规则 | AGENTS/CLAUDE 规则、目录约束 | ClayMore 已有实践 |
| Skills | 可复用任务流程 | 已有推荐页 |
| 多 Agent | 并行探索、实现、审查 | 有资料线索，待提取 |
| 知识库维护 | raw 到 wiki 的编译流程 | ClayMore 正在使用 |
| 内容创作自动化 | 本地知识、Claude Code、配图和版本控制 | 已整理 [[30-技术知识/AI与大模型/Obsidian-Claude-Code内容创作自动化流程]] |
| 验证与复盘 | lint、测试、周复盘 | 需要制度化 |

## 关键事实

- Cubox 中 Claude Code / Codex / Skill 相关资料数量较多。
- ClayMore 已经有 AGENTS 规则、Cubox 接入流程和整理日志。
- 目前缺少一页把“工具使用”和“知识库维护”连接起来的长期框架。
- 2026-05-11 新增一条 B 站线索：Obsidian + Claude Code + Nano Banana 内容创作自动化。已用 `yt-dlp` 获取 metadata，并通过 `faster-whisper` 生成机器转写稿；已沉淀为 [[30-技术知识/AI与大模型/Obsidian-Claude-Code内容创作自动化流程]]，专有名词仍需核验。

## 重要来源

- [[30-技术知识/AI与大模型/Claude-Code-Skills推荐]]
- [[30-技术知识/AI与大模型/Cubox-AI资料索引]]
- [[30-技术知识/AI与大模型/Obsidian-Claude-Code内容创作自动化流程]]
- [[80-raw-原始资料/Cubox/技术/AI/Obsidian从1到2｜超越Karpathy，最全内容创作自动化全流程！把你的Ai训练成贾维斯～_哔哩哔哩_bilibili-2026-05-11]]
- [[00-meta-规则/00-快速入口]]
- [[00-meta-规则/40-Wiki-Lint流程]]

## 待核验问题

- 哪些 Skill 是稳定高频使用，哪些只是视频推荐？
- Claude Code、Codex App、多 Agent 工作流之间的边界如何划分？
- 哪些配置应该成为 ClayMore 的固定维护规则？
- Obsidian + Claude Code 的内容创作自动化流程中，哪些环节可复用于 ClayMore，哪些只适合创作项目？

## 下一步行动

- 从 Simon 林、阿众、技术爬爬虾相关资料中优先提取完整内容。
- 基于“Obsidian从1到2”的整理页，继续核对 git、配图、本地知识工作流中的工具名和可复用环节。
- 把 Skill 推荐页改造成“场景 -> Skill -> 使用条件 -> 风险”的结构。
- 每次新增工作流经验时，回写本页。

## 相关页面

- [[30-技术知识/AI与大模型/index]]
- [[00-meta-规则/30-页面模板]]
- [[00-meta-规则/40-Wiki-Lint流程]]
