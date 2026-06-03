# WeChat ClawBot Codex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect WeChat ClawBot to Codex through the official OpenClaw Weixin channel, with the agent workspace fixed to `E:\华为云盘\Wiki\Obsidia`.

**Architecture:** WeChat ClawBot talks to `@tencent-weixin/openclaw-weixin`, OpenClaw routes chat turns through the Codex harness, and Codex runs with `E:\华为云盘\Wiki\Obsidia` as its workspace. The standalone `codex exec` runner remains a fallback, but the primary route is OpenClaw's native Codex runtime.

**Tech Stack:** OpenClaw CLI, `@openclaw/codex`, `@tencent-weixin/openclaw-weixin`, OpenAI Codex OAuth, Windows PowerShell `.cmd` entrypoints.

---

### Task 1: Install Required CLIs and Plugins

**Files:**
- Modify: global npm packages
- Modify: `C:\Users\Administrator\.openclaw\openclaw.json`

- [x] **Step 1: Install OpenClaw**

```powershell
npm.cmd install -g openclaw
```

Expected: `openclaw.cmd --version` prints `OpenClaw 2026.5.7` or newer.

- [x] **Step 2: Install Codex harness plugin**

```powershell
openclaw.cmd plugins install clawhub:@openclaw/codex
```

Expected: plugin `codex` is installed under `C:\Users\Administrator\.openclaw\extensions\codex`.

- [x] **Step 3: Install Weixin channel plugin**

```powershell
openclaw.cmd plugins install "@tencent-weixin/openclaw-weixin"
```

Expected: plugin `openclaw-weixin` is installed and enabled.

- [x] **Step 4: Refresh the plugin registry**

```powershell
openclaw.cmd plugins registry --refresh
```

Expected: registry contains `packageChannel.id = openclaw-weixin`.

### Task 2: Configure Workspace and Runtime

**Files:**
- Modify: `C:\Users\Administrator\.openclaw\openclaw.json`

- [x] **Step 1: Fix the OpenClaw workspace**

```powershell
openclaw.cmd config set --batch-file 'Tools-工具\openclaw-config-set.batch.json'
```

- [x] **Step 2: Select the Codex runtime model route**

```powershell
openclaw.cmd config set agents.defaults.model.primary openai/gpt-5.5
openclaw.cmd config set agents.defaults.agentRuntime.id codex
openclaw.cmd config set channels.openclaw-weixin.enabled true --strict-json
```

- [x] **Step 3: Validate configuration**

```powershell
openclaw.cmd config validate
```

Expected: `Config valid: ~\.openclaw\openclaw.json`.

### Task 3: Complete Interactive Auth

**Files:**
- Modify: OpenClaw auth/profile state under `C:\Users\Administrator\.openclaw`

- [ ] **Step 1: Log in to Codex OAuth**

```powershell
openclaw.cmd models auth login --provider openai-codex
```

Expected: browser or terminal auth flow completes successfully.

- [ ] **Step 2: Bind WeChat ClawBot**

```powershell
openclaw.cmd channels login --channel openclaw-weixin
```

Expected: terminal shows a QR code; scan it with WeChat and confirm authorization.

- [ ] **Step 3: Verify auth profiles**

```powershell
openclaw.cmd models auth list --provider openai-codex --json
openclaw.cmd channels list
```

Expected: Codex auth and Weixin channel account are listed.

### Task 4: Start Gateway and Smoke Test

**Files:**
- Read: `E:\华为云盘\Wiki\Obsidia\AGENTS.md`
- Read: `E:\华为云盘\Wiki\Obsidia\ClayMore\AGENTS.md` for ClayMore tasks
- Read: `E:\华为云盘\Wiki\Obsidia\ClayMore\CLAUDE.md` for ClayMore tasks

- [ ] **Step 1: Restart the gateway**

```powershell
openclaw.cmd gateway restart
```

- [ ] **Step 2: Check status**

```powershell
openclaw.cmd channels status --deep
openclaw.cmd doctor
```

Expected: Weixin channel is connected and the Codex runtime is available.

- [ ] **Step 3: Test from WeChat**

Send this to ClawBot:

```text
/status
```

Expected: the reply reports the OpenAI Codex runtime.

- [ ] **Step 4: Test workspace policy**

Send this to ClawBot:

```text
只读总结 E:\华为云盘\Wiki\Obsidia 的根目录规则，不要修改文件。
```

Expected: reply mentions the root `AGENTS.md` rule and does not touch `ClayMore-Private-Wiki/`.
