# Ace CLI - call Ace from any CMD or PowerShell window.
#   ace                 -> help
#   ace <anything>      -> talk to Ace / give an order, prints his reply
#   ace chat            -> live chat session in the terminal

param ([Parameter(ValueFromRemainingArguments = $true)] [string[]]$ArgsList)

# Locate project (works from the repo folder or from a copy on PATH)
$projectRoot = $null
foreach ($cand in @((Split-Path -Parent $PSScriptRoot), $env:ACE_HOME, "$env:USERPROFILE\Documents\Project-Jarvis-Ace")) {
    if ($cand -and (Test-Path (Join-Path $cand "core\ace_agent.ps1"))) { $projectRoot = $cand; break }
}
if (-not $projectRoot) { Write-Host "[ACE] Can't find the Ace project folder. Set ACE_HOME to it." -ForegroundColor Red; exit 1 }

$agentScript  = Join-Path $projectRoot "core\ace_agent.ps1"
$interview    = Join-Path $projectRoot "core\ace_interview.ps1"
$ipcDir       = Join-Path $projectRoot "ipc"
$lockFile     = Join-Path $ipcDir "ace.lock"
$queueFile    = Join-Path $ipcDir "queue.json"
$responseFile = Join-Path $ipcDir "response.json"
$settingsFile = Join-Path $projectRoot "config\settings.json"
if (!(Test-Path $ipcDir)) { New-Item -ItemType Directory -Path $ipcDir -Force | Out-Null }

function Test-AceRunning {
    if (!(Test-Path $lockFile)) { return $false }
    $id = (Get-Content $lockFile -Raw -ErrorAction SilentlyContinue)
    if (-not $id) { return $false }
    $p = Get-Process -Id ([int]$id.Trim()) -ErrorAction SilentlyContinue
    return [bool]($p -and $p.ProcessName -like "powershell*")
}

function Start-Ace {
    if (Test-AceRunning) { return }
    Write-Host "[ACE] Waking Ace up..." -ForegroundColor Cyan
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", "`"$agentScript`""
    for ($i = 0; $i -lt 30 -and -not (Test-AceRunning); $i++) { Start-Sleep -Milliseconds 200 }
    Start-Sleep -Milliseconds 800
}

function Send-Ace {
    param ([string]$Text, [int]$TimeoutSec = 25)
    Start-Ace
    $id = [guid]::NewGuid().ToString()
    @{ id = $id; command = $Text; timestamp = (Get-Date).ToString("o") } | ConvertTo-Json | Set-Content -Path $queueFile -Force -Encoding UTF8
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 200
        try {
            $r = Get-Content -Raw $responseFile -ErrorAction Stop | ConvertFrom-Json
            if ($r.id -eq $id) { Write-Host "Ace: " -ForegroundColor Cyan -NoNewline; Write-Host $r.reply; return }
        } catch {}
    }
    Write-Host "[ACE] Sent, but no reply yet (he may still be thinking)." -ForegroundColor DarkYellow
}

function Set-Setting {
    param ([string]$Name, $Value)
    $s = if (Test-Path $settingsFile) { Get-Content -Raw $settingsFile | ConvertFrom-Json } else { [pscustomobject]@{} }
    $s | Add-Member NoteProperty $Name $Value -Force
    $s | ConvertTo-Json -Depth 5 | Set-Content -Path $settingsFile -Force -Encoding UTF8
}

$raw = ($ArgsList -join " ").Trim()

switch -Regex ($raw) {
    '^$' {
        Write-Host ""
        Write-Host "  ACE // Project Jarvis" -ForegroundColor Cyan
        Write-Host "  ---------------------" -ForegroundColor DarkCyan
        Write-Host "  ace start | stop | restart     Launch / close Ace"
        Write-Host "  ace <anything>                 Talk to him or give an order (he replies here)"
        Write-Host "  ace chat                       Live chat session in this terminal"
        Write-Host "  ace open spotify | search x | play lofi | type hello | screenshot | status"
        Write-Host "  ace run <powershell cmd>       Run any command through Ace"
        Write-Host "  ace corner tl|tr|bl|br         Snap to a screen corner"
        Write-Host "  ace mode man | mode island     Solo little man / dynamic island"
        Write-Host "  ace mic on | mic off           Toggle voice listening"
        Write-Host "  ace learn                      Teach Ace how you talk"
        Write-Host "  ace set-key <GEMINI_KEY>       Give Ace a real AI brain (free key: aistudio.google.com)"
        Write-Host "  ace autostart on | off         Start Ace when Windows starts"
        Write-Host ""
        Write-Host "  Voice: say 'Hey Ace, open notepad' or 'Hey Ace' ... then talk." -ForegroundColor DarkGray
        Write-Host ""
        break
    }
    '^start$'   { if (Test-AceRunning) { Write-Host "[ACE] Already on screen." -ForegroundColor Yellow } else { Start-Ace; Write-Host "[ACE] Online." -ForegroundColor Green }; break }
    '^(stop|quit|exit)$' {
        if (Test-AceRunning) { Stop-Process -Id ([int](Get-Content $lockFile -Raw).Trim()) -Force; Remove-Item $lockFile -Force -ErrorAction SilentlyContinue; Write-Host "[ACE] Asleep." -ForegroundColor Yellow }
        else { Write-Host "[ACE] Not running." -ForegroundColor Gray }
        break
    }
    '^restart$' {
        if (Test-AceRunning) { Stop-Process -Id ([int](Get-Content $lockFile -Raw).Trim()) -Force; Remove-Item $lockFile -Force -ErrorAction SilentlyContinue; Start-Sleep 1 }
        Start-Ace; Write-Host "[ACE] Restarted." -ForegroundColor Green; break
    }
    '^(learn|interview|calibrate)$' { & powershell -NoProfile -ExecutionPolicy Bypass -File $interview; break }
    '^set-key\s+(\S+)$' { Set-Setting "aiApiKey" $matches[1]; Write-Host "[ACE] Key saved. Restarting Ace isn't needed - next message uses it." -ForegroundColor Green; break }
    '^mic\s+(on|off)$' {
        Set-Setting "voiceEnabled" ($matches[1] -eq "on")
        if (Test-AceRunning) { & $PSCommandPath restart } else { Write-Host "[ACE] Mic $($matches[1]) saved." }
        break
    }
    '^autostart\s+(on|off)$' {
        $lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "Ace.lnk"
        if ($matches[1] -eq "on") {
            $sh = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
            $sh.TargetPath = "powershell.exe"
            $sh.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$agentScript`""
            $sh.WindowStyle = 7
            $sh.Save()
            Write-Host "[ACE] Ace will start with Windows." -ForegroundColor Green
        } else { Remove-Item $lnk -Force -ErrorAction SilentlyContinue; Write-Host "[ACE] Autostart off." }
        break
    }
    '^chat$' {
        Write-Host "Chat with Ace. Type 'exit' to leave." -ForegroundColor Cyan
        while ($true) {
            $line = Read-Host "You"
            if ($line -match '^(exit|quit|bye)$') { Write-Host "Ace: Later bro." -ForegroundColor Cyan; break }
            if ($line.Trim()) { Send-Ace $line }
        }
        break
    }
    default { Send-Ace $raw }
}
