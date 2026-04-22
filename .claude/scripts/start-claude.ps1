# Start-ClaudeSession.ps1
# Automates the full Claude Code session startup sequence.
# Usage: .\Start-ClaudeSession.ps1 [project-name]
# If no project name is provided, prompts interactively.

param(
    [string]$ProjectName
)

$ErrorActionPreference = "Stop"
$ProjectsRoot = "C:\Development\projects"
$ConfigRepo = "$ProjectsRoot\claude-config"

# --- Prompt for project name if not provided ---
if (-not $ProjectName) {
    Write-Host "`nAvailable projects:" -ForegroundColor Cyan
    Get-ChildItem -Path $ProjectsRoot -Directory |
        Sort-Object Name |
        ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    Write-Host ""
    $ProjectName = Read-Host "Project name"
    if (-not $ProjectName) {
        Write-Host "No project name provided. Exiting." -ForegroundColor Red
        exit 1
    }
}

$ProjectPath = "$ProjectsRoot\$ProjectName"

if (-not (Test-Path $ProjectPath)) {
    Write-Host "Project not found: $ProjectPath" -ForegroundColor Red
    exit 1
}

# --- Step 1: Sync claude-config ---
Write-Host "`n[1/5] Syncing claude-config..." -ForegroundColor Yellow
Push-Location $ConfigRepo
try {
    git pull --quiet
    Write-Host "  Config synced." -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not pull claude-config. Continuing with local copy." -ForegroundColor DarkYellow
}
Pop-Location

# --- Step 2: Verify symlinks ---
Write-Host "[2/5] Checking config symlinks..." -ForegroundColor Yellow
$symlinks = Get-ChildItem ~\.claude -ErrorAction SilentlyContinue |
    Where-Object { $_.LinkType -eq "SymbolicLink" }
if ($symlinks) {
    $symlinks | ForEach-Object {
        Write-Host "  $($_.Name) -> $($_.Target)" -ForegroundColor Green
    }
} else {
    Write-Host "  Warning: No symlinks found in ~/.claude. Skills may not load." -ForegroundColor DarkYellow
    Write-Host "  Fix: ln -s $ConfigRepo\commands ~\.claude\commands" -ForegroundColor Gray
    Write-Host "  Fix: ln -s $ConfigRepo\skills ~\.claude\skills" -ForegroundColor Gray
}

# Check user settings for skill-breaking flags
$SettingsFile = "$env:USERPROFILE\.claude\settings.json"
if (Test-Path $SettingsFile) {
    try {
        $Settings = Get-Content $SettingsFile -Raw | ConvertFrom-Json
        if ($Settings.disableSkillShellExecution -eq $true) {
            Write-Host "  Warning: disableSkillShellExecution=true in ~\.claude\settings.json" -ForegroundColor Red
            Write-Host "  Breaks /code-cleanup --fix, /code-review --verify, and /resume-work deep." -ForegroundColor Gray
            Write-Host "  Fix: set it to false or remove the key." -ForegroundColor Gray
        }
    } catch {
        # Silently skip if settings.json isn't parseable
    }
}

# --- Step 3: Navigate to project and pull ---
Write-Host "[3/5] Opening project: $ProjectName" -ForegroundColor Yellow
Set-Location $ProjectPath

if (Test-Path "$ProjectPath\.git") {
    Write-Host "  Pulling latest changes..." -ForegroundColor Gray
    try {
        git pull --quiet
        Write-Host "  Project synced." -ForegroundColor Green
    } catch {
        Write-Host "  Warning: Could not pull. Continuing with local state." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  Not a git repo — skipping pull." -ForegroundColor Gray
}

# --- Step 4: Update Claude Code ---
Write-Host "[4/5] Checking for Claude Code updates..." -ForegroundColor Yellow
try {
    claude update 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
} catch {
    Write-Host "  Warning: Could not check for updates." -ForegroundColor DarkYellow
}

# --- Step 5: Launch Claude Code with /resume-work ---
Write-Host "[5/5] Launching Claude Code..." -ForegroundColor Yellow
Write-Host "  Tip: Run /resume-work to get up to speed." -ForegroundColor Gray
Write-Host ""
claude