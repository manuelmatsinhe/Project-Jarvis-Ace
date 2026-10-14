# ==========================================
# ACE - AI DESKTOP ASSISTANT (MAIN PROCESS)
# ==========================================
# UI Modes: "mini_man", "island", "block", "ambient"

Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase, System.Windows.Forms, System.Drawing -ErrorAction SilentlyContinue

# --- Directories & IPC Setup ---
$projectRoot = Split-Path -Parent $PSScriptRoot
$configDir   = Join-Path $projectRoot "config"
$ipcDir      = Join-Path $projectRoot "ipc"

if (!(Test-Path $ipcDir)) { New-Item -ItemType Directory -Path $ipcDir -Force | Out-Null }
$script:QueueFile    = Join-Path $ipcDir "queue.json"
$script:ResponseFile = Join-Path $ipcDir "response.json"
$script:ErrorLog     = Join-Path $ipcDir "error.log"
$script:SettingsFile = Join-Path $configDir "settings.json"

function Write-AceLog { param([string]$Msg) try { Add-Content -Path $script:ErrorLog -Value ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Msg) } catch {} }

# --- Core Modules ---
. (Join-Path $PSScriptRoot "ace_actions.ps1")
. (Join-Path $PSScriptRoot "ace_speech.ps1")
. (Join-Path $PSScriptRoot "ace_personality.ps1")
. (Join-Path $PSScriptRoot "ace_brain.ps1")

# --- Settings Management ---

function Get-AceSettings {
    $s = $null
    if (Test-Path $script:SettingsFile) { try { $s = Get-Content -Raw $script:SettingsFile | ConvertFrom-Json } catch {} }
    if (-not $s) { $s = [pscustomobject]@{} }
    $defaults = @{ corner = "TR"; displayMode = "mini_man"; voiceEnabled = $true; nudgeMinutes = 20 }
    foreach ($k in $defaults.Keys) { if ($null -eq $s.$k) { $s | Add-Member NoteProperty $k $defaults[$k] -Force } }
    return $s
}
function Save-AceSettings { try { $script:S | ConvertTo-Json -Depth 5 | Set-Content -Path $script:SettingsFile -Force -Encoding UTF8 } catch {} }
$script:S = Get-AceSettings

# --- XAML Loading & UI Initialization ---
$fs = [System.IO.File]::OpenRead((Join-Path $PSScriptRoot "ace_ui.xaml"))
$window = [System.Windows.Markup.XamlReader]::Load($fs)
$fs.Close()

$names = "RootContainer","MainUIBox","FullScreenBg","ContentGrid","AmbientInfo","AmbientClock","AmbientAmPm","AmbientDate","AmbientWeather",
         "TrayBorder","TrayStack","IslandHeader","IslandStatusText","BlockBody","BtnScreenshot","BtnBrowser",
         "BtnMic","BtnSettings","BtnMode","BtnPrompts","BtnToggleColor","BtnAutomations","BtnSleep","CmdInput","BtnRunCmd","AvatarCanvas","AvatarViewbox",
         "LeftEye","RightEye","LeftArm","RightArm","AvatarHead","AvatarBody","AvatarLeftLeg","AvatarRightLeg","AvatarTie","AmbientWaveformPanel","AmbientStatus","AmbientInput",
         "AmbientNavBar","BtnNavSolo","BtnNavIsland","BtnNavBlock","BtnNavExit",
         "AvatarGlow","PW1","PW2","PW3","PW4","PW5","PW6","PW7",
         "BW1","BW2","BW3","BW4","BW5","BW6","BW7","BW8","BW9",
         "AW1","AW2","AW3","AW4","AW5","AW6","AW7","AW8","AW9"

$ui = @{}
foreach ($n in $names) { $ui[$n] = $window.FindName($n) }

$script:Brush = New-Object System.Windows.Media.BrushConverter

$script:FreeMove     = $false
$script:WorkQueue    = New-Object System.Collections.Queue
$script:LastActivity = Get-Date
$script:PendingType  = $null
$script:TypeAt       = [datetime]::MaxValue

$anim = $window.Resources["LevitateAnim"]
if ($anim) { $anim.Begin($ui.AvatarCanvas, $true) }

# --- State & Layout Management ---
function Set-AceState {
    param ([string]$State, [string]$Message)
    $c = switch ($State) { "listening" { "#10B981" } "thinking" { "#F59E0B" } "acting" { "#A855F7" } default { "#FFFFFF" } }
    
    if ($ui.AvatarGlow) { $ui.AvatarGlow.Color = [System.Windows.Media.ColorConverter]::ConvertFromString($c) }
    
    if ($Message) { 
        if ($ui.IslandStatusText) { $ui.IslandStatusText.Text = $Message }
        if ($ui.AmbientStatus) { $ui.AmbientStatus.Text = $Message }
    }
}

function Update-Position {
    if ($script:FreeMove -or $script:S.displayMode -eq "ambient") { return }
    $wa = [System.Windows.SystemParameters]::WorkArea
    $w = $window.ActualWidth; $h = $window.ActualHeight; $m = 12
    if ($w -eq 0 -or $h -eq 0) { return }
    switch ($script:S.corner) {
        "TL" { $window.Left = $wa.Left + $m;          $window.Top = $wa.Top + $m }
        "TR" { $window.Left = $wa.Right - $w - $m;    $window.Top = $wa.Top + $m }
        "BL" { $window.Left = $wa.Left + $m;          $window.Top = $wa.Bottom - $h - $m }
        default { $window.Left = $wa.Right - $w - $m; $window.Top = $wa.Bottom - $h - $m }
    }
}

function Set-Corner {
    param ([string]$Corner)
    $c = $Corner.ToUpper().Trim()
    if ($c -notin "TL","TR","BL","BR") { return }
    $script:S.corner = $c; $script:FreeMove = $false; Save-AceSettings; Update-Position
}

function Set-DisplayMode {
    param ([string]$Mode)
    $script:S.displayMode = $Mode; Save-AceSettings
    
    if ($Mode -eq "ambient") {
        $window.SizeToContent = "Manual"
        $window.Width = [System.Windows.SystemParameters]::PrimaryScreenWidth
        $window.Height = [System.Windows.SystemParameters]::PrimaryScreenHeight
        $window.Left = 0; $window.Top = 0
        
        $ui.FullScreenBg.Visibility = "Visible"
        $ui.AmbientInfo.Visibility = "Visible"
        $ui.AmbientWaveformPanel.Visibility = "Visible"
        if ($ui.AmbientNavBar) { $ui.AmbientNavBar.Visibility = "Visible" }
        $ui.TrayBorder.Visibility = "Collapsed"
        
        if ($ui.MainUIBox) {
            $ui.MainUIBox.VerticalAlignment = "Center"
        }

        if ($ui.AvatarViewbox) {
            $ui.AvatarViewbox.Width = 320
            $ui.AvatarViewbox.Height = 400
            $ui.AvatarViewbox.HorizontalAlignment = "Right"
            $ui.AvatarViewbox.VerticalAlignment = "Center"
            $ui.AvatarViewbox.Margin = [System.Windows.Thickness]::new(0,0,150,0)
        }
        
        $ui.AmbientClock.Text = (Get-Date).ToString("h:mm")
        $ui.AmbientAmPm.Text = (Get-Date).ToString("tt")
        $ui.AmbientDate.Text = (Get-Date).ToString("dddd, MMMM d")
    } else {
        $window.SizeToContent = "WidthAndHeight"
        $window.Width = [Double]::NaN
        $window.Height = [Double]::NaN
        
        $ui.FullScreenBg.Visibility = "Collapsed"
        $ui.AmbientInfo.Visibility = "Collapsed"
        $ui.AmbientWaveformPanel.Visibility = "Collapsed"
        if ($ui.AmbientNavBar) { $ui.AmbientNavBar.Visibility = "Collapsed" }
        
        if ($ui.MainUIBox) {
            $ui.MainUIBox.VerticalAlignment = "Top"
        }

        if ($Mode -eq "mini_man") {
            $ui.TrayBorder.Visibility = "Collapsed"
            if ($ui.AvatarViewbox) {
                $ui.AvatarViewbox.Width = 80
                $ui.AvatarViewbox.Height = 100
                $ui.AvatarViewbox.HorizontalAlignment = "Center"
                $ui.AvatarViewbox.VerticalAlignment = "Top"
                $ui.AvatarViewbox.Margin = [System.Windows.Thickness]::new(0,0,0,0)
            }
        } elseif ($Mode -eq "island") {
            $ui.TrayBorder.Visibility = "Visible"
            $ui.BlockBody.Visibility = "Collapsed"
            $ui.IslandHeader.Visibility = "Visible"
            
            if ($ui.AvatarViewbox) {
                $ui.AvatarViewbox.Width = 55
                $ui.AvatarViewbox.Height = 70
                $ui.AvatarViewbox.HorizontalAlignment = "Left"
                $ui.AvatarViewbox.VerticalAlignment = "Top"
                $ui.AvatarViewbox.Margin = [System.Windows.Thickness]::new(12,0,0,0)
            }
        } elseif ($Mode -eq "block") {
            $ui.TrayBorder.Visibility = "Visible"
            $ui.BlockBody.Visibility = "Visible"
            $ui.IslandHeader.Visibility = "Collapsed"
            
            if ($ui.AvatarViewbox) {
                $ui.AvatarViewbox.Width = 60
                $ui.AvatarViewbox.Height = 75
                $ui.AvatarViewbox.HorizontalAlignment = "Left"
                $ui.AvatarViewbox.VerticalAlignment = "Top"
                $ui.AvatarViewbox.Margin = [System.Windows.Thickness]::new(25,15,0,0)
            }
        }
    }
    
    # We must delay Update-Position until rendering is complete because SizeToContent takes a moment
    $window.Dispatcher.InvokeAsync({ Update-Position }, [System.Windows.Threading.DispatcherPriority]::ContextIdle) | Out-Null
}

function Set-Mic {
    param ([bool]$On)
    if ($On) {
        if (Start-AceVoiceListener) {
            if ($ui.BtnMic) { $ui.BtnMic.Content = "Mic: ON"; $ui.BtnMic.Foreground = $script:Brush.ConvertFromString("#10B981") }
            $script:S.voiceEnabled = $true; Save-AceSettings
        } else {
            if ($ui.BtnMic) { $ui.BtnMic.Content = "Mic: ERR"; $ui.BtnMic.Foreground = $script:Brush.ConvertFromString("#f87171") }
            Write-AceLog $global:AceVoiceError
        }
    } else {
        Stop-AceVoiceListener
        if ($ui.BtnMic) { $ui.BtnMic.Content = "Mic: OFF"; $ui.BtnMic.Foreground = $script:Brush.ConvertFromString("#94a3b8") }
        $script:S.voiceEnabled = $false; Save-AceSettings
    }
}

# --- Input & Task Processing ---
function Submit-Input {
    param ([string]$Text, [string]$Id = $null)
    if ([string]::IsNullOrWhiteSpace($Text)) { return }
    $Text = $Text.Trim()
    if ($Text -match "^(return to pc|exit ambient|close ambient)$") { Set-DisplayMode "block"; return }
    
    $script:LastActivity = Get-Date
    Set-AceState "thinking" "Thinking..."
    $script:WorkQueue.Enqueue([pscustomobject]@{ Text = $Text; Id = $Id })
}

function Invoke-Work {
    param ($Item)
    try {
        $res = Ask-AceBrain -UserInput $Item.Text
        if ($res.UiCommand -match '^corner (\w\w)$') { Set-Corner $matches[1] }
        elseif ($res.UiCommand -eq "mode man")       { Set-DisplayMode "mini_man" }
        elseif ($res.UiCommand -eq "mode island")    { Set-DisplayMode "island" }
        if ($res.TypeText) { $script:PendingType = $res.TypeText; $script:TypeAt = (Get-Date).AddSeconds(3) }
        Set-AceState "acting" $res.Reply
        Speak-Ace $res.Reply -Async
        $script:IdleAt = (Get-Date).AddSeconds(3)
        if ($Item.Id) {
            @{ id = $Item.Id; status = "ok"; input = $Item.Text; reply = $res.Reply; time = (Get-Date).ToString("o") } | ConvertTo-Json | Set-Content -Path $script:ResponseFile -Force -Encoding UTF8
        }
    } catch {
        Write-AceLog "Work error: $($_.Exception.Message)"
        Set-AceState "idle" "Error"
        if ($Item.Id) { @{ id = $Item.Id; status = "error"; reply = $_.Exception.Message } | ConvertTo-Json | Set-Content -Path $script:ResponseFile -Force }
    }
}

# --- UI Event Bindings ---
function Toggle-AvatarColor {
    $isDark = ($ui.AvatarHead.Fill.ToString() -eq "#FF151515")
    $newFill = if ($isDark) { $script:Brush.ConvertFromString("#FAFAFA") } else { $script:Brush.ConvertFromString("#151515") }
    $eyeFill = if ($isDark) { $script:Brush.ConvertFromString("#111111") } else { $script:Brush.ConvertFromString("#FAFAFA") }
    
    if ($ui.AvatarHead) { $ui.AvatarHead.Fill = $newFill }
    if ($ui.AvatarBody) { $ui.AvatarBody.Fill = $newFill }
    if ($ui.LeftArm) { $ui.LeftArm.Fill = $newFill }
    if ($ui.RightArm) { $ui.RightArm.Fill = $newFill }
    if ($ui.AvatarLeftLeg) { $ui.AvatarLeftLeg.Fill = $newFill }
    if ($ui.AvatarRightLeg) { $ui.AvatarRightLeg.Fill = $newFill }
    if ($ui.LeftEye) { $ui.LeftEye.Fill = $eyeFill }
    if ($ui.RightEye) { $ui.RightEye.Fill = $eyeFill }
    if ($ui.AvatarTie) { $ui.AvatarTie.Fill = $eyeFill }
}

if ($ui.BtnRunCmd) { $ui.BtnRunCmd.Add_Click({ $t = $ui.CmdInput.Text; $ui.CmdInput.Text = ""; Submit-Input $t }) }
if ($ui.CmdInput) { $ui.CmdInput.Add_KeyDown({ if ($_.Key -eq "Return") { $t = $ui.CmdInput.Text; $ui.CmdInput.Text = ""; Submit-Input $t } }) }
if ($ui.AmbientInput) { $ui.AmbientInput.Add_KeyDown({ if ($_.Key -eq "Return") { $t = $ui.AmbientInput.Text; $ui.AmbientInput.Text = ""; Submit-Input $t } }) }

if ($ui.BtnMic) { $ui.BtnMic.Add_Click({ Set-Mic (-not $global:AceIsListening) }) }
if ($ui.BtnScreenshot) { $ui.BtnScreenshot.Add_Click({ Submit-Input "screenshot" }) }
if ($ui.BtnBrowser) { $ui.BtnBrowser.Add_Click({ Submit-Input "open browser" }) }
if ($ui.BtnMode) { $ui.BtnMode.Add_Click({ Set-DisplayMode "ambient" }) }
if ($ui.BtnPrompts) { $ui.BtnPrompts.Add_Click({ Speak-Ace "I don't have saved prompts yet." -Async }) }
if ($ui.BtnSettings) { $ui.BtnSettings.Add_Click({ Submit-Input "open settings" }) }
if ($ui.BtnToggleColor) { $ui.BtnToggleColor.Add_Click({ Toggle-AvatarColor }) }
if ($ui.BtnAutomations) { $ui.BtnAutomations.Add_Click({ Speak-Ace "Automations not configured." -Async }) }
if ($ui.BtnSleep) { $ui.BtnSleep.Add_Click({ Speak-Ace "Later bro." ; $window.Close() }) }

if ($ui.BtnNavSolo) { $ui.BtnNavSolo.Add_Click({ Set-DisplayMode "mini_man" }) }
if ($ui.BtnNavIsland) { $ui.BtnNavIsland.Add_Click({ Set-DisplayMode "island" }) }
if ($ui.BtnNavBlock) { $ui.BtnNavBlock.Add_Click({ Set-DisplayMode "block" }) }
if ($ui.BtnNavExit) { $ui.BtnNavExit.Add_Click({ Speak-Ace "Later bro." ; $window.Close() }) }

if ($ui.AvatarViewbox) {
    $ui.AvatarViewbox.Add_MouseLeftButtonDown({
        $_.Handled = $true
        $beforeX = $window.Left
        $beforeY = $window.Top
        try { $window.DragMove() } catch {}
        if ([math]::Abs($window.Left - $beforeX) -gt 3 -or [math]::Abs($window.Top - $beforeY) -gt 3) { 
            $script:FreeMove = $true 
        } else {
            if ($script:S.displayMode -eq "mini_man") { Set-DisplayMode "block" }
            elseif ($script:S.displayMode -eq "block") { Set-DisplayMode "island" }
            else { Set-DisplayMode "mini_man" }
        }
    })
}
if ($ui.TrayBorder) {
    $ui.TrayBorder.Add_MouseLeftButtonDown({
        $beforeX = $window.Left
        $beforeY = $window.Top
        try { $window.DragMove() } catch {}
        if ([math]::Abs($window.Left - $beforeX) -gt 3 -or [math]::Abs($window.Top - $beforeY) -gt 3) { 
            $script:FreeMove = $true 
        } else {
            if ($script:S.displayMode -eq "mini_man") { Set-DisplayMode "block" }
            elseif ($script:S.displayMode -eq "block") { Set-DisplayMode "island" }
            else { Set-DisplayMode "mini_man" }
        }
    })
}
$window.Add_SizeChanged({ Update-Position })

# ---------------- Main loop ----------------
$script:Tick = 0
$script:IdleAt = [datetime]::MaxValue
$timer = New-Object System.Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromMilliseconds(120)
$timer.Add_Tick({
    try {
        $script:Tick++
        $now = Get-Date

        if ($script:WorkQueue.Count -gt 0) { Invoke-Work $script:WorkQueue.Dequeue() }

        if ($global:AceIsListening) {
            foreach ($v in (Read-AceVoiceInput)) {
                switch ($v.Kind) {
                    "detected" { if ($ui.IslandStatusText.Text -notlike "Thinking*") { Set-AceState "listening" "Listening..." } }
                    "wake"     { Set-AceState "listening" "I'm listening..."; $script:IdleAt = $now.AddSeconds(10) }
                    "command"  { Submit-Input $v.Text }
                }
            }
        }

        if ($script:Tick % 2 -eq 0 -and (Test-Path $script:QueueFile)) {
            $raw = Get-Content -Raw $script:QueueFile -ErrorAction SilentlyContinue
            if (-not [string]::IsNullOrWhiteSpace($raw)) {
                Set-Content -Path $script:QueueFile -Value "" -Force
                $obj = $raw | ConvertFrom-Json
                if ($obj.command) { Submit-Input $obj.command $obj.id }
            }
        }

        if ($script:PendingType -and $now -ge $script:TypeAt) {
            $txt = $script:PendingType; $script:PendingType = $null; $script:TypeAt = [datetime]::MaxValue
            Set-AceState "acting" "Typing..."
            Invoke-AceType -Text $txt
            Set-AceState "idle" "Typed it."
        }

        if ($now -gt $script:IdleAt -and -not (Test-AceSpeaking)) {
            $script:IdleAt = [datetime]::MaxValue
            Set-AceState "idle" $(if ($global:AceIsListening) { "Say 'hey Ace...'" } else { "Ready." })
        }
        
        # Real-time Audio Waveform scaling
        $level = 0
        if ($global:AceRecognizer -and $global:AceIsListening) { try { $level = $global:AceRecognizer.AudioLevel } catch {} }

        $rnd = New-Object Random
        if ($global:AceIsSpeaking) {
            if ($ui.PW1) {
                $ui.PW1.Height = $rnd.Next(2, 20); $ui.PW2.Height = $rnd.Next(4, 25); $ui.PW3.Height = $rnd.Next(8, 30)
                $ui.PW4.Height = $rnd.Next(10, 35); $ui.PW5.Height = $rnd.Next(8, 30); $ui.PW6.Height = $rnd.Next(4, 25)
                $ui.PW7.Height = $rnd.Next(2, 20)
            }
            if ($ui.BW1) {
                $ui.BW1.Height = $rnd.Next(4, 30); $ui.BW2.Height = $rnd.Next(10, 35); $ui.BW3.Height = $rnd.Next(15, 40)
                $ui.BW4.Height = $rnd.Next(20, 50); $ui.BW5.Height = $rnd.Next(30, 60); $ui.BW6.Height = $rnd.Next(20, 50)
                $ui.BW7.Height = $rnd.Next(15, 40); $ui.BW8.Height = $rnd.Next(10, 35); $ui.BW9.Height = $rnd.Next(4, 30)
            }
            if ($ui.AW1) {
                $ui.AW1.Height = $rnd.Next(6, 40); $ui.AW2.Height = $rnd.Next(14, 50); $ui.AW3.Height = $rnd.Next(26, 60)
                $ui.AW4.Height = $rnd.Next(42, 80); $ui.AW5.Height = $rnd.Next(56, 100); $ui.AW6.Height = $rnd.Next(42, 80)
                $ui.AW7.Height = $rnd.Next(26, 60); $ui.AW8.Height = $rnd.Next(14, 50); $ui.AW9.Height = $rnd.Next(6, 40)
            }
        } elseif ($level -gt 2) {
            # Scale listening waveform based on real-time microphone level (0-100)
            $factor = [math]::Min(1.0, ($level / 30.0))
            $f = { param($max, $min) return [math]::Max($min, $max * $factor + $rnd.Next(-2, 3)) }
            
            if ($ui.PW1) {
                $ui.PW1.Height = &$f 20 2; $ui.PW2.Height = &$f 25 6; $ui.PW3.Height = &$f 30 10
                $ui.PW4.Height = &$f 35 12; $ui.PW5.Height = &$f 30 10; $ui.PW6.Height = &$f 25 6
                $ui.PW7.Height = &$f 20 2
            }
            if ($ui.BW1) {
                $ui.BW1.Height = &$f 30 4; $ui.BW2.Height = &$f 35 10; $ui.BW3.Height = &$f 40 18
                $ui.BW4.Height = &$f 50 28; $ui.BW5.Height = &$f 60 36; $ui.BW6.Height = &$f 50 28
                $ui.BW7.Height = &$f 40 18; $ui.BW8.Height = &$f 35 10; $ui.BW9.Height = &$f 30 4
            }
            if ($ui.AW1) {
                $ui.AW1.Height = &$f 40 6; $ui.AW2.Height = &$f 50 14; $ui.AW3.Height = &$f 60 26
                $ui.AW4.Height = &$f 80 42; $ui.AW5.Height = &$f 100 56; $ui.AW6.Height = &$f 80 42
                $ui.AW7.Height = &$f 60 26; $ui.AW8.Height = &$f 50 14; $ui.AW9.Height = &$f 40 6
            }
        } else {
            if ($ui.PW1) {
                $ui.PW1.Height = 2; $ui.PW2.Height = 6; $ui.PW3.Height = 12; $ui.PW4.Height = 18; $ui.PW5.Height = 12
                $ui.PW6.Height = 6; $ui.PW7.Height = 2
            }
            if ($ui.BW1) {
                $ui.BW1.Height = 4; $ui.BW2.Height = 10; $ui.BW3.Height = 18; $ui.BW4.Height = 28; $ui.BW5.Height = 36
                $ui.BW6.Height = 28; $ui.BW7.Height = 18; $ui.BW8.Height = 10; $ui.BW9.Height = 4
            }
            if ($ui.AW1) {
                $ui.AW1.Height = 6; $ui.AW2.Height = 14; $ui.AW3.Height = 26; $ui.AW4.Height = 42; $ui.AW5.Height = 56
                $ui.AW6.Height = 42; $ui.AW7.Height = 26; $ui.AW8.Height = 14; $ui.AW9.Height = 6
            }
        }

        if ($script:Tick % 25 -eq 0 -and $ui.LeftEye) { $ui.LeftEye.Height = 2; $ui.RightEye.Height = 2 }
        elseif ($script:Tick % 25 -eq 1 -and $ui.LeftEye) { $ui.LeftEye.Height = 10; $ui.RightEye.Height = 10 }
        
        if (Test-AceSpeaking -and $ui.RightArm) {
            $ui.RightArm.SetValue([System.Windows.Controls.Canvas]::TopProperty, [double]$(if ($script:Tick % 4 -lt 2) { 45 } else { 50 }))
        } elseif ($ui.RightArm) { $ui.RightArm.SetValue([System.Windows.Controls.Canvas]::TopProperty, [double]50) }

        if ($script:S.displayMode -eq "ambient" -and $script:Tick % 100 -eq 0 -and $ui.AmbientClock) {
            $ui.AmbientClock.Text = $now.ToString("h:mm")
            $ui.AmbientAmPm.Text = $now.ToString("tt")
            $ui.AmbientDate.Text = $now.ToString("dddd, MMMM d")
        }

        $p = Get-AceProfile
        if ($p -and $p.autonomyMode -ne "silent_executor" -and $script:S.nudgeMinutes -gt 0 -and
            ($now - $script:LastActivity).TotalMinutes -ge $script:S.nudgeMinutes) {
            $script:LastActivity = $now
            $msg = Pick @("Yo $(Get-AceUserName), you good? Need me to open anything?", "Been quiet over there. What are we working on?", "Reminder: drink some water, bro. Anything I can handle for you?")
            Speak-Ace $msg -Async
        }
    } catch { Write-AceLog "Tick error: $($_.Exception.Message)" }
})

# --- Application Lifecycle ---
$window.Add_Loaded({
    try {
        Initialize-AceSpeech
        Set-DisplayMode $script:S.displayMode
        Update-Position
        if ($script:S.voiceEnabled) { Set-Mic $true } else { Set-Mic $false }
        $n = Get-AceUserName
        $greet = Pick @("Yo $n, Ace is online.", "What's good $n! I'm up.")
        Set-AceState "idle" $greet; Speak-Ace $greet -Async
        $script:IdleAt = (Get-Date).AddSeconds(4)
        $timer.Start()
    } catch { Write-AceLog "Loaded error: $($_.Exception.Message)" }
})
$window.Add_Closing({
    $timer.Stop(); Stop-AceVoiceListener
})

try { $window.ShowDialog() | Out-Null } catch { Write-AceLog "Fatal: $($_.Exception.Message)" }
