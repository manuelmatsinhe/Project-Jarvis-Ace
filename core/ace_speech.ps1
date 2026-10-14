# Ace Voice Module
# - Text-to-speech (Ace talks)
# - Speech recognition with wake word: say "hey Ace, open notepad" or "Ace" then speak.
# Events are QUEUED (no -Action) and polled from the UI timer via Read-AceVoiceInput,
# because PowerShell -Action handlers never run while ShowDialog() is blocking.

Add-Type -AssemblyName System.Speech -ErrorAction SilentlyContinue

$global:AceSynthesizer   = $null
$global:AceRecognizer    = $null
$global:AceIsListening   = $false
$global:AceAwakeUntil    = [datetime]::MinValue
$global:AceLastSpokeAt   = [datetime]::MinValue
$global:AceVoiceError    = ""
$global:AceWakeWords     = @("ace", "hey ace", "yo ace", "okay ace", "ok ace", "hi ace")

function Initialize-AceSpeech {
    if ($global:AceSynthesizer) { return }
    try {
        $global:AceSynthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $global:AceSynthesizer.Rate = 1
        $global:AceSynthesizer.Volume = 100
        foreach ($v in $global:AceSynthesizer.GetInstalledVoices()) {
            if ($v.VoiceInfo.Name -like "*David*") { $global:AceSynthesizer.SelectVoice($v.VoiceInfo.Name); break }
        }
    } catch { $global:AceVoiceError = "TTS init failed: $($_.Exception.Message)" }
}

function Speak-Ace {
    param ([string]$Text, [switch]$Async)
    if ([string]::IsNullOrWhiteSpace($Text)) { return }
    Initialize-AceSpeech
    if (-not $global:AceSynthesizer) { return }
    $clean = $Text -replace '[\*_#`>]', '' -replace '\s+', ' '
    try {
        $global:AceSynthesizer.SpeakAsyncCancelAll()
        $global:AceLastSpokeAt = Get-Date
        if ($Async) { $global:AceSynthesizer.SpeakAsync($clean) | Out-Null }
        else { $global:AceSynthesizer.Speak($clean) }
    } catch { $global:AceVoiceError = "TTS error: $($_.Exception.Message)" }
}

function Test-AceSpeaking {
    if (-not $global:AceSynthesizer) { return $false }
    return ($global:AceSynthesizer.State -eq [System.Speech.Synthesis.SynthesizerState]::Speaking)
}

function Start-AceVoiceListener {
    param ([string]$InputWav)   # optional: feed a .wav file instead of the mic (for testing)
    Stop-AceVoiceListener
    try {
        $re = New-Object System.Speech.Recognition.SpeechRecognitionEngine
        if ($InputWav) { $re.SetInputToWaveFile($InputWav) } else { $re.SetInputToDefaultAudioDevice() }

        $wake = New-Object System.Speech.Recognition.Choices
        foreach ($w in $global:AceWakeWords) { $wake.Add($w) }

        # 1) "hey ace <anything>"
        $gbCmd = New-Object System.Speech.Recognition.GrammarBuilder
        $gbCmd.Append($wake)
        $gbCmd.AppendDictation()
        $gCmd = New-Object System.Speech.Recognition.Grammar -ArgumentList $gbCmd
        $gCmd.Name = "wake_command"

        # 2) "hey ace" alone -> Ace wakes up and listens to the next sentence
        $gbWake = New-Object System.Speech.Recognition.GrammarBuilder
        $gbWake.Append($wake)
        $gWake = New-Object System.Speech.Recognition.Grammar -ArgumentList $gbWake
        $gWake.Name = "wake"

        # 3) Free dictation (only accepted while awake)
        $gDict = New-Object System.Speech.Recognition.DictationGrammar
        $gDict.Name = "dictation"

        $re.LoadGrammar($gCmd)
        $re.LoadGrammar($gWake)
        $re.LoadGrammar($gDict)

        Register-ObjectEvent -InputObject $re -EventName SpeechRecognized -SourceIdentifier "Ace.Recognized" | Out-Null
        Register-ObjectEvent -InputObject $re -EventName SpeechDetected   -SourceIdentifier "Ace.Detected"   | Out-Null

        $re.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Multiple)
        $global:AceRecognizer = $re
        $global:AceIsListening = $true
        return $true
    } catch {
        $global:AceVoiceError = "Mic error: $($_.Exception.Message)"
        $global:AceIsListening = $false
        return $false
    }
}

function Stop-AceVoiceListener {
    Unregister-Event -SourceIdentifier "Ace.Recognized" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "Ace.Detected"   -ErrorAction SilentlyContinue
    Get-Event -ErrorAction SilentlyContinue | Where-Object { $_.SourceIdentifier -like "Ace.*" } | Remove-Event -ErrorAction SilentlyContinue
    if ($global:AceRecognizer) {
        try { $global:AceRecognizer.RecognizeAsyncCancel() } catch {}
        try { $global:AceRecognizer.Dispose() } catch {}
        $global:AceRecognizer = $null
    }
    $global:AceIsListening = $false
}

function Remove-WakeWord {
    param ([string]$Text)
    return ($Text -replace '^\s*(hey|yo|okay|ok|hi)?\s*ace\b[\s,\.!]*', '').Trim()
}

# Poll queued voice events. Returns objects: @{ Kind = 'detected'|'wake'|'command'; Text = '...' }
function Read-AceVoiceInput {
    $out = New-Object System.Collections.ArrayList
    $events = @(Get-Event -ErrorAction SilentlyContinue | Where-Object { $_.SourceIdentifier -like "Ace.*" })
    foreach ($e in $events) {
        Remove-Event -EventIdentifier $e.EventIdentifier -ErrorAction SilentlyContinue

        # Ignore everything heard while Ace is talking (+1.2s tail) so he doesn't hear himself
        $selfTalk = (Test-AceSpeaking) -or (((Get-Date) - $global:AceLastSpokeAt).TotalSeconds -lt 1.2 -and (Test-AceSpeaking))
        if ($selfTalk) { continue }

        if ($e.SourceIdentifier -eq "Ace.Detected") {
            [void]$out.Add([pscustomobject]@{ Kind = "detected"; Text = "" })
            continue
        }

        $r = $e.SourceEventArgs.Result
        if (-not $r) { continue }
        $text = [string]$r.Text
        $conf = [double]$r.Confidence
        $gram = if ($r.Grammar) { $r.Grammar.Name } else { "" }

        switch ($gram) {
            "wake" {
                if ($conf -ge 0.5) {
                    $global:AceAwakeUntil = (Get-Date).AddSeconds(10)
                    [void]$out.Add([pscustomobject]@{ Kind = "wake"; Text = "" })
                }
            }
            "wake_command" {
                if ($conf -ge 0.3) {
                    $cmd = Remove-WakeWord $text
                    if ($cmd.Length -lt 2) {
                        $global:AceAwakeUntil = (Get-Date).AddSeconds(10)
                        [void]$out.Add([pscustomobject]@{ Kind = "wake"; Text = "" })
                    } else {
                        [void]$out.Add([pscustomobject]@{ Kind = "command"; Text = $cmd })
                    }
                }
            }
            "dictation" {
                if ((Get-Date) -lt $global:AceAwakeUntil -and $conf -ge 0.15 -and $text.Trim().Length -gt 1) {
                    $global:AceAwakeUntil = [datetime]::MinValue
                    [void]$out.Add([pscustomobject]@{ Kind = "command"; Text = (Remove-WakeWord $text) })
                } elseif ($text -match '^\s*(hey |yo |ok |okay |hi )?ace\b' -and $conf -ge 0.3) {
                    $cmd = Remove-WakeWord $text
                    if ($cmd.Length -ge 2) { [void]$out.Add([pscustomobject]@{ Kind = "command"; Text = $cmd }) }
                }
            }
        }
    }
    return ,$out
}
