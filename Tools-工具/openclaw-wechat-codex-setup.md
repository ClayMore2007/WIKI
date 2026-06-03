# OpenClaw WeChat Codex Setup

This note records the local setup for connecting WeChat ClawBot to Codex.

## Workspace

OpenClaw workspace:

```text
.
```

Run the config and gateway commands from the Obsidia workspace root so `.`
resolves to the migrated project directory. The workspace root `AGENTS.md`
remains authoritative. ClayMore tasks must first read:

```text
ClayMore\AGENTS.md
ClayMore\CLAUDE.md
```

Do not operate on `ClayMore-Private-Wiki\` unless the user explicitly asks.

## Windows Command Notes

PowerShell blocks npm-generated `.ps1` shims on this machine. Use `.cmd` entrypoints:

```powershell
npm.cmd --version
npx.cmd --version
openclaw.cmd --version
```

## Installed Components

```powershell
npm.cmd install -g openclaw
openclaw.cmd plugins install clawhub:@openclaw/codex
openclaw.cmd plugins install "@tencent-weixin/openclaw-weixin"
openclaw.cmd plugins registry --refresh
```

Installed/verified versions:

```text
OpenClaw 2026.5.7
@tencent-weixin/openclaw-weixin 2.4.3
```

## Current OpenClaw Config

```powershell
openclaw.cmd config set --batch-file 'Tools-工具\openclaw-config-set.batch.json'
openclaw.cmd config set agents.defaults.model.primary openai/gpt-5.5
openclaw.cmd config set agents.defaults.agentRuntime.id codex
openclaw.cmd config set channels.openclaw-weixin.enabled true --strict-json
openclaw.cmd config set gateway.auth.mode none
openclaw.cmd config validate
```

The batch file is used because direct PowerShell argv passing can corrupt Chinese path text on some Windows terminals.

`gateway.auth.mode none` is currently used because this local OpenClaw version accepts the loopback gateway but some deep CLI RPCs fail with `device identity required` under token/device auth. The gateway is bound to `127.0.0.1`, not LAN.

## WeChat Login

The official channel login path produced QR/login trouble in this Windows shell, so this helper was used:

```powershell
node .\Tools-工具\openclaw-weixin-manual-login.mjs
```

The WeChat account was saved locally under:

```text
C:\Users\Administrator\.openclaw\openclaw-weixin\
```

Do not print or commit account token files.

## Device Pairing Repair

If OpenClaw reports `device identity required` or `metadata change pending approval`, refresh the local operator token:

```powershell
node .\Tools-工具\openclaw-refresh-device-operator.mjs
```

If OpenClaw gives a specific pending request id:

```powershell
node .\Tools-工具\openclaw-refresh-device-operator.mjs <request-id>
```

## Start and Verify

Start the gateway:

```powershell
openclaw.cmd gateway run --force
```

Current known-good checks:

```powershell
openclaw.cmd gateway probe --timeout 30000
openclaw.cmd gateway health --timeout 30000
openclaw.cmd status --timeout 30000
openclaw.cmd models auth list --provider openai-codex
```

Expected verified state:

```text
Gateway reachable: yes
Gateway health: OK
Channel openclaw-weixin: OK / configured
Runtime: OpenAI Codex
Model: gpt-5.5
Codex OAuth profile: openai-codex:default
```

Known limitation: `openclaw.cmd status --deep` and `openclaw.cmd channels status --deep` may still fail with `device identity required` on this host even when the normal status and gateway health are OK.

## WeChat Smoke Test

From WeChat, send:

```text
/status
```

Expected result: the bot answers and reports the OpenAI Codex runtime/session.

## Fallback Route

If the native OpenClaw Codex runtime fails, use direct Codex CLI execution:

```powershell
codex exec -C "." "<task>"
```
