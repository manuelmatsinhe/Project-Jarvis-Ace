$ErrorActionPreference = "Stop"

$GH_PATH = "C:\Program Files\GitHub CLI\gh.exe"
$GIT_PATH = "C:\Program Files\Git\cmd\git.exe"

# Verify Git is installed
try {
    & $GIT_PATH --version | Out-Null
    Write-Host "Git is installed." -ForegroundColor Green
} catch {
    Write-Host "Error: Git is not installed or not in PATH. Please install it from https://git-scm.com/downloads and restart this window." -ForegroundColor Red
    exit 1
}

# Verify GH is installed
if (-not (Test-Path $GH_PATH)) {
    Write-Host "Error: GitHub CLI (gh) not found at $GH_PATH." -ForegroundColor Red
    exit 1
}

# Verify GitHub Auth
try {
    & $GH_PATH auth status *> $null
} catch {
    Write-Host "You are not logged into GitHub CLI. Please run:" -ForegroundColor Yellow
    Write-Host "& `"$GH_PATH`" auth login" -ForegroundColor Cyan
    Write-Host "Follow the prompts to log in (choose Web Browser, and copy the code)." -ForegroundColor Yellow
    exit 1
}

# Configure Git user if not set
$gitEmail = & $GIT_PATH config --global user.email
if (-not $gitEmail) {
    & $GIT_PATH config --global user.email "ace@jarvis.local"
    & $GIT_PATH config --global user.name "Ace User"
}

# Initialize Git
if (-not (Test-Path ".git")) {
    & $GIT_PATH init
    & $GIT_PATH branch -M main
}

# Add and commit
& $GIT_PATH add .
try {
    & $GIT_PATH commit -m "Initial commit: Project Jarvis - Ace"
} catch {
    Write-Host "No changes to commit or commit failed."
}

# Create repo and push
Write-Host "Creating GitHub repository 'Project-Jarvis-Ace'..." -ForegroundColor Cyan
try {
    & $GH_PATH repo create Project-Jarvis-Ace --public --source=. --remote=origin --push
    Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green
} catch {
    Write-Host "Failed to create or push repository. It might already exist." -ForegroundColor Yellow
    Write-Host "Attempting to just push..." -ForegroundColor Cyan
    & $GIT_PATH push -u origin main
}
