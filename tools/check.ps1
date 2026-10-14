# Dev helper: ensure every script is ASCII-safe, saved as UTF-8 with BOM, and parses cleanly.
$root = Split-Path -Parent $PSScriptRoot
$bad = 0
Get-ChildItem -Path $root -Recurse -Include *.ps1 | Where-Object { $_.FullName -notlike "*\ipc\*" } | ForEach-Object {
    $text = [System.IO.File]::ReadAllText($_.FullName)
    $nonAscii = [regex]::Matches($text, '[^\x00-\x7F]')
    if ($nonAscii.Count -gt 0) { Write-Host "NON-ASCII ($($nonAscii.Count)) in $($_.Name)" -ForegroundColor Yellow }
    [System.IO.File]::WriteAllText($_.FullName, $text, (New-Object System.Text.UTF8Encoding($true)))
    $errs = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$null, [ref]$errs) | Out-Null
    if ($errs -and $errs.Count) { $bad++; Write-Host "PARSE ERROR in $($_.Name):" -ForegroundColor Red; $errs | ForEach-Object { Write-Host "   line $($_.Extent.StartLineNumber): $($_.Message)" } }
    else { Write-Host "ok  $($_.FullName.Substring($root.Length + 1))" -ForegroundColor Green }
}
if ($bad) { exit 1 }
