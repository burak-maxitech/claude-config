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

# --- Project picker (numbered selection if no name given) ---
if (-not $ProjectName) {
    $projects = @(Get-ChildItem -Path $ProjectsRoot -Directory | Sort-Object Name)
    if ($projects.Count -eq 0) {
        Write-Host "No projects found in $ProjectsRoot. Exiting." -ForegroundColor Red
        exit 1
    }
    Write-Host "`nWhich project do you want to work on today?" -ForegroundColor Cyan
    for ($i = 0; $i -lt $projects.Count; $i++) {
        Write-Host ("  {0}-{1}" -f ($i + 1), $projects[$i].Name) -ForegroundColor Gray
    }
    Write-Host ""
    $sel = Read-Host "Enter number"
    if ($sel -match '^\d+$' -and [int]$sel -ge 1 -and [int]$sel -le $projects.Count) {
        $ProjectName = $projects[[int]$sel - 1].Name
    } elseif ($sel -and (Test-Path "$ProjectsRoot\$sel")) {
        $ProjectName = $sel   # typed a name instead of a number — accept it
    } else {
        Write-Host "Invalid selection: '$sel'. Exiting." -ForegroundColor Red
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
# NOTE: git is a native exe — failures surface via $LASTEXITCODE, NOT exceptions,
# so try/catch can't catch them. Gate the success message on $LASTEXITCODE instead.
if (Test-Path "$ConfigRepo\.git") {
    git -C $ConfigRepo pull --stat
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  claude-config clone synced." -ForegroundColor Green
    } else {
        Write-Host "  Could not pull claude-config clone (exit $LASTEXITCODE) — continuing." -ForegroundColor DarkGray
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
    git pull --stat
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Project synced." -ForegroundColor Green
    } else {
        Write-Host "  Could not pull (exit $LASTEXITCODE) — continuing with local state." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  Not a git repo — skipping pull." -ForegroundColor Gray
}

# --- Step 4: Update Claude Code ---
Write-Host "[4/5] Checking for Claude Code updates..." -ForegroundColor Yellow
claude update 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Could not check for updates (exit $LASTEXITCODE)." -ForegroundColor DarkYellow
}

# --- Step 5: Launch Claude Code ---
Write-Host "[5/5] Launching Claude Code..." -ForegroundColor Yellow
Write-Host "  Tip: run /bx:resume to get up to speed." -ForegroundColor Gray
Write-Host ""
claude
