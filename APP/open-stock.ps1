param(
    [switch]$RefreshCache,
    [int]$Port = 5173,
    [string]$Url = "http://127.0.0.1:5173"
)

$ErrorActionPreference = "Stop"

$StockRoot = Join-Path $PSScriptRoot "stock"
$CacheMeta = Join-Path $StockRoot "data\cache\meta.json"
$LogPath = Join-Path $StockRoot "vite-dev.log"
$ErrorLogPath = Join-Path $StockRoot "vite-dev.err.log"

function Test-StockPort {
    $connection = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Test-StockCache {
    return Test-Path -LiteralPath $CacheMeta
}

function Invoke-StockCacheBuild {
    Push-Location $StockRoot
    try {
        & npm.cmd run build:cache
        if ($LASTEXITCODE -ne 0) {
            throw "npm run build:cache failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Start-StockDevServer {
    Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev") `
        -WorkingDirectory $StockRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogPath `
        -RedirectStandardError $ErrorLogPath

    for ($i = 0; $i -lt 20; $i++) {
        if (Test-StockPort) {
            return
        }
        Start-Sleep -Milliseconds 250
    }

    throw "Stock app did not start on $Url. Check $LogPath and $ErrorLogPath."
}

if ($RefreshCache -or -not (Test-StockCache)) {
    Invoke-StockCacheBuild
}

if (-not (Test-StockPort)) {
    Start-StockDevServer
}

Start-Process $Url
