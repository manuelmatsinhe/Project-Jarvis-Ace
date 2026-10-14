# Ace Brain - conversation, memory, personality and PC command routing.
# Ask-AceBrain returns: @{ Reply = "..."; TypeText = $null or "text to type after a delay"; UiCommand = $null or "corner tl"/"mode man" }

$script:BrainRoot         = Split-Path -Parent $PSScriptRoot
$script:MemoryFile        = Join-Path $script:BrainRoot "config\memory.json"
$script:BrainSettingsFile = Join-Path $script:BrainRoot "config\settings.json"

# ---------------- Memory ----------------
function Get-AceMemory {
    $m = $null
    if (Test-Path $script:MemoryFile) { try { $m = Get-Content -Raw $script:MemoryFile | ConvertFrom-Json } catch {} }
    if (-not $m) { $m = [pscustomobject]@{ history = @(); facts = @() } }
    if ($null -eq $m.history) { $m | Add-Member NoteProperty history @() -Force }
    if ($null -eq $m.facts)   { $m | Add-Member NoteProperty facts @() -Force }
    return $m
}
function Save-AceMemory { param($m) try { $m | ConvertTo-Json -Depth 6 | Set-Content -Path $script:MemoryFile -Force -Encoding UTF8 } catch {} }
function Add-AceMemory {
    param ([string]$UserMsg, [string]$AceReply)
    $m = Get-AceMemory
    $list = [System.Collections.ArrayList]@($m.history)
    [void]$list.Add([pscustomobject]@{ time = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"); user = $UserMsg; ace = $AceReply })
    while ($list.Count -gt 30) { $list.RemoveAt(0) }
    $m.history = @($list)
    Save-AceMemory $m
}
function Add-AceFact {
    param ([string]$Fact)
    $m = Get-AceMemory
    $list = [System.Collections.ArrayList]@($m.facts)
    if ($list -notcontains $Fact) { [void]$list.Add($Fact) }
    $m.facts = @($list)
    Save-AceMemory $m
}
function Get-AceUserName { $p = Get-AceProfile; if ($p -and $p.userName) { return $p.userName } else { return "bro" } }
function Get-AceBrainSettings {
    if (Test-Path $script:BrainSettingsFile) { try { return Get-Content -Raw $script:BrainSettingsFile | ConvertFrom-Json } catch {} }
    return $null
}
function Pick { param([string[]]$Options) return (Get-Random -InputObject $Options) }

# ---------------- Direct PC commands (fast path) ----------------
function Invoke-AceCommand {
    param ([string]$Text)
    $t = $Text.Trim()
    $l = $t.ToLower() -replace '^((can|could) you|please|pls|yo|bro|ace)[,\s]+', '' -replace '\s+(please|pls|for me|bro)[\.\!\?]*$', ''
    $l = $l.Trim()
    $r = @{ Handled = $false; Reply = ""; TypeText = $null; UiCommand = $null }

    if ($l -match '^corner\s+(tl|tr|bl|br)$')        { $r.Handled = $true; $r.UiCommand = "corner $($matches[1])"; $r.Reply = "Moving to $($matches[1].ToUpper())."; return $r }
    if ($l -match '^mode\s+(man|solo|mini)$')        { $r.Handled = $true; $r.UiCommand = "mode man";    $r.Reply = "Solo mode. Just me, no box."; return $r }
    if ($l -match '^mode\s+(island|hud)$')           { $r.Handled = $true; $r.UiCommand = "mode island"; $r.Reply = "Back to the island."; return $r }

    if ($l -match '^(open|launch|start|pull up|fire up)\s+(.+)$') {
        $res = Invoke-AceOpen $matches[2]
        $r.Handled = $true
        $r.Reply = if ($res -like "Couldn't*") { $res } else { Pick @("Bet. $res", "Say less. $res", "Done. $res") }
        return $r
    }
    if ($l -match '^(search|google|look up)\s+(for\s+)?(.+)$') {
        $q = $matches[3]; Start-Process ("https://www.google.com/search?q=" + [uri]::EscapeDataString($q))
        $r.Handled = $true; $r.Reply = "Googled '$q' for you."; return $r
    }
    if ($l -match '^(play|youtube|find on youtube)\s+(.+)$') {
        $q = $matches[2] -replace '\s+on youtube$', ''
        Start-Process ("https://www.youtube.com/results?search_query=" + [uri]::EscapeDataString($q))
        $r.Handled = $true; $r.Reply = "Pulling up '$q' on YouTube."; return $r
    }
    if ($t -match '^(?i)(type|write)\s+(.+)$') {
        $r.Handled = $true; $r.TypeText = $matches[2]; $r.Reply = "Click where you want it. Typing in 3 seconds."; return $r
    }
    if ($t -match '^(?i)(run|exec|execute|powershell|cmd)\s+(.+)$') {
        $cmd = $matches[2]
        try {
            $out = (Invoke-Expression $cmd 2>&1 | Out-String).Trim()
            if ($out.Length -gt 220) { $out = $out.Substring(0, 220) + "..." }
            $r.Reply = if ($out) { "Ran it. Output: $out" } else { "Ran '$cmd'. Done." }
        } catch { $r.Reply = "That command failed: $($_.Exception.Message)" }
        $r.Handled = $true; return $r
    }
    if ($l -match '^(kill|close|quit|terminate)\s+(.+)$') {
        $name = ($matches[2] -replace '\.exe$', '').Trim()
        $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
        if ($procs) { $procs | Stop-Process -Force -ErrorAction SilentlyContinue; $r.Reply = "Closed $name." } else { $r.Reply = "Nothing called '$name' is running." }
        $r.Handled = $true; return $r
    }
    if ($l -match 'screenshot|screen shot|capture (my|the) screen') {
        $p = Invoke-AceScreenshot; $r.Handled = $true; $r.Reply = "Screenshot saved in Pictures: $(Split-Path $p -Leaf)"; return $r
    }
    if ($l -match '^(mute|unmute)')                          { Invoke-AceVolume mute; $r.Handled = $true; $r.Reply = "Toggled mute."; return $r }
    if ($l -match '(volume|sound) up|louder|turn it up')     { Invoke-AceVolume up;   $r.Handled = $true; $r.Reply = "Turned it up."; return $r }
    if ($l -match '(volume|sound) down|quieter|turn it down'){ Invoke-AceVolume down; $r.Handled = $true; $r.Reply = "Turned it down."; return $r }
    if ($l -match '^(press|hit)\s+(.+)$') { Invoke-AceKeyCombo $matches[2]; $r.Handled = $true; $r.Reply = "Pressed $($matches[2])."; return $r }
    if ($l -match '\b(ram|cpu|battery|specs|pc status|system status|status)\b') {
        $m = Get-AcePcMetrics
        $bat = if ($m.Battery) { " Battery at $($m.Battery)%." } else { "" }
        $r.Handled = $true; $r.Reply = "CPU at $($m.Cpu)%, RAM at $($m.RamPercent)% ($($m.UsedRamGB) of $($m.TotalRamGB) GB).$bat"; return $r
    }
    if ($l -match '^lock (my |the )?(pc|computer|screen)') { rundll32.exe user32.dll,LockWorkStation; $r.Handled = $true; $r.Reply = "Locking it up."; return $r }
    return $r
}


# ---------------- Tool Implementations ----------------

function Get-AceWeather {
    param([string]$Location)
    try {
        $loc = if ($Location) { $Location } else { "New York" } # default location
        $geoUrl = "https://geocoding-api.open-meteo.com/v1/search?name=$([uri]::EscapeDataString($loc))&count=1"
        $geo = Invoke-RestMethod -Uri $geoUrl -TimeoutSec 5
        if (-not $geo.results) { return @{ error = "City not found" } }
        $lat = $geo.results[0].latitude
        $lon = $geo.results[0].longitude
        
        $wUrl = "https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
        $w = Invoke-RestMethod -Uri $wUrl -TimeoutSec 5
        
        $codeMap = @{
            0="Clear"; 1="Mainly clear"; 2="Partly cloudy"; 3="Overcast"; 45="Fog"; 48="Fog"; 51="Drizzle"; 53="Drizzle"; 55="Drizzle"; 61="Rain"; 63="Rain"; 65="Heavy rain"; 71="Snow"; 73="Snow"; 75="Heavy snow"; 95="Thunderstorm"
        }
        $code = [int]$w.current.weather_code
        $cond = if ($codeMap.ContainsKey($code)) { $codeMap[$code] } else { "Unknown" }
        
        return @{
            location = $geo.results[0].name
            temperature = $w.current.temperature_2m
            feels_like = $w.current.apparent_temperature
            humidity = $w.current.relative_humidity_2m
            wind_speed = $w.current.wind_speed_10m
            conditions = $cond
            today_high = $w.daily.temperature_2m_max[0]
            today_low = $w.daily.temperature_2m_min[0]
            rain_chance = $w.daily.precipitation_probability_max[0]
        }
    } catch {
        return @{ error = "Weather API failed: $($_.Exception.Message)" }
    }
}

function Get-AceTimeDate {
    return @{
        time = (Get-Date).ToString("h:mm tt")
        date = (Get-Date).ToString("yyyy-MM-dd")
        day_of_week = (Get-Date).ToString("dddd")
    }
}

function Invoke-AceWebSearch {
    param([string]$Query)
    try {
        $url = "https://html.duckduckgo.com/html/?q=$([uri]::EscapeDataString($Query))"
        $html = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10 -Headers @{ "User-Agent" = "Mozilla/5.0" }
        $matches = [regex]::Matches($html.Content, '<a class="result__snippet[^>]*>(.*?)</a>', 'IgnoreCase,Singleline')
        $results = @()
        foreach ($m in $matches) {
            $text = $m.Groups[1].Value -replace '<[^>]+>', '' -replace '&#x27;', "'" -replace '&quot;', '"'
            $results += $text.Trim()
            if ($results.Count -ge 3) { break }
        }
        if ($results.Count -eq 0) { return @{ error = "No search results found for query: $Query" } }
        return @{ results = $results }
    } catch {
        return @{ error = "Search failed: $($_.Exception.Message)" }
    }
}

# ---------------- Gemini LLM (real conversation with Tools) ----------------
function Invoke-AceGemini {
    param ([string]$UserText, [string]$ApiKey, [string]$Model = "gemini-2.5-flash")
    
    $name  = Get-AceUserName
    $p     = Get-AceProfile
    $slang = if ($p -and $p.learnedWords) { ($p.learnedWords -join ", ") } else { "bet, say less, let's cook" }
    $style = if ($p -and $p.speechStyle) { $p.speechStyle } else { "casual" }
    $mem   = Get-AceMemory
    $facts = if ($mem.facts) { ($mem.facts -join "; ") } else { "nothing yet" }

    $sys = "Name: Ace. Personality: sharp, warm, a bit witty, confident, like Jarvis. Talk in first person, directly to ${name}, in short natural sentences. Never narrate or describe yourself or the scene. No 'Ace says...' style. Match ${name}'s tone ($style). Use slang lightly: $slang. Give your own opinions and ask follow-up questions when it fits. Keep replies short by default. Be honest when you don't know something. Use tools instead of guessing. You remember this about ${name}: $facts"

    # Define tools
    $toolsObj = @(
        @{
            functionDeclarations = @(
                @{ name = "get_weather"; description = "Get current weather for a location."; parameters = @{ type = "OBJECT"; properties = @{ location = @{ type = "STRING"; description = "City name" } }; required = @("location") } },
                @{ name = "get_time_date"; description = "Get current local time and date." },
                @{ name = "web_search"; description = "Quick lookup for current facts and news. Use this to find answers on the web."; parameters = @{ type = "OBJECT"; properties = @{ query = @{ type = "STRING"; description = "Search query" } }; required = @("query") } },
                @{ name = "execute_pc_command"; description = "Execute a PC command. Valid commands: open <app/site>, search <query>, type <text>, screenshot, volume up/down, mute, status, press <keys>, corner tl/tr/bl/br, mode man/island"; parameters = @{ type = "OBJECT"; properties = @{ command = @{ type = "STRING"; description = "The command string, e.g. 'open notepad', 'type hello'" } }; required = @("command") } },
                @{ name = "remember_fact"; description = "Save a fact about the user to memory."; parameters = @{ type = "OBJECT"; properties = @{ fact = @{ type = "STRING"; description = "Short fact to remember" } }; required = @("fact") } }
            )
        }
    )

    $contents = New-Object System.Collections.ArrayList
    foreach ($h in @($mem.history | Select-Object -Last 30)) {
        if ($h.user) { [void]$contents.Add(@{ role = "user";  parts = @(@{ text = [string]$h.user }) }) }
        if ($h.ace)  { [void]$contents.Add(@{ role = "model"; parts = @(@{ text = [string]$h.ace  }) }) }
    }
    [void]$contents.Add(@{ role = "user"; parts = @(@{ text = $UserText }) })

    $loopResult = @{ Reply = ""; TypeText = $null; UiCommand = $null }
    
    # Tool execution loop (max 3 iterations to prevent infinite)
    for ($i = 0; $i -lt 3; $i++) {
        $body = @{ systemInstruction = @{ parts = @(@{ text = $sys }) }; contents = @($contents); tools = $toolsObj; generationConfig = @{ temperature = 0.8 } } | ConvertTo-Json -Depth 10
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
        
        try {
            $url  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=$ApiKey"
            $resp = Invoke-RestMethod -Uri $url -Method Post -Body $bytes -ContentType "application/json; charset=utf-8" -TimeoutSec 60
            
            $part = $resp.candidates[0].content.parts[0]
            if ($part.functionCall) {
                $fc = $part.functionCall
                $fnName = $fc.name
                $args = $fc.args
                
                # add model's functionCall to contents to maintain history
                [void]$contents.Add(@{ role = "model"; parts = @($part) })
                
                $funcResult = $null
                if ($fnName -eq "get_weather") { $funcResult = Get-AceWeather -Location $args.location }
                elseif ($fnName -eq "get_time_date") { $funcResult = Get-AceTimeDate }
                elseif ($fnName -eq "web_search") { $funcResult = Invoke-AceWebSearch -Query $args.query }
                elseif ($fnName -eq "execute_pc_command") {
                    $act = Invoke-AceCommand $args.command
                    if ($act.TypeText)  { $loopResult.TypeText = $act.TypeText }
                    if ($act.UiCommand) { $loopResult.UiCommand = $act.UiCommand }
                    $funcResult = @{ success = $act.Handled; result = $act.Reply }
                }
                elseif ($fnName -eq "remember_fact") {
                    Add-AceFact $args.fact
                    $funcResult = @{ success = $true; message = "Fact remembered." }
                } else {
                    $funcResult = @{ error = "Unknown function" }
                }
                
                # return function result to Gemini
                [void]$contents.Add(@{
                    role = "user"
                    parts = @(
                        @{
                            functionResponse = @{
                                name = $fnName
                                response = @{ name = $fnName; content = $funcResult }
                            }
                        }
                    )
                })
            } elseif ($part.text) {
                $loopResult.Reply = $part.text.Trim()
                return $loopResult
            } else {
                return $loopResult
            }
        } catch {
            $global:AceBrainError = $_.Exception.Message
            $loopResult.Reply = "I hit a snag reaching my brain APIs: $($_.Exception.Message)"
            return $loopResult
        }
    }
    return $loopResult
}

# ---------------- Offline personality ----------------
function Get-AceLocalReply {
    param ([string]$Text)
    $t = $Text.ToLower().Trim()
    $n = Get-AceUserName
    $h = (Get-Date).Hour
    $tod = if ($h -lt 12) { "morning" } elseif ($h -lt 18) { "afternoon" } else { "evening" }
    $core = ($t -replace '^(yo|hey|hi|hello|sup|ayo|ok|okay)[,!\s]+', '' -replace '^(bro|ace|man|dude)[,!\s]+', '').Trim()
    if (-not $core) { $core = $t }

    # Specific intents first, greetings last
    if ($core -match '^(my name is|call me)\s+(.+)$') {
        $newName = ($matches[2] -replace '[\.\!]+$', '').Trim()
        $p = Get-AceProfile; if ($p) { $p.userName = $newName; Save-AceProfile $p }
        return "Locked in. You're $newName from now on."
    }
    if ($core -match '^remember( that)?\s+(.+)$') { Add-AceFact $matches[2]; return (Pick @("Got it, saved.", "Noted. I won't forget that.", "Stored in the vault, $n.")) }
    if ($core -match 'what do you (remember|know) about me') {
        $f = (Get-AceMemory).facts
        if ($f) { return "Here's what I've got: " + ((@($f) | Select-Object -Last 5) -join "; ") + "." }
        return "Not much yet. Tell me stuff with 'remember that...'"
    }
    if ($core -match 'joke|make me laugh|something funny') {
        return (Pick @("Why do programmers prefer dark mode? Because light attracts bugs.",
                       "I told my PC I needed a break. It said no problem and froze.",
                       "There are 10 kinds of people: those who get binary and those who don't.",
                       "My wifi and I have a lot in common. We both drop out when things get serious."))
    }
    if ($core -match "how (are|r) (you|u)|how you doing|you good|how'?s it going|wyd|what are you doing") {
        return (Pick @("I'm good man, just chilling in the corner. How's your day going?",
                       "Vibing. CPU's cool, mood's good. What about you, ${n}?",
                       "Can't complain, I got the best seat on your screen. What are we doing today?"))
    }
    if ($core -match "i'?m (tired|exhausted|sleepy)")     { return (Pick @("Then take a break, ${n}. Want me to put on some chill music?", "Long day? Close some tabs, grab water. I'll hold it down.")) }
    if ($core -match "i'?m (sad|down|stressed|not ok|depressed)") { return "Damn, I'm sorry ${n}. Want to talk about it? I'm here, no rush." }
    if ($core -match "i'?m (happy|good|great|hyped|fine|chilling)") { return (Pick @("Love that energy. What's got you in a good mood?", "That's what I like to hear. Let's keep it rolling.")) }
    if ($core -match "i'?m bored|bored|entertain me") { return (Pick @("Say 'play lofi' and I'll throw on music, or we start a new project. Your call.", "Want a joke, some YouTube, or should we build something cool?")) }
    if ($core -match "motivat|inspire me|i can'?t do (it|this)") { return (Pick @("You've already done harder stuff than this. One step at a time, let's go.", "Bro, nobody's coming to do it for you, and that's the good news. You got this.")) }
    if ($core -match 'who (made|created|built) you') { return "You did, ${n}. Project Jarvis. I'm Ace, your guy in the corner." }
    if ($core -match 'who are you|what are you|your name') { return "I'm Ace. Your friend, your co-pilot, the little man in the corner. I open stuff, type, search, run commands, and talk when you need it." }
    if ($core -match 'what can you do|help|commands') { return "Talk to me like normal. Or say: open spotify, search something, play lofi, type hello, screenshot, volume up, status, corner bl, mode man." }
    if ($core -match "love you|you'?re (the best|awesome|cool)|good job|thank|thx|appreciate") { return (Pick @("Always, ${n}. That's what I'm here for.", "Real recognize real.", "Say less. I got you.")) }
    if ($core -match 'good night|gn|going to sleep|bye|see you|later') { return (Pick @("Later ${n}. I'll be right here.", "Sleep well, bro. Don't forget to charge your laptop.")) }
    if ($core -match 'good morning') { return "Morning ${n}! Coffee first, then we cook. What's the plan today?" }
    if ($core -match 'what time|the time') { return "It's $((Get-Date).ToString('h:mm tt')), $n." }
    if ($core -match 'what day|the date|today') { return "Today's $((Get-Date).ToString('dddd, MMMM d'))." }
    if ($t -match '^(yo|hey|hi|hello|sup|what''?s up|whats up|wassup|ayo)\b') {
        return (Pick @("Yo ${n}! Good $tod. What's the move?", "What's good ${n}! I'm here. What we getting into?", "Ayy, there he is. Talk to me."))
    }
    return (Pick @("Hmm, I'm still learning that one, ${n}. Give me a Gemini key with 'ace set-key' and I'll get way smarter. Meanwhile, what do you need on the PC?",
                   "Real. Tell me more, or tell me what to open.",
                   "I hear you. Want me to search that up for you?"))
}

# ---------------- Main entry ----------------
function Ask-AceBrain {
    param ([string]$UserInput)
    $result = @{ Reply = ""; TypeText = $null; UiCommand = $null }
    $clean = ($UserInput.Trim() -replace '^(hey|yo|ok|okay)?\s*ace[,\s]+', '').Trim()
    if (-not $clean) { $result.Reply = "Yo, I'm here. What's up?"; return $result }

    $s = Get-AceBrainSettings
    $key = if ($s -and $s.aiApiKey) { $s.aiApiKey } else { $env:GEMINI_API_KEY }
    
    if ($key) {
        $model = if ($s -and $s.aiModel) { $s.aiModel } else { "gemini-2.5-flash" }
        $aiResult = Invoke-AceGemini -UserText $clean -ApiKey $key -Model $model
        
        if ($aiResult -and $aiResult.Reply) {
            $result = $aiResult
            Add-AceMemory $clean $result.Reply
            return $result
        }
    }

    # fallback offline
    # try direct commands first
    $cmd = Invoke-AceCommand $clean
    if ($cmd.Handled) {
        $result.Reply = $cmd.Reply; $result.TypeText = $cmd.TypeText; $result.UiCommand = $cmd.UiCommand
        Add-AceMemory $clean $result.Reply
        return $result
    }
    
    $result.Reply = Get-AceLocalReply $clean
    Add-AceMemory $clean $result.Reply
    return $result
}





