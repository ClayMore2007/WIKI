# Obsidia / Obsidian 空闲自动提交安装说明

本文记录当前电脑的自动提交方案，供公司/家里其他 Windows 电脑复刻。目标是在键盘/鼠标空闲 30 分钟后，将 `Obsidia` 仓库的全部 Git 变更提交并推送到 `origin/main`，提交成功后通过 OpenClaw Weixin 给 Claw Bot 发通知。

## 当前机器状态（2026-06-03）

- 当前仓库：`D:\ClayMore\WorkSpace\Obsidian`
- Windows 计划任务：`Obsidian Idle Git Snapshot`
- 触发方式：空闲 `30` 分钟后触发
- 本机脚本：`%USERPROFILE%\.codex\local-tasks\obsidian-idle-commit.ps1`
- 通知脚本：`%USERPROFILE%\.codex\local-tasks\send-obsidian-weixin-notification.mjs`
- 当前限制：这台机器的 PATH 中未找到 `openclaw.cmd`，也未配置 `OPENCLAW_WEIXIN_ACCOUNT` / `OPENCLAW_WEIXIN_TARGET` 环境变量；因此提交和推送正常执行，微信通知会跳过并写入日志。

## 行为边界

- 工作仓库：按机器实际路径配置；当前机器为 `D:\ClayMore\WorkSpace\Obsidian`
- 触发方式：Windows Task Scheduler `ONIDLE`，空闲 `30` 分钟后触发
- 提交范围：整个 Git 仓库，执行 `git add -A`，遵守 `.gitignore`
- 私有 Wiki：包含 `ClayMore-Private-Wiki/` 的变更
- 推送目标：`origin/main`
- 无变更：不创建空提交，不发送微信通知
- 失败处理：不自动解决 rebase/merge 冲突，不 force push，只写日志
- 通知策略：只有 commit + push 成功后发送微信通知

## 前置条件

1. 当前电脑已经 clone 仓库到 `E:\WorkSpace\Obsidia`。
2. Git 可以在该仓库正常提交和推送：

```powershell
cd E:\WorkSpace\Obsidia
git status --short --branch
git remote -v
git push --dry-run origin main
```

3. Node.js 可用：

```powershell
node.exe --version
```

4. OpenClaw 和 Weixin 通道已配置。可参考：

```text
Tools-工具\openclaw\openclaw-wechat-codex-setup.md
```

验证 OpenClaw：

```powershell
openclaw.cmd gateway health --timeout 30000
openclaw.cmd status --timeout 30000
```

期望看到 `openclaw-weixin: configured` 或 `Channel openclaw-weixin: OK`。

## 文件位置

脚本放在仓库外，避免把本机任务脚本误提交：

```text
%USERPROFILE%\.codex\local-tasks\obsidia-idle-commit.ps1
%USERPROFILE%\.codex\local-tasks\send-obsidia-weixin-notification.mjs
%USERPROFILE%\.codex\logs\obsidia-idle-commit.log
```

创建目录：

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\.codex\local-tasks", "$HOME\.codex\logs"
```

## 微信通知参数

通知脚本需要三个值：

```js
const channel = "openclaw-weixin";
const account = "<account-id>";
const target = "<user-id@im.wechat>";
```

获取 `account`：

```powershell
Get-ChildItem "$HOME\.openclaw\openclaw-weixin\accounts" -Filter "*.json"
```

通常文件名类似：

```text
ad20556f300b-im-bot.json
```

其中 `ad20556f300b-im-bot` 就是 account id。

获取 `target`：

```powershell
Select-String -Path "$HOME\.openclaw\openclaw-weixin\accounts\*.json" -Pattern "@im\.wechat"
```

也可以从当前 Weixin 会话上下文文件中查找最近联系人：

```powershell
Select-String -Path "$HOME\.openclaw\openclaw-weixin\accounts\*.context-tokens.json" -Pattern "@im\.wechat"
```

不要把 token、context token、完整账号文件提交到仓库。

## 通知脚本

创建 `%USERPROFILE%\.codex\local-tasks\send-obsidia-weixin-notification.mjs`：

```js
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const channel = "openclaw-weixin";
const account = "<account-id>";
const target = "<user-id@im.wechat>";
const openClawEntrypoint = join(
  process.env.APPDATA ?? "C:\\Users\\Administrator\\AppData\\Roaming",
  "npm",
  "node_modules",
  "openclaw",
  "openclaw.mjs",
);

const commit = process.argv[2] ?? "unknown";
const subject = process.argv.slice(3).join(" ") || "unknown";
const timestamp = new Date().toLocaleString("zh-CN", {
  hour12: false,
  timeZone: "Asia/Shanghai",
});

const message = [
  "Obsidia 自动提交完成",
  `时间：${timestamp}`,
  "分支：main -> origin/main",
  `提交：${commit}`,
  `说明：${subject}`,
].join("\n");

const result = spawnSync(
  process.execPath,
  [
    openClawEntrypoint,
    "message",
    "send",
    "--channel",
    channel,
    "--account",
    account,
    "--target",
    target,
    "--message",
    message,
    "--json",
  ],
  {
    encoding: "utf8",
    windowsHide: true,
  },
);

if (result.error) {
  process.stderr.write(`${result.error.stack ?? result.error.message}\n`);
}
if (result.stdout) {
  process.stdout.write(result.stdout);
}
if (result.stderr) {
  process.stderr.write(result.stderr);
}

process.exit(result.status ?? 1);
```

注意：不要在 PowerShell 中直接把中文正文传给 `openclaw.cmd --message`，容易出现微信乱码。中文正文应由 Node 脚本内部构造，并直接调用 `openclaw.mjs`。

测试通知：

```powershell
node.exe "$HOME\.codex\local-tasks\send-obsidia-weixin-notification.mjs" test123 "中文编码测试"
```

确认微信收到正常中文后再继续。

## 自动提交脚本

创建 `%USERPROFILE%\.codex\local-tasks\obsidia-idle-commit.ps1`：

```powershell
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$repo = "E:\WorkSpace\Obsidia"
$logPath = Join-Path $env:USERPROFILE ".codex\logs\obsidia-idle-commit.log"
$lockPath = Join-Path $env:TEMP "obsidia-idle-commit.lock"
$statePath = Join-Path $env:USERPROFILE ".codex\local-tasks\obsidia-idle-commit-state.txt"
$notifyScript = Join-Path $env:USERPROFILE ".codex\local-tasks\send-obsidia-weixin-notification.mjs"
$minimumCommitIntervalMinutes = 30

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logPath -Value "[$timestamp] $Message"
}

function Invoke-Git {
    param([string[]]$Arguments)
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($output) {
        foreach ($line in $output) {
            Write-Log "git $($Arguments -join ' '): $line"
        }
    }
    if ($exitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $exitCode"
    }
    return $output
}

function Get-LastSuccessfulIdleCommitTime {
    if (Test-Path -LiteralPath $statePath) {
        $raw = (Get-Content -LiteralPath $statePath -Raw).Trim()
        if ($raw) {
            try {
                return [datetime]::Parse($raw)
            }
            catch {
                Write-Log "Ignoring unreadable state timestamp: $raw"
            }
        }
    }

    $rawUnixTime = (& git log -1 --format=%ct --grep="^chore: idle snapshot " 2>$null)
    if ($LASTEXITCODE -eq 0 -and $rawUnixTime) {
        return [DateTimeOffset]::FromUnixTimeSeconds([int64]$rawUnixTime.Trim()).LocalDateTime
    }

    return $null
}

function Set-LastSuccessfulIdleCommitTime {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $statePath) | Out-Null
    Set-Content -LiteralPath $statePath -Value (Get-Date -Format "o")
}

function Sync-OriginMain {
    Invoke-Git @("pull", "--rebase", "origin", "main") | Out-Null
    Invoke-Git @("push", "origin", "main") | Out-Null
}

function Send-WeixinNotification {
    param(
        [string]$Commit,
        [string]$Subject
    )

    $output = & node.exe $notifyScript $Commit $Subject 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        foreach ($line in $output) {
            Write-Log "openclaw notify: $line"
        }
    }
    if ($exitCode -ne 0) {
        Write-Log "Weixin notification failed with exit code $exitCode."
        return
    }
    Write-Log "Weixin notification sent."
}

$lockStream = $null

try {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null

    $lockStream = [System.IO.File]::Open($lockPath, "OpenOrCreate", "ReadWrite", "None")
    Write-Log "Starting idle snapshot."

    if (-not (Test-Path -LiteralPath $repo)) {
        throw "Repository path not found: $repo"
    }

    Set-Location -LiteralPath $repo
    $gitDir = (& git rev-parse --git-dir 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $gitDir) {
        throw "Not a git repository: $repo"
    }
    $gitDir = $gitDir.Trim()
    if (-not [System.IO.Path]::IsPathRooted($gitDir)) {
        $gitDir = Join-Path $repo $gitDir
    }

    $lastSuccessfulIdleCommit = Get-LastSuccessfulIdleCommitTime
    if ($lastSuccessfulIdleCommit) {
        $elapsedSinceCommit = (Get-Date) - $lastSuccessfulIdleCommit
        if ($elapsedSinceCommit.TotalMinutes -lt $minimumCommitIntervalMinutes) {
            Write-Log ("Skipped because last successful idle commit was {0:N1} minutes ago, below {1} minutes." -f $elapsedSinceCommit.TotalMinutes, $minimumCommitIntervalMinutes)
            exit 0
        }
    }

    $blockedStates = @(
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "BISECT_LOG",
        "rebase-apply",
        "rebase-merge"
    )
    foreach ($state in $blockedStates) {
        if (Test-Path -LiteralPath (Join-Path $gitDir $state)) {
            Write-Log "Skipped because git state is in progress: $state"
            exit 0
        }
    }

    Invoke-Git @("add", "-A") | Out-Null

    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        $aheadCount = (& git rev-list --count origin/main..HEAD 2>$null)
        if ($LASTEXITCODE -eq 0 -and [int]$aheadCount -gt 0) {
            Write-Log "No staged changes, but local branch is ahead by $aheadCount commit(s). Syncing."
            Sync-OriginMain
            Write-Log "Ahead commits synced."
            exit 0
        }
        Write-Log "No staged changes and no ahead commits. Nothing to do."
        exit 0
    }

    if ($LASTEXITCODE -ne 1) {
        throw "git diff --cached --quiet failed with exit code $LASTEXITCODE"
    }

    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    Invoke-Git @("commit", "-m", "chore: idle snapshot $stamp") | Out-Null
    Sync-OriginMain
    Set-LastSuccessfulIdleCommitTime
    $commit = (& git rev-parse --short HEAD).Trim()
    $subject = (& git log -1 --pretty=%s).Trim()
    Send-WeixinNotification -Commit $commit -Subject $subject

    Write-Log "Idle snapshot completed."
}
catch [System.IO.IOException] {
    Write-Log "Skipped because another idle snapshot is already running."
    exit 0
}
catch {
    Write-Log "Failed: $($_.Exception.Message)"
    exit 1
}
finally {
    if ($lockStream) {
        $lockStream.Close()
        $lockStream.Dispose()
    }
}
```

语法检查：

```powershell
$script = Get-Content -Raw -LiteralPath "$HOME\.codex\local-tasks\obsidia-idle-commit.ps1"
$parseErrors = $null
[System.Management.Automation.PSParser]::Tokenize($script, [ref]$parseErrors) | Out-Null
if ($parseErrors -and $parseErrors.Count -gt 0) { $parseErrors | Format-List *; exit 1 }
"PowerShell syntax OK"
```

手动运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$HOME\.codex\local-tasks\obsidia-idle-commit.ps1"
Get-Content -LiteralPath "$HOME\.codex\logs\obsidia-idle-commit.log" -Tail 40
git -C E:\WorkSpace\Obsidia status --short --branch
```

## 创建 Windows 计划任务

创建空闲任务：

```powershell
$taskName = "Obsidia Idle Git Snapshot"
$script = Join-Path $HOME ".codex\local-tasks\obsidia-idle-commit.ps1"
$tr = "`"$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe`" -NoProfile -ExecutionPolicy Bypass -File `"$script`""
schtasks /Create /SC ONIDLE /I 30 /TN $taskName /TR $tr /F
```

调整运行策略：

```powershell
$settings = New-ScheduledTaskSettingsSet `
  -MultipleInstances IgnoreNew `
  -RunOnlyIfIdle `
  -IdleDuration (New-TimeSpan -Minutes 30) `
  -IdleWaitTimeout (New-TimeSpan -Hours 1) `
  -DontStopOnIdleEnd `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Set-ScheduledTask -TaskName "Obsidia Idle Git Snapshot" -Settings $settings | Out-Null
```

验证任务：

```powershell
schtasks /Query /TN "Obsidia Idle Git Snapshot" /V /FO LIST
schtasks /Query /TN "Obsidia Idle Git Snapshot" /XML
```

XML 中应包含：

```xml
<IdleTrigger>
<RunOnlyIfIdle>true</RunOnlyIfIdle>
<Duration>PT30M</Duration>
<StopOnIdleEnd>false</StopOnIdleEnd>
```

## 日常检查

查看任务：

```powershell
schtasks /Query /TN "Obsidia Idle Git Snapshot" /V /FO LIST
```

查看日志：

```powershell
Get-Content -LiteralPath "$HOME\.codex\logs\obsidia-idle-commit.log" -Tail 80
```

禁用任务：

```powershell
schtasks /Change /TN "Obsidia Idle Git Snapshot" /DISABLE
```

启用任务：

```powershell
schtasks /Change /TN "Obsidia Idle Git Snapshot" /ENABLE
```

删除任务：

```powershell
schtasks /Delete /TN "Obsidia Idle Git Snapshot" /F
```

## 常见问题

### 微信消息乱码

不要用 PowerShell 直接执行：

```powershell
openclaw.cmd message send --message "中文正文"
```

应使用 `send-obsidia-weixin-notification.mjs`，由 Node 构造中文正文并直接调用 `openclaw.mjs`。

### Push 成功但出现 credential-manager-core 提示

如果日志里出现：

```text
git: 'credential-manager-core' is not a git command
```

但后面仍显示 `main -> main`，说明 push 已成功。这是本机 Git credential helper 的非阻塞提示。可后续单独修 Git 配置。

### Rebase 或 push 失败

脚本不会 force push，也不会自动解决冲突。查看日志后手动处理：

```powershell
cd E:\WorkSpace\Obsidia
git status
git pull --rebase origin main
git push origin main
```

### 无变更时没有微信通知

这是预期行为。日志会显示：

```text
No staged changes and no ahead commits. Nothing to do.
```
