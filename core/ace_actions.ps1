# Ace PC Actions Engine - hands on your PC
Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue

function Invoke-AceType {
    param ([string]$Text, [int]$DelayMs = 15)
    if ([string]::IsNullOrEmpty($Text)) { return }
    foreach ($ch in $Text.ToCharArray()) {
        $c = [string]$ch
        if ($c -eq "`n") { $c = "{ENTER}" }
        elseif ($c -eq "`r") { continue }
        elseif ($c -match '[\+\^\%~\(\)\{\}\[\]]') { $c = "{$c}" }
        try { [System.Windows.Forms.SendKeys]::SendWait($c) } catch {}
        if ($DelayMs -gt 0) { Start-Sleep -Milliseconds $DelayMs }
    }
}

$script:AceAppAliases = @{
    "downloads" = "SHELL:Downloads"; "documents" = "SHELL:Personal"; "desktop" = "SHELL:Desktop"
    "pictures" = "SHELL:My Pictures"; "music" = "SHELL:My Music"; "videos" = "SHELL:My Video"
    "calc" = "calc.exe"; "calculator" = "calc.exe"; "notepad" = "notepad.exe"; "paint" = "mspaint.exe"
    "explorer" = "explorer.exe"; "file explorer" = "explorer.exe"; "files" = "explorer.exe"
    "settings" = "ms-settings:"; "task manager" = "taskmgr.exe"; "control panel" = "control.exe"
    "cmd" = "cmd.exe"; "command prompt" = "cmd.exe"; "powershell" = "powershell.exe"; "terminal" = "wt.exe"
    "chrome" = "chrome.exe"; "google chrome" = "chrome.exe"; "edge" = "msedge.exe"; "firefox" = "firefox.exe"
    "vscode" = "code"; "vs code" = "code"; "visual studio code" = "code"
    "word" = "winword.exe"; "excel" = "excel.exe"; "powerpoint" = "powerpnt.exe"; "outlook" = "outlook.exe"
    "spotify" = "spotify:"; "discord" = "discord:"; "whatsapp" = "whatsapp:"; "steam" = "steam:"
    "store" = "ms-windows-store:"; "camera" = "microsoft.windows.camera:"; "snipping tool" = "ms-screenclip:"
}

$script:AceWebFallbacks = @{
    "browser" = "https://www.google.com"; "google" = "https://www.google.com"
    "youtube" = "https://www.youtube.com"; "github" = "https://github.com"; "gmail" = "https://mail.google.com"
    "chatgpt" = "https://chatgpt.com"; "netflix" = "https://www.netflix.com"
}

function Find-AceStartMenuApp {
    param ([string]$Name)
    $dirs = @(
        [Environment]::GetFolderPath("Desktop"),
        [Environment]::GetFolderPath("CommonDesktopDirectory"),
        "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
        "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
    ) | Where-Object { $_ -and (Test-Path $_) }
    $links = Get-ChildItem -Path $dirs -Include *.lnk, *.url, *.appref-ms -Recurse -ErrorAction SilentlyContinue
    $hit = $links | Where-Object { $_.BaseName -ieq $Name } | Select-Object -First 1
    if (-not $hit) { $hit = $links | Where-Object { $_.BaseName -like "*$Name*" } | Sort-Object { $_.BaseName.Length } | Select-Object -First 1 }
    return $hit
}

function Invoke-AceOpen {
    param ([string]$Target)
    if ([string]::IsNullOrWhiteSpace($Target)) { return "Open what, bro?" }
    $t = $Target.Trim().Trim('"').TrimEnd('.', '!', '?')
    $key = $t.ToLower() -replace '^(the|my|up)\s+', '' -replace '\s+(shortcut|atalho|app|application|for me|please)$', ''

    $lnk = Find-AceStartMenuApp $key
    if ($lnk) {
        try { Start-Process $lnk.FullName -ErrorAction Stop; return "Opened $($lnk.BaseName) shortcut." } catch {}
    }

    if ($script:AceAppAliases.ContainsKey($key)) { $t = $script:AceAppAliases[$key] }
    elseif ($script:AceWebFallbacks.ContainsKey($key)) { $t = $script:AceWebFallbacks[$key] }

    if ($t -match '^[\w\-]+\.(com|org|net|io|dev|ai|co|app|tv|gg)(/.*)?$') { $t = "https://$t" }

    try { Start-Process $t -ErrorAction Stop; return "Opened $Target." } catch {}
    return "Couldn't find '$Target' on this PC, bro."
}

function Invoke-AceKeyCombo {
    param ([string]$Combo)
    $map = @{ "enter"="{ENTER}"; "tab"="{TAB}"; "copy"="^c"; "paste"="^v"; "cut"="^x"; "select all"="^a";
              "save"="^s"; "undo"="^z"; "redo"="^y"; "new tab"="^t"; "close tab"="^w"; "escape"="{ESC}";
              "close window"="%{F4}"; "refresh"="{F5}"; "find"="^f" }
    $k = $Combo.Trim().ToLower()
    $seq = if ($map.ContainsKey($k)) { $map[$k] } else { $Combo }
    [System.Windows.Forms.SendKeys]::SendWait($seq)
}

function Invoke-AceVolume {
    param ([ValidateSet("up","down","mute")] [string]$Action, [int]$Steps = 5)
    $wsh = New-Object -ComObject WScript.Shell
    switch ($Action) {
        "mute" { $wsh.SendKeys([string][char]173) }
        "down" { 1..$Steps | ForEach-Object { $wsh.SendKeys([string][char]174) } }
        "up"   { 1..$Steps | ForEach-Object { $wsh.SendKeys([string][char]175) } }
    }
}

function Invoke-AceScreenshot {
    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bmp.Size)
    $dir = [Environment]::GetFolderPath('MyPictures')
    $path = Join-Path $dir ("Ace_Screenshot_{0}.png" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    return $path
}

function Get-AcePcMetrics {
    $os = Get-CimInstance Win32_OperatingSystem
    $total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    $free  = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
    $used  = [math]::Round($total - $free, 1)
    $cpu = try { [math]::Round((Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average) } catch { "?" }
    $bat = try { (Get-CimInstance Win32_Battery -ErrorAction Stop | Select-Object -First 1).EstimatedChargeRemaining } catch { $null }
    return @{ TotalRamGB = $total; UsedRamGB = $used; RamPercent = [math]::Round(($used / $total) * 100); Cpu = $cpu; Battery = $bat }
}
