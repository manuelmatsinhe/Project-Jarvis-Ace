# Ace Persona Calibration / Onboarding Interview
# Teaches Ace how to talk like you, type like you, and act as your virtual twin co-pilot

param (
    [switch]$VoicePrompts
)

$coreDir = $PSScriptRoot
. (Join-Path $coreDir "ace_personality.ps1")
. (Join-Path $coreDir "ace_speech.ps1")

function Run-AceInterview {
    Clear-Host
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "       PROJECT JARVIS // ACE PERSONA CALIBRATION           " -ForegroundColor Yellow -NoNewline
    Write-Host " [TWIN MODE]" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Yo! I'm Ace. Before I take over your screen and start running things," -ForegroundColor White
    Write-Host "I need to learn how you talk, how you write, and how you roll." -ForegroundColor Gray
    Write-Host ""

    if ($VoicePrompts) {
        Speak-Ace "Hey! I am Ace. Let's calibrate your virtual twin. Tell me how you like to roll." -Async
    }

    $profile = Get-AceProfile
    if (-not $profile) {
        $profile = [PSCustomObject]@{
            userName = "Bro"
            speechStyle = "casual_bro"
            catchphrases = @("Say less, bro", "On it!", "Bet")
            textStyle = "chill_lowercase"
            autonomyMode = "proactive_doer"
            favoriteApps = @("notepad", "chrome", "explorer")
            learnedWords = @("bro", "bet", "say less", "cook")
            onboardingCompleted = $false
        }
    }

    # 1. User Name / Nickname
    Write-Host "[1/5] What should I call you?" -ForegroundColor Yellow
    Write-Host "  (e.g., Bro, Boss, Chief, King, your real name)" -ForegroundColor DarkGray
    $nameInput = Read-Host "  Your name/callsign [Default: $($profile.userName)]"
    if (![string]::IsNullOrWhiteSpace($nameInput)) {
        $profile.userName = $nameInput.Trim()
    }

    # 2. Speech Style
    Write-Host ""
    Write-Host "[2/5] What's your natural speech style?" -ForegroundColor Yellow
    Write-Host "  1) Casual Bro     -> 'Say less bro', hype, energetic, loyal companion" -ForegroundColor Cyan
    Write-Host "  2) Chill Coder    -> lowercase, clean, tech-focused, no fluff" -ForegroundColor Green
    Write-Host "  3) Direct / Fast  -> razor-sharp, immediate, military-grade efficiency" -ForegroundColor Magenta
    $styleChoice = Read-Host "  Pick 1, 2, or 3 [Default: 1]"
    switch ($styleChoice.Trim()) {
        "2" { $profile.speechStyle = "chill_coder" }
        "3" { $profile.speechStyle = "direct_fast" }
        default { $profile.speechStyle = "casual_bro" }
    }

    # 3. Favorite Slang & Catchphrases
    Write-Host ""
    Write-Host "[3/5] What slang, words, or catchphrases do you use the most?" -ForegroundColor Yellow
    Write-Host "  (Type comma-separated, e.g.: bet, say less, let's cook, gg, fire, valid)" -ForegroundColor DarkGray
    $slangInput = Read-Host "  Your catchphrases"
    if (![string]::IsNullOrWhiteSpace($slangInput)) {
        $words = $slangInput -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
        if ($words.Count -gt 0) {
            $profile.learnedWords = $words
            $profile.catchphrases = $words | ForEach-Object { "$_, $($profile.userName)!" }
        }
    }

    # 4. Typing & Input Preference
    Write-Host ""
    Write-Host "[4/5] When I type text for you, how do you type?" -ForegroundColor Yellow
    Write-Host "  1) chill_lowercase (fast modern typing, all lowercase)" -ForegroundColor Cyan
    Write-Host "  2) standard_proper (proper capitalization and punctuation)" -ForegroundColor Green
    $textChoice = Read-Host "  Pick 1 or 2 [Default: 1]"
    if ($textChoice.Trim() -eq "2") {
        $profile.textStyle = "standard_proper"
    } else {
        $profile.textStyle = "chill_lowercase"
    }

    # 5. Autonomy & Proactiveness
    Write-Host ""
    Write-Host "[5/5] How should I assist you throughout the day?" -ForegroundColor Yellow
    Write-Host "  1) Proactive Doer -> I nudge you, ask what to cook next, and take initiative" -ForegroundColor Cyan
    Write-Host "  2) Silent Executor-> Only speak and act when you call me via voice or CLI" -ForegroundColor Green
    $autonomyChoice = Read-Host "  Pick 1 or 2 [Default: 1]"
    if ($autonomyChoice.Trim() -eq "2") {
        $profile.autonomyMode = "silent_executor"
    } else {
        $profile.autonomyMode = "proactive_doer"
    }

    $profile.onboardingCompleted = $true
    $profile.lastInteraction = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Save-AceProfile $profile

    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host " [OK] CALIBRATION COMPLETE! ACE IS NOW TUNED TO YOU." -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "Ace Profile Saved:" -ForegroundColor White
    Write-Host "  Callsign: $($profile.userName)" -ForegroundColor Yellow
    Write-Host "  Style   : $($profile.speechStyle)" -ForegroundColor Yellow
    Write-Host "  Slang   : $($profile.learnedWords -join ', ')" -ForegroundColor Yellow
    Write-Host "  Autonomy: $($profile.autonomyMode)" -ForegroundColor Yellow
    Write-Host ""

    $closing = Format-AceResponse -ActionType "greet"
    Write-Host "Ace: '$closing'" -ForegroundColor Cyan
    if ($VoicePrompts) {
        Speak-Ace $closing -Async
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    Run-AceInterview -VoicePrompts:$true
}
