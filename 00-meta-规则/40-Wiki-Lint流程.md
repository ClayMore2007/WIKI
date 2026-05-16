---
status: active
updated: 2026-05-11
confidence: high
sources:
  - [[00-meta-规则/00-快速入口]]
  - [[00-meta-规则/10-知识库原则]]
---

# Wiki Lint 流程

Wiki lint 用于定期检查知识库是否还能被搜索、链接、复盘和长期维护。

## 频率

- 每周复盘前轻量检查一次。
- 大批量整理 Cubox 或 raw 资料后检查一次。
- 修改分类体系或规则后检查一次。

## 检查项

| 检查项 | 处理方式 |
|---|---|
| 断链 | 修正到具体页面或 README；无法确认写入整理日志 |
| 空 README | 补领域定位、入口、活跃问题、待处理资料 |
| 目录链接 | 改为具体 README 或具体页面 |
| 低可信页面 | 保留 `confidence: low`，补待核验问题 |
| 高风险页面缺来源 | 补来源或标记 `needs source` |
| raw 多但无主题页 | 建议新增或更新主题页 |
| Cubox title-only 资料 | 标记内容提取优先级 |
| notes_template TODO | 单列 `_notes_template.md` 中仍有 `TODO:` 的资料，标记为已提取但未编译 |
| 仪表盘过载 | 每个领域保留 1-3 个当前关注 |

## 输出格式

```markdown
## Wiki Lint 报告 YYYY-MM-DD

### 本次范围

### 发现的问题

### 已修复

### 待用户确认

### 下一步
```

## 禁止事项

- 不因 lint 自动删除页面。
- 不擅自合并来源或统一别名。
- 不把不确定资料改写成确定结论。
- 不读取或移动 private wiki，除非用户明确要求。
