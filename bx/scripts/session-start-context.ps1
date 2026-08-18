# session-start-context.ps1 - emit cheap project orientation context for Claude
#
# Wired to Claude Code's SessionStart hook on Windows. Stdout is injected into
# the session as system context before the user's first prompt.
#
# Design rules (mirror session-start-context.sh):
#   - Cheap: must complete in < 1 second on a typical repo
#   - Read-only on the repo: no writes anywhere except the harness-provided
#     $env:CLAUDE_ENV_FILE side-channel (session env persistence, CC 2.1.152+)
#   - Silent on non-repo dirs: emit nothing rather than errors
#   - Bounded: never emit more than ~50 lines (Claude reads this on every start)
#   - Manual /bx:resume still works for deep orientation (deliberate dual-path)

$ErrorActionPreference = 'SilentlyContinue'

# Persist session-wide env vars (CC 2.1.152+) - see .sh sibling for rationale
if ($env:CLAUDE_ENV_FILE) {
    Add-Content -Path $env:CLAUDE_ENV_FILE -Value 'export PYTHONIOENCODING=utf-8'
    Add-Content -Path $env:CLAUDE_ENV_FILE -Value 'export PYTHONUTF8=1'
}

# Only emit context inside a git repo
$null = git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) { exit 0 }

$repoRoot = git rev-parse --show-toplevel 2>$null
$repoName = Split-Path $repoRoot -Leaf

Write-Output "## Project orientation: $repoName"
Write-Output ""

# Branch + uncommitted files
$branch = (git rev-parse --abbrev-ref HEAD 2>$null)
if (-not $branch) { $branch = 'unknown' }
$dirtyCount = (git status --porcelain 2>$null | Measure-Object -Line).Lines
$lastCommitAge = git log -1 --format=%cr 2>$null
if (-not $lastCommitAge) { $lastCommitAge = 'unknown' }
Write-Output "- Branch: ``$branch`` | $dirtyCount uncommitted files | last commit $lastCommitAge"

# Recent commits (5 lines max)
Write-Output ""
Write-Output "**Recent commits:**"
Write-Output '```'
$log = git log --oneline -5 2>$null
if ($log) { Write-Output $log } else { Write-Output "(no commits)" }
Write-Output '```'

# Current Status + freshness. Schema v2 keeps state in docs/STATUS.md; v1 keeps
# it in CLAUDE.md. Read whichever holds it, or the banner goes silently empty.
$statusMd = Join-Path $repoRoot 'docs/STATUS.md'
$claudeMd = Join-Path $repoRoot 'CLAUDE.md'
$stateFile = $null
$stateFilePath = $null
if (Test-Path $statusMd) {
    $stateFile = 'docs/STATUS.md'
    $stateFilePath = $statusMd
} elseif (Test-Path $claudeMd) {
    $stateFile = 'CLAUDE.md'
    $stateFilePath = $claudeMd
}

if ($stateFile) {
    Write-Output ""
    Write-Output "**Project status** (from ``$stateFile``):"

    $content = Get-Content $stateFilePath -ErrorAction SilentlyContinue
    if ($content) {
        # Last Updated line
        $lastUpdated = $content | Select-String -Pattern '^Last Updated' | Select-Object -First 1
        if ($lastUpdated) { Write-Output $lastUpdated.Line }

        # Single-section extractor: a flag that turns on at "## Current Status"
        # and off at the very next "## " header. The old range match
        # ('^## [^C]' as the end pattern) could never stop at "## Completed"
        # and ran on into "## In Progress".
        $inSection = $false
        $emitted = 0
        foreach ($line in $content) {
            if ($line -match '^## Current Status') { $inSection = $true; Write-Output $line; $emitted++; continue }
            if ($inSection -and $line -match '^## ') { break }
            if ($inSection) { Write-Output $line; $emitted++; if ($emitted -ge 12) { break } }
        }

        # Stale-doc check against the file that actually carries the state.
        $stateCommit = git log -1 --format=%ct -- $stateFile 2>$null
        $headCommit = git log -1 --format=%ct 2>$null
        if ($stateCommit -and $headCommit -and ([int]$headCommit -gt [int]$stateCommit)) {
            $ageDays = [int](([int]$headCommit - [int]$stateCommit) / 86400)
            if ($ageDays -gt 2) {
                Write-Output ""
                Write-Output "_($stateFile last updated $ageDays days before the latest commit - may be stale. Run ``/bx:resume`` to verify.)_"
            }
        }
    }
}

# Open PR for this branch (best-effort via gh)
if (Get-Command gh -ErrorAction SilentlyContinue) {
    $prInfo = gh pr view --json number,state,title 2>$null
    if ($prInfo) {
        $prJson = $prInfo | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($prJson -and $prJson.number) {
            Write-Output ""
            Write-Output "- Open PR: #$($prJson.number) - $($prJson.title)"
        }
    }
}

Write-Output ""
Write-Output "_(Orientation auto-injected by ``session-start-context.ps1``. For full task hydration + docs scan, run ``/bx:resume`` explicitly.)_"
