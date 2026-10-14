# Ace Personality & Persona Engine
# Adapts speech, tone, text style, and autonomy to mirror the user's virtual twin

$script:ProfilePath = Join-Path $PSScriptRoot "..\config\profile.json"

function Get-AceProfile {
    if (Test-Path $script:ProfilePath) {
        try {
            return Get-Content -Raw -Path $script:ProfilePath | ConvertFrom-Json
        } catch {
            return $null
        }
    }
    return $null
}

function Save-AceProfile {
    param ($Profile)
    try {
        $json = $Profile | ConvertTo-Json -Depth 5
        Set-Content -Path $script:ProfilePath -Value $json -Force
    } catch {
        Write-Warning "Could not save profile: $_"
    }
}

function Format-AceResponse {
    param (
        [string]$ActionType,  # e.g., 'open', 'type', 'corner', 'status', 'greet', 'nudge', 'confirm'
        [string]$Detail       # e.g., target name or text
    )

    $profile = Get-AceProfile
    $name = if ($profile -and $profile.userName) { $profile.userName } else { "bro" }
    $style = if ($profile -and $profile.speechStyle) { $profile.speechStyle } else { "casual_bro" }

    switch ($style) {
        "casual_bro" {
            switch ($ActionType) {
                "greet"   { return "Yo $name! Ace is live and locking into the corner. What's the move?" }
                "open"    { return "Say less $name, opening $Detail right now." }
                "type"    { return "Gotchu bro, typing that out for you now." }
                "corner"  { return "Swapping to $Detail corner, staying out of your way." }
                "status"  { return "All green $name. Memory chill, Ace ready for commands." }
                "nudge"   { return "Yo $name, what are we cooking up right now? Tell me what to launch." }
                "learn"   { return "Bet. Time to calibrate Ace so I think and act just like you." }
                default   { return "On it $name! $Detail" }
            }
        }
        "chill_coder" {
            switch ($ActionType) {
                "greet"   { return "systems online. ready for inputs." }
                "open"    { return "spawning $Detail..." }
                "type"    { return "injecting keystrokes." }
                "corner"  { return "relocated to $Detail." }
                "status"  { return "runtime healthy. awaiting execution." }
                "nudge"   { return "idle state detected. need anything opened?" }
                default   { return "executed: $Detail" }
            }
        }
        "direct_fast" {
            switch ($ActionType) {
                "greet"   { return "Ace active. Ready." }
                "open"    { return "Opening $Detail." }
                "type"    { return "Typing text." }
                "corner"  { return "Corner $Detail set." }
                "status"  { return "System optimal." }
                "nudge"   { return "Standing by for orders." }
                default   { return "Done: $Detail" }
            }
        }
        default {
            return "Executing $ActionType for $Detail, $name."
        }
    }
}
