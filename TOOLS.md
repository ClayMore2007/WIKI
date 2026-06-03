# TOOLS.md - 本机工具备忘

这个文件记录本工作区特有的本机工具、自动化、账号连接和环境约定。

通用工作流规则放在 `AGENTS.md`；ClayMore Wiki 的维护规则放在 `ClayMore/AGENTS.md`。这里主要放“换一台电脑时需要复刻或检查的本机配置”。

## 本机自动化

- Obsidian 空闲自动提交、推送、微信 Claw Bot 通知：
  `Tools-工具/automations/obsidia-idle-auto-commit-setup.md`
  - 当前机器任务名：`Obsidian Idle Git Snapshot`
  - 当前仓库路径：`D:\ClayMore\WorkSpace\Obsidian`
  - 本机脚本：`%USERPROFILE%\.codex\local-tasks\obsidian-idle-commit.ps1`
  - 微信通知脚本：`%USERPROFILE%\.codex\local-tasks\send-obsidian-weixin-notification.mjs`
  - 说明：当前机器未配置 `openclaw.cmd` / Weixin 账号环境变量时，自动提交和推送仍会执行，微信通知会跳过并写入日志。

## OpenClaw / Weixin

- WeChat Claw Bot 与 Codex/OpenClaw 的配置说明：
  `Tools-工具/openclaw/openclaw-wechat-codex-setup.md`

## 股票脚本

- 同花顺自选股/持仓更新脚本仍保留在 `Tools-工具/` 根目录，以兼容 `ClayMore/AGENTS.md` 中的固定命令。
- 后续如果移动这些脚本，必须同步更新 `ClayMore/AGENTS.md` 和对应 Wiki 规则。

## 记录原则

- 不在这里写 token、密码、context token 或完整账号凭据。
- 可以记录脚本位置、任务名称、排障命令和非敏感的本机约定。
- 如果某个工具说明变长，优先放到 `Tools-工具/` 下单独成文，再在这里加链接。
