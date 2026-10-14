# Dev test: brain intents + end-to-end voice pipeline (TTS -> wav -> recognizer -> polled events inside a WPF dispatcher loop)
$core = Join-Path (Split-Path -Parent $PSScriptRoot) "core"
. "$core\ace_personality.ps1"; . "$core\ace_actions.ps1"; . "$core\ace_speech.ps1"; . "$core\ace_brain.ps1"

Write-Host "== BRAIN ==" -ForegroundColor Cyan
foreach ($q in "yo bro tell me a joke", "how are you doing", "what time is it", "status", "hey ace what can you do", "i'm tired", "remember that I like lofi", "what do you remember about me", "yo") {
    $r = Ask-AceBrain $q
    Write-Host ("  {0,-32} -> {1}" -f $q, $r.Reply)
}
$r = Ask-AceBrain "type hello world"; Write-Host "  type -> TypeText='$($r.TypeText)'"
$r = Ask-AceBrain "corner bl";        Write-Host "  corner -> UiCommand='$($r.UiCommand)'"

Write-Host "== VOICE ==" -ForegroundColor Cyan
$wav = Join-Path $env:TEMP "ace_voice_test.wav"
$syn = New-Object System.Speech.Synthesis.SpeechSynthesizer
$syn.Rate = -1
$syn.SetOutputToWaveFile($wav)
$syn.Speak("Hey Ace, tell me a joke.")
$syn.Speak("Hey Ace.")
$syn.Speak("What time is it?")
$syn.SetOutputToNull(); $syn.Dispose()

Add-Type -AssemblyName PresentationFramework
$ok = Start-AceVoiceListener -InputWav $wav
Write-Host "  listener started: $ok $global:AceVoiceError"
$script:got = New-Object System.Collections.ArrayList
$win = New-Object System.Windows.Window
$win.Width = 1; $win.Height = 1; $win.ShowInTaskbar = $false; $win.WindowStyle = "None"
$t = New-Object System.Windows.Threading.DispatcherTimer
$t.Interval = [TimeSpan]::FromMilliseconds(150)
$script:ticks = 0
$t.Add_Tick({
    $script:ticks++
    foreach ($v in (Read-AceVoiceInput)) { if ($v.Kind -ne "detected") { [void]$script:got.Add($v); Write-Host "  heard [$($v.Kind)] '$($v.Text)'" -ForegroundColor Green } }
    if ($script:ticks -gt 80) { $t.Stop(); $win.Close() }
})
$t.Start(); $win.ShowDialog() | Out-Null
Stop-AceVoiceListener
Write-Host "  voice events captured: $($script:got.Count)"
