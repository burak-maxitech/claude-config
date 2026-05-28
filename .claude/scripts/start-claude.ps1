# start-claude.ps1
# Automates the full Claude Code session startup sequence.
# Usage: .\start-claude.ps1 [project-name]   (no name → interactive project picker)
#
# NOTE: the bx toolkit is now a Claude Code PLUGIN (bx@burak-tools), not symlinks.
# Step 1 refreshes the plugin from the GitHub marketplace so every launch has the
# latest skills — the plugin-model equivalent of the old "git pull updates symlinks".
# (Don't want auto-updates? Delete the two `claude plugin ...` lines in Step 1.)

param(
    [string]$ProjectName
)

$ProjectsRoot = "C:\Development\projects"
$ConfigRepo = "$ProjectsRoot\claude-config"

# --- Project picker (scan ProjectsRoot if no name given) ---
if (-not $ProjectName) {
    Write-Host "`nAvailable projects:" -ForegroundColor Cyan
    Get-ChildItem -Path $ProjectsRoot -Directory |
        Sort-Object Name |
        ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor Gray }
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

# --- Step 1: Sync the bx toolkit (dev clone + installed plugin) ---
Write-Host "`n[1/5] Syncing bx toolkit..." -ForegroundColor Yellow
# 1a. Refresh the local dev clone if present (only matters when you edit skills)
if (Test-Path "$ConfigRepo\.git") {
    try {
        git -C $ConfigRepo pull --quiet
        Write-Host "  claude-config clone synced." -ForegroundColor Green
    } catch {
        Write-Host "  Could not pull claude-config clone (continuing)." -ForegroundColor DarkGray
    }
}
# 1b. Refresh the installed plugin from the GitHub marketplace (this is the live skills)
$pluginList = (claude plugin list 2>$null | Out-String)
if ($pluginList -match "bx@burak-tools") {
    claude plugin marketplace update burak-tools 2>$null | Out-Null
    claude plugin update bx 2>$null | Out-Null
    Write-Host "  bx plugin up to date." -ForegroundColor Green
}

# --- Step 2: Verify the bx plugin + skill-breaking settings ---
Write-Host "[2/5] Checking the bx plugin..." -ForegroundColor Yellow
$pluginList = (claude plugin list 2>$null | Out-String)
if ($pluginList -match "bx@burak-tools") {
    Write-Host "  bx plugin installed (skills: /bx:*)" -ForegroundColor Green
} else {
    Write-Host "  Warning: bx plugin not detected. Skills (/bx:*) may not load." -ForegroundColor DarkYellow
    Write-Host "  Fix (in Claude Code): /plugin marketplace add burak-maxitech/claude-config" -ForegroundColor Gray
    Write-Host "                        /plugin install bx@burak-tools" -ForegroundColor Gray
}

# Check user settings for skill-breaking flags
$SettingsFile = "$env:USERPROFILE\.claude\settings.json"
if (Test-Path $SettingsFile) {
    try {
        $Settings = Get-Content $SettingsFile -Raw | ConvertFrom-Json
        if ($Settings.disableSkillShellExecution -eq $true) {
            Write-Host "  Warning: disableSkillShellExecution=true in ~\.claude\settings.json" -ForegroundColor Red
            Write-Host "  Breaks /bx:clean --fix, /bx:review --verify, and /bx:resume deep." -ForegroundColor Gray
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
        Write-Host "  Could not pull (continuing with local state)." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  Not a git repo — skipping pull." -ForegroundColor Gray
}

# --- Step 4: Update Claude Code ---
Write-Host "[4/5] Checking for Claude Code updates..." -ForegroundColor Yellow
try {
    claude update 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
} catch {
    Write-Host "  Could not check for updates." -ForegroundColor DarkYellow
}

# --- Step 5: Launch Claude Code ---
Write-Host "[5/5] Launching Claude Code..." -ForegroundColor Yellow
Write-Host "  Tip: run /bx:resume to get up to speed." -ForegroundColor Gray
Write-Host ""
claude
