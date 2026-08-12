# Per-project `cc` Session Name + Color — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `cc <project>` launch a Claude Code session already named after the project and colored distinctly from every other project, with no manual step.

**Architecture:** A tiny sticky-allocator function — one implementation per shell — reads a machine-local `name=color` registry, returns the project's remembered color (assigning and persisting one on first sight), and the two `cc` launchers use it to build `claude -n "<project>" "/color <color>"`. The allocator lives in its own sourceable file per shell so it can be unit-tested without launching anything.

**Tech Stack:** PowerShell 7 (`start-claude.ps1`), bash 3.2-compatible shell (`start-claude.sh`). No new dependencies — no `jq`, no Pester, no Python.

**Spec:** `docs/superpowers/specs/2026-08-12-cc-session-naming-design.md`

## Global Constraints

- **Palette, in allocation order (verbatim):** `cyan, green, blue, purple, orange, pink, yellow, red`. These are the only values `/color` accepts besides `default`; any other string is invalid.
- **Registry path:** `~/.claude/cc-session-colors` (PowerShell: `Join-Path $env:USERPROFILE '.claude\cc-session-colors'`; bash: `$HOME/.claude/cc-session-colors`).
- **Registry format:** one `name=color` per line, plus a leading comment line. Header text, identical in both shells and ASCII-only so encodings can never diverge: `# cc session colors - auto-assigned, safe to delete (colors get reassigned)`
- **Parse rules:** skip blank lines, lines starting with `#`, lines that do not contain exactly one `=`, and lines whose color is not in the palette. A malformed file degrades to an empty registry — never a fatal error. Duplicate entries for one name: first wins.
- **Failure is never fatal:** any registry read or write failure returns "no color", and the launcher then starts the session with `-n` only. A missing registry file is *not* a failure — it is an empty registry.
- **bash 3.2 compatible** (macOS ships 3.2): no `mapfile`, no `${var,,}` lowercasing, no associative arrays. `arr+=("x")` is fine. Never expand a possibly-empty array as `"${arr[@]}"` under `set -u`; index into it instead.
- **PowerShell:** never rely on `try/catch` to catch a native executable's failure — check `$LASTEXITCODE` (repo rule from S40). The allocator itself calls no native exe.
- **Resolve the script's own directory before any `cd`/`Set-Location`.** `start-claude.sh` changes directory in Step 3, so `BASH_SOURCE`-based resolution must happen at the top of the file. `$PSScriptRoot` is unaffected but is set near the top for symmetry.
- **No plugin version bump.** These scripts live in `.claude/scripts/`, outside `bx/`, so the S54 bump-on-`bx/**`-change rule does not apply. Do not touch `bx/.claude-plugin/plugin.json` or `CHANGELOG.md`.
- **Repo commit convention:** end commit messages with the trailer `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- **Version floor:** developed against Claude Code 2.1.228. `-n/--name` and `/color` both predate it comfortably; no runtime version guard is implemented because the launcher runs `claude update` on every launch.

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `.claude/scripts/session-color.ps1` | Create | PowerShell allocator. Defines `Get-CcSessionColor`; does nothing when dot-sourced. |
| `.claude/scripts/session-color.sh` | Create | bash allocator. Defines `cc_session_color`; does nothing when sourced. |
| `.claude/scripts/tests/test-session-color.ps1` | Create | Unit checks for the PowerShell allocator against temp registries. Exit 1 on any failure. |
| `.claude/scripts/tests/test-session-color.sh` | Create | The same checks for the bash allocator. Exit 1 on any failure. |
| `.claude/scripts/start-claude.ps1` | Modify | Step 5 sources the allocator and launches `claude -n <project> "/color <color>"`. |
| `.claude/scripts/start-claude.sh` | Modify | Same change, mirrored. |
| `README.md` | Modify | One paragraph in the `cc` launcher section documenting the behavior and the reset. |

Allocator and launcher are split because the spec's verification requires pointing the allocator at a temp registry path — impossible while it is inline in a script whose body launches Claude Code.

---

### Task 1: PowerShell allocator

**Files:**
- Create: `.claude/scripts/session-color.ps1`
- Test: `.claude/scripts/tests/test-session-color.ps1`

**Interfaces:**
- Consumes: nothing.
- Produces: `Get-CcSessionColor -ProjectName <string> [-RegistryPath <string>] -> [string] color name, or $null on failure`. Also defines `$CcColorPalette` (string array, allocation order) and `$CcRegistryHeader` (string). Task 3 dot-sources this file and calls `Get-CcSessionColor`.

- [ ] **Step 1: Write the failing test**

Create `.claude/scripts/tests/test-session-color.ps1`:

```powershell
# test-session-color.ps1 — unit checks for Get-CcSessionColor.
# Run: pwsh -NoProfile -File .claude/scripts/tests/test-session-color.ps1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\session-color.ps1')

$script:Failures = 0
function Assert-Equal($Expected, $Actual, $Message) {
    if ($Expected -eq $Actual) {
        Write-Host "  PASS  $Message" -ForegroundColor Green
    } else {
        Write-Host "  FAIL  $Message (expected '$Expected', got '$Actual')" -ForegroundColor Red
        $script:Failures++
    }
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("cc-color-test-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null

try {
    # --- Fresh registry: sequential assignment, stable re-reads ---
    $reg1 = Join-Path $tmp 'registry-1'
    Assert-Equal 'cyan'  (Get-CcSessionColor -ProjectName 'alpha' -RegistryPath $reg1) 'first project gets cyan'
    Assert-Equal 'green' (Get-CcSessionColor -ProjectName 'beta'  -RegistryPath $reg1) 'second project gets green'
    Assert-Equal 'cyan'  (Get-CcSessionColor -ProjectName 'alpha' -RegistryPath $reg1) 'known project keeps its color'
    $alphaLines = @(Get-Content -LiteralPath $reg1 | Where-Object { $_ -like 'alpha=*' })
    Assert-Equal 1 $alphaLines.Count 'known project is not appended twice'
    Assert-Equal $true ((Get-Content -LiteralPath $reg1)[0].StartsWith('#')) 'registry gets a header comment'

    # --- Malformed lines are ignored, not fatal ---
    $reg2 = Join-Path $tmp 'registry-2'
    Set-Content -LiteralPath $reg2 -Encoding utf8 -Value @(
        '# header', '', 'garbage-no-separator', 'weird=notacolor', 'a=b=c', 'alpha=cyan'
    )
    Assert-Equal 'cyan'  (Get-CcSessionColor -ProjectName 'alpha' -RegistryPath $reg2) 'valid entry survives malformed neighbours'
    Assert-Equal 'green' (Get-CcSessionColor -ProjectName 'beta'  -RegistryPath $reg2) 'malformed lines do not consume colors'

    # --- Palette exhausted: least-used wins, ties broken by palette order ---
    $reg3 = Join-Path $tmp 'registry-3'
    Set-Content -LiteralPath $reg3 -Encoding utf8 -Value @(
        '# header', 'p1=cyan', 'p2=green', 'p3=blue', 'p4=purple',
        'p5=orange', 'p6=pink', 'p7=yellow', 'p8=red', 'p9=cyan'
    )
    Assert-Equal 'green' (Get-CcSessionColor -ProjectName 'p10' -RegistryPath $reg3) 'ninth project reuses the least-used color'

    # --- Unwritable registry degrades to no color ---
    $blocker = Join-Path $tmp 'blocker'
    Set-Content -LiteralPath $blocker -Encoding utf8 -Value 'this is a file, not a directory'
    Assert-Equal $null (Get-CcSessionColor -ProjectName 'alpha' -RegistryPath (Join-Path $blocker 'registry')) 'unwritable registry returns null'
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:Failures -gt 0) { Write-Host "`n$script:Failures check(s) failed." -ForegroundColor Red; exit 1 }
Write-Host "`nAll checks passed." -ForegroundColor Green
```

- [ ] **Step 2: Run the test to verify it fails**

```
pwsh -NoProfile -File .claude/scripts/tests/test-session-color.ps1
```

Expected: fails immediately — the dot-source on line 3 cannot find `session-color.ps1`.

- [ ] **Step 3: Write the implementation**

Create `.claude/scripts/session-color.ps1`:

```powershell
# session-color.ps1
# Sticky per-project session color allocation for the cc launcher.
# Dot-source this file, then call Get-CcSessionColor. Sourcing has no side effects.
#
# The registry is a machine-local `name=color` file. A project keeps its color
# forever; a new project claims the first unused color. Any read/write failure
# returns $null so the caller can launch without a color instead of failing.

$CcColorPalette = @('cyan', 'green', 'blue', 'purple', 'orange', 'pink', 'yellow', 'red')
$CcRegistryHeader = '# cc session colors - auto-assigned, safe to delete (colors get reassigned)'

function Get-CcSessionColorRegistryPath {
    Join-Path $env:USERPROFILE '.claude\cc-session-colors'
}

function Get-CcSessionColor {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectName,
        [string]$RegistryPath
    )

    if (-not $RegistryPath) { $RegistryPath = Get-CcSessionColorRegistryPath }

    # --- Read. A missing file is an empty registry, not a failure. ---
    $entries = @()
    if (Test-Path -LiteralPath $RegistryPath) {
        try {
            $lines = Get-Content -LiteralPath $RegistryPath -ErrorAction Stop
        } catch {
            return $null
        }
        foreach ($line in $lines) {
            $trimmed = $line.Trim()
            if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
            $parts = $trimmed -split '='
            if ($parts.Count -ne 2) { continue }          # zero or 2+ separators
            $name = $parts[0].Trim()
            $color = $parts[1].Trim().ToLower()
            if (-not $name) { continue }
            if ($CcColorPalette -notcontains $color) { continue }
            $entries += [pscustomobject]@{ Name = $name; Color = $color }
        }
    }

    # --- A known project keeps its color, and the file is left untouched. ---
    foreach ($entry in $entries) {
        if ($entry.Name -eq $ProjectName) { return $entry.Color }
    }

    # --- First unused color, else least-used (strict < keeps palette order on ties). ---
    $color = $null
    foreach ($candidate in $CcColorPalette) {
        $used = $false
        foreach ($entry in $entries) { if ($entry.Color -eq $candidate) { $used = $true; break } }
        if (-not $used) { $color = $candidate; break }
    }
    if (-not $color) {
        $bestCount = [int]::MaxValue
        foreach ($candidate in $CcColorPalette) {
            $count = 0
            foreach ($entry in $entries) { if ($entry.Color -eq $candidate) { $count++ } }
            if ($count -lt $bestCount) { $bestCount = $count; $color = $candidate }
        }
    }

    # --- Persist. Any failure here means "no color", not a broken launch. ---
    try {
        $dir = Split-Path -Parent $RegistryPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force -ErrorAction Stop | Out-Null
        }
        if (-not (Test-Path -LiteralPath $RegistryPath)) {
            Set-Content -LiteralPath $RegistryPath -Value $CcRegistryHeader -Encoding utf8 -ErrorAction Stop
        }
        Add-Content -LiteralPath $RegistryPath -Value ("{0}={1}" -f $ProjectName, $color) -Encoding utf8 -ErrorAction Stop
    } catch {
        return $null
    }

    return $color
}
```

- [ ] **Step 4: Run the test to verify it passes**

```
pwsh -NoProfile -File .claude/scripts/tests/test-session-color.ps1
```

Expected: 8 `PASS` lines and `All checks passed.`, exit code 0. If the "ninth project" check returns `cyan` instead of `green`, the least-used comparison is using `<=` instead of `<`.

- [ ] **Step 5: Commit**

```bash
git -C C:/Development/projects/claude-config add .claude/scripts/session-color.ps1 .claude/scripts/tests/test-session-color.ps1
git -C C:/Development/projects/claude-config commit -m "feat(cc): sticky per-project session color allocator (PowerShell)"
```

---

### Task 2: bash allocator + cross-shell parity

**Files:**
- Create: `.claude/scripts/session-color.sh`
- Test: `.claude/scripts/tests/test-session-color.sh`

**Interfaces:**
- Consumes: the registry format and palette order established in Task 1. Both shells must produce byte-identical registries for the same sequence of project names.
- Produces: `cc_session_color <project-name> [registry-path]` — prints the color to stdout and returns 0; prints nothing and returns 1 on failure. Also defines `$CC_COLOR_PALETTE` (space-separated string) and `$CC_REGISTRY_HEADER`. Task 3 sources this file and calls `cc_session_color`.

- [ ] **Step 1: Write the failing test**

Create `.claude/scripts/tests/test-session-color.sh`:

```bash
#!/usr/bin/env bash
# test-session-color.sh — unit checks for cc_session_color.
# Run: bash .claude/scripts/tests/test-session-color.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/../session-color.sh"

FAILURES=0
assert_equal() {  # expected, actual, message
    if [ "$1" = "$2" ]; then
        echo "  PASS  $3"
    else
        echo "  FAIL  $3 (expected '$1', got '$2')"
        FAILURES=$((FAILURES + 1))
    fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Fresh registry: sequential assignment, stable re-reads ---
REG1="$TMP/registry-1"
assert_equal "cyan"  "$(cc_session_color alpha "$REG1")" "first project gets cyan"
assert_equal "green" "$(cc_session_color beta  "$REG1")" "second project gets green"
assert_equal "cyan"  "$(cc_session_color alpha "$REG1")" "known project keeps its color"
assert_equal "1" "$(grep -c '^alpha=' "$REG1")" "known project is not appended twice"
assert_equal "1" "$(head -n 1 "$REG1" | grep -c '^#')" "registry gets a header comment"

# --- Malformed lines are ignored, not fatal ---
REG2="$TMP/registry-2"
printf '%s\n' '# header' '' 'garbage-no-separator' 'weird=notacolor' 'a=b=c' 'alpha=cyan' > "$REG2"
assert_equal "cyan"  "$(cc_session_color alpha "$REG2")" "valid entry survives malformed neighbours"
assert_equal "green" "$(cc_session_color beta  "$REG2")" "malformed lines do not consume colors"

# --- Palette exhausted: least-used wins, ties broken by palette order ---
REG3="$TMP/registry-3"
printf '%s\n' '# header' 'p1=cyan' 'p2=green' 'p3=blue' 'p4=purple' \
              'p5=orange' 'p6=pink' 'p7=yellow' 'p8=red' 'p9=cyan' > "$REG3"
assert_equal "green" "$(cc_session_color p10 "$REG3")" "ninth project reuses the least-used color"

# --- Unwritable registry degrades to no color ---
BLOCKER="$TMP/blocker"
echo "this is a file, not a directory" > "$BLOCKER"
assert_equal "" "$(cc_session_color alpha "$BLOCKER/registry")" "unwritable registry prints nothing"

if [ "$FAILURES" -gt 0 ]; then echo ""; echo "$FAILURES check(s) failed."; exit 1; fi
echo ""; echo "All checks passed."
```

- [ ] **Step 2: Run the test to verify it fails**

```
bash .claude/scripts/tests/test-session-color.sh
```

Expected: fails on the `.` source line — `session-color.sh: No such file or directory`.

- [ ] **Step 3: Write the implementation**

Create `.claude/scripts/session-color.sh`:

```bash
#!/usr/bin/env bash
# session-color.sh
# Sticky per-project session color allocation for the cc launcher.
# Source this file, then call: cc_session_color <project-name> [registry-path]
# Sourcing has no side effects. bash 3.2 compatible (macOS ships 3.2).
#
# Prints the color on stdout and returns 0. Prints nothing and returns 1 when
# the registry cannot be read or written, so the caller can launch uncolored.

CC_COLOR_PALETTE="cyan green blue purple orange pink yellow red"
CC_REGISTRY_HEADER="# cc session colors - auto-assigned, safe to delete (colors get reassigned)"

_cc_trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "$s"
}

cc_session_color() {
    local project="$1"
    local registry="${2:-$HOME/.claude/cc-session-colors}"
    local names=() colors=()
    # Every scalar is initialised: `local x` leaves x unset, and reading an unset
    # variable under `set -u` (which start-claude.sh sets) aborts the shell.
    local line="" name="" color="" candidate="" count=0
    local chosen="" best="" best_count=-1 i=0 dir=""

    # --- Read. A missing file is an empty registry, not a failure. ---
    if [ -e "$registry" ]; then
        [ -r "$registry" ] || return 1
        while IFS= read -r line || [ -n "$line" ]; do
            line="${line%$'\r'}"                       # tolerate CRLF registries
            line="$(_cc_trim "$line")"
            [ -z "$line" ] && continue
            case "$line" in \#*) continue ;; esac
            case "$line" in *=*) ;; *) continue ;; esac
            name="$(_cc_trim "${line%%=*}")"
            color="${line#*=}"
            case "$color" in *=*) continue ;; esac      # 2+ separators
            color="$(_cc_trim "$color" | tr '[:upper:]' '[:lower:]')"
            [ -n "$name" ] || continue
            case " $CC_COLOR_PALETTE " in *" $color "*) ;; *) continue ;; esac
            names+=("$name")
            colors+=("$color")
        done < "$registry"
    fi

    # --- A known project keeps its color, and the file is left untouched. ---
    i=0
    while [ "$i" -lt "${#names[@]}" ]; do
        if [ "${names[$i]}" = "$project" ]; then
            printf '%s\n' "${colors[$i]}"
            return 0
        fi
        i=$((i + 1))
    done

    # --- First unused color, else least-used (strict < keeps palette order on ties). ---
    chosen=""; best=""; best_count=-1
    for candidate in $CC_COLOR_PALETTE; do
        count=0
        i=0
        while [ "$i" -lt "${#colors[@]}" ]; do
            if [ "${colors[$i]}" = "$candidate" ]; then count=$((count + 1)); fi
            i=$((i + 1))
        done
        if [ "$count" -eq 0 ]; then chosen="$candidate"; break; fi
        if [ "$best_count" -lt 0 ] || [ "$count" -lt "$best_count" ]; then
            best_count="$count"; best="$candidate"
        fi
    done
    [ -n "$chosen" ] || chosen="$best"

    # --- Persist. Any failure here means "no color", not a broken launch. ---
    dir="$(dirname "$registry")"
    if [ ! -d "$dir" ]; then mkdir -p "$dir" 2>/dev/null || return 1; fi
    if [ ! -e "$registry" ]; then
        printf '%s\n' "$CC_REGISTRY_HEADER" > "$registry" 2>/dev/null || return 1
    fi
    printf '%s=%s\n' "$project" "$chosen" >> "$registry" 2>/dev/null || return 1

    printf '%s\n' "$chosen"
    return 0
}
```

- [ ] **Step 4: Run the test to verify it passes**

```
bash .claude/scripts/tests/test-session-color.sh
```

Expected: 8 `PASS` lines and `All checks passed.`, exit code 0.

- [ ] **Step 5: Prove cross-shell parity**

Both shells must build an identical registry from the same project sequence. Run this from the repo root:

```bash
bash -c 'set -u; . .claude/scripts/session-color.sh; \
  for n in burakarik6 claude-config horowell kaanarik maxitech-concierge maxitech-crm-sync personal-tools venture-compass; do \
    cc_session_color "$n" /tmp/cc-parity-bash > /dev/null; done; cat /tmp/cc-parity-bash'
```

```
pwsh -NoProfile -Command ". .claude/scripts/session-color.ps1; \
  'burakarik6','claude-config','horowell','kaanarik','maxitech-concierge','maxitech-crm-sync','personal-tools','venture-compass' | \
  ForEach-Object { Get-CcSessionColor -ProjectName $_ -RegistryPath \"$env:TEMP\cc-parity-ps\" | Out-Null }; \
  Get-Content \"$env:TEMP\cc-parity-ps\""
```

Expected: both print the same 9 lines —

```
# cc session colors - auto-assigned, safe to delete (colors get reassigned)
burakarik6=cyan
claude-config=green
horowell=blue
kaanarik=purple
maxitech-concierge=orange
maxitech-crm-sync=pink
personal-tools=yellow
venture-compass=red
```

Delete both temp files afterwards. If they differ, the allocation order or the header string drifted between the two implementations — fix the bash side to match Task 1.

- [ ] **Step 6: Commit**

```bash
git -C C:/Development/projects/claude-config add .claude/scripts/session-color.sh .claude/scripts/tests/test-session-color.sh
git -C C:/Development/projects/claude-config commit -m "feat(cc): sticky per-project session color allocator (bash) + parity check"
```

---

### Task 3: Wire both launchers

**Files:**
- Modify: `.claude/scripts/start-claude.ps1` (add `$PSScriptRoot`-based sourcing near the top; replace Step 5, currently lines 117-121)
- Modify: `.claude/scripts/start-claude.sh` (add `SCRIPT_DIR` near the top; replace Step 5, currently lines 116-120)

**Interfaces:**
- Consumes: `Get-CcSessionColor` (Task 1) and `cc_session_color` (Task 2).
- Produces: the final launch command. Nothing downstream consumes it.

- [ ] **Step 1: Add script-directory resolution to `start-claude.sh`**

`SCRIPT_DIR` must be computed before Step 3's `cd "$PROJECT_PATH"`, or a relative `BASH_SOURCE` resolves against the wrong directory. Insert immediately after the `set -uo pipefail` line (line 11):

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

- [ ] **Step 2: Replace Step 5 in `start-claude.sh`**

Replace the current Step 5 block:

```bash
# --- Step 5: Launch Claude Code ---
echo -e "${YELLOW}[5/5] Launching Claude Code...${RESET}"
echo -e "  ${GRAY}Tip: run /bx:resume to get up to speed.${RESET}"
echo ""
claude
```

with:

```bash
# --- Step 5: Launch Claude Code ---
# Name the session after the project (-n also sets the terminal tab title) and
# color its prompt bar. There is no launch-time color flag, so /color rides in
# as the initial prompt; it is handled locally and costs no model turn.
SESSION_COLOR=""
if [ -f "$SCRIPT_DIR/session-color.sh" ]; then
    # shellcheck source=/dev/null
    . "$SCRIPT_DIR/session-color.sh"
    SESSION_COLOR="$(cc_session_color "$PROJECT_NAME")"
fi

if [ -n "$SESSION_COLOR" ]; then
    echo -e "${YELLOW}[5/5] Launching Claude Code as \"$PROJECT_NAME\" ($SESSION_COLOR)...${RESET}"
else
    echo -e "${YELLOW}[5/5] Launching Claude Code as \"$PROJECT_NAME\"...${RESET}"
fi
echo -e "  ${GRAY}Tip: run /bx:resume to get up to speed.${RESET}"
echo ""

if [ -n "$SESSION_COLOR" ]; then
    claude -n "$PROJECT_NAME" "/color $SESSION_COLOR"
else
    claude -n "$PROJECT_NAME"
fi
```

- [ ] **Step 3: Replace Step 5 in `start-claude.ps1`**

Replace the current Step 5 block:

```powershell
# --- Step 5: Launch Claude Code ---
Write-Host "[5/5] Launching Claude Code..." -ForegroundColor Yellow
Write-Host "  Tip: run /bx:resume to get up to speed." -ForegroundColor Gray
Write-Host ""
claude
```

with:

```powershell
# --- Step 5: Launch Claude Code ---
# Name the session after the project (-n also sets the terminal tab title) and
# color its prompt bar. There is no launch-time color flag, so /color rides in
# as the initial prompt; it is handled locally and costs no model turn.
$SessionColor = $null
$ColorHelper = Join-Path $PSScriptRoot 'session-color.ps1'
if (Test-Path $ColorHelper) {
    . $ColorHelper
    $SessionColor = Get-CcSessionColor -ProjectName $ProjectName
}

if ($SessionColor) {
    Write-Host "[5/5] Launching Claude Code as `"$ProjectName`" ($SessionColor)..." -ForegroundColor Yellow
} else {
    Write-Host "[5/5] Launching Claude Code as `"$ProjectName`"..." -ForegroundColor Yellow
}
Write-Host "  Tip: run /bx:resume to get up to speed." -ForegroundColor Gray
Write-Host ""

if ($SessionColor) {
    claude -n $ProjectName "/color $SessionColor"
} else {
    claude -n $ProjectName
}
```

`$PSScriptRoot` is an absolute path set at parse time, so Step 3's `Set-Location` cannot break it.

- [ ] **Step 4: Syntax-check both launchers without running them**

```
bash -n .claude/scripts/start-claude.sh
```

Expected: no output, exit 0.

```
pwsh -NoProfile -Command "$null = [scriptblock]::Create((Get-Content -Raw .claude/scripts/start-claude.ps1)); 'parse ok'"
```

Expected: prints `parse ok`. A syntax error throws instead.

- [ ] **Step 5: Re-run both allocator test suites**

Sourcing the helpers from the launchers must not have changed their behavior:

```
pwsh -NoProfile -File .claude/scripts/tests/test-session-color.ps1
bash .claude/scripts/tests/test-session-color.sh
```

Expected: both report `All checks passed.`

- [ ] **Step 6: MANUAL GATE — live launch check**

An agent cannot run this; it needs a real terminal. Hand it to the user with these instructions:

1. Open a fresh PowerShell window and run `cc claude-config`.
2. Confirm three things: the Step 5 line reads `Launching Claude Code as "claude-config" (<color>)...`; the prompt bar in the session is that color; the name chip / terminal tab title reads `claude-config`.
3. Open a second window, run `cc horowell`, and confirm it is a different color.
4. Confirm `~/.claude/cc-session-colors` now holds both entries.

**If the name appears but the prompt bar is NOT colored**, the interactive prompt-argument path does not run local slash commands — the one link the spec flags as unverified. Do not patch around it in the launcher. Stop, report it, and fall back to the spec's documented alternative (a custom `statusLine` that prints a per-project colored banner), which is a separate design decision the user should make.

- [ ] **Step 7: Commit**

```bash
git -C C:/Development/projects/claude-config add .claude/scripts/start-claude.ps1 .claude/scripts/start-claude.sh
git -C C:/Development/projects/claude-config commit -m "feat(cc): launch sessions named + colored per project"
```

---

### Task 4: Document the behavior

**Files:**
- Modify: `README.md` (the `cc` launcher description, currently the paragraph ending "…checks for Claude Code updates, and launches Claude Code.")

**Interfaces:**
- Consumes: the behavior shipped in Task 3.
- Produces: nothing.

- [ ] **Step 1: Extend the `cc` description**

In `README.md`, the sentence describing `cc` currently reads:

```markdown
`cc` refreshes the `bx` plugin from the marketplace, opens (and pulls) your chosen project, checks for Claude Code updates, and launches Claude Code.
```

Replace it with:

```markdown
`cc` refreshes the `bx` plugin from the marketplace, opens (and pulls) your chosen project, checks for Claude Code updates, and launches Claude Code.

Each session is launched **named after the project and color-coded**, so parallel sessions stay distinguishable: the project name shows on the prompt bar, in the `/resume` picker, and in the terminal tab title, and the prompt bar takes a per-project color. Colors are assigned automatically on a project's first launch and remembered in `~/.claude/cc-session-colors` (a plain `name=color` file — delete it to reshuffle every project). `/color` supports eight colors, so past eight projects colors start repeating; the name is what stays unique.
```

- [ ] **Step 2: Verify the claims against the shipped scripts**

Re-read the replaced paragraph next to `.claude/scripts/start-claude.ps1` Step 5. Every claim — name on prompt bar, `/resume` picker, tab title, registry path, delete-to-reset — must match what the code does. Fix the prose, not the code.

- [ ] **Step 3: Commit**

```bash
git -C C:/Development/projects/claude-config add README.md
git -C C:/Development/projects/claude-config commit -m "docs: document per-project cc session naming and coloring"
```

---

## Self-Review

**Spec coverage.** Launch command (§1) → Task 3. Registry file and format (§2) → Tasks 1–2, enforced by the parity step. Allocation algorithm, all five rules (§3) → Tasks 1–2, one test per rule. Cross-platform parity (§4) → Task 2 Step 5. Out-of-scope items → no tasks, correctly. Risk/fallback → Task 3 Step 6 states the stop condition and forbids improvising around it. Verification §1 (allocator unit check) → Tasks 1–2; §2 (live check) → Task 3 Step 6; §3 (parity) → Task 2 Step 5. Notes: no plugin bump → Global Constraints; README sentence → Task 4.

**Placeholder scan.** No TBD/TODO; every code step carries the literal code an engineer pastes, including both replaced launcher blocks in full.

**Type consistency.** `Get-CcSessionColor -ProjectName/-RegistryPath` returning a string or `$null`, and `cc_session_color <name> [registry]` printing a color or nothing with exit 1, are used identically in the tests (Tasks 1–2) and the launchers (Task 3). `$CcColorPalette` / `$CC_COLOR_PALETTE` and `$CcRegistryHeader` / `$CC_REGISTRY_HEADER` keep each shell's native naming convention and are never referenced across shells.
