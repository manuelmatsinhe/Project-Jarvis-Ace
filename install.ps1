# Ace installer - run once:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
# - puts the `ace` command on your PATH (CMD + PowerShell)
# - sets ACE_HOME
# - creates config files from the examples
# - optional: start with Windows

param ([switch]$Autostart)

$root = $PSScriptRoot
$cli  = Join-Path $root "cli"
$cfg  = Join-Path $root "config"

Write-Host "Installing Ace from $root" -ForegroundColor Cyan

foreach ($name in "settings", "profile") {
    $target  = Join-Path $cfg "$name.json"
    $example = Join-Path $cfg "$name.example.json"
    if (!(Test-Path $target) -and (Test-Path $example)) { Copy-Item $example $target; Write-Host "  created config\$name.json" }
}
if (!(Test-Path (Join-Path $root "ipc"))) { New-Item -ItemType Directory -Path (Join-Path $root "ipc") | Out-Null }

[Environment]::SetEnvironmentVariable("ACE_HOME", $root, "User")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$parts = @($userPath -split ';' | Where-Object { $_ -and $_ -notlike "*project-jarvis-ace\cli*" -and $_ -notlike "*Project-Jarvis-Ace\cli*" })
$parts = @($cli) + $parts
[Environment]::SetEnvironmentVariable("Path", ($parts -join ';'), "User")
Write-Host "  added $cli to your PATH" -ForegroundColor Green

Get-ChildItem -Path $root -Recurse -Include *.ps1, *.bat, *.cmd | Unblock-File -ErrorAction SilentlyContinue

if ($Autostart) { & (Join-Path $cli "ace.ps1") autostart on }

Write-Host ""
Write-Host "Done. Open a NEW terminal and type:  ace start" -ForegroundColor Green
Write-Host "Then teach him your style:           ace learn"
Write-Host "Optional real AI brain:              ace set-key <your Gemini API key>"
