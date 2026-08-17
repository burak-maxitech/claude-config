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
            # Invariant, not culture-sensitive: in a Turkish locale ToLower()
            # maps 'I' to dotless 'i', so a hand-typed PINK would never match
            # the palette and the entry would be silently dropped.
            $color = $parts[1].Trim().ToLowerInvariant()
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
        # A 0-byte registry counts as missing: an existing-but-empty file would
        # otherwise skip the header forever and leave the file unexplained.
        $needsHeader = $true
        if (Test-Path -LiteralPath $RegistryPath) {
            $needsHeader = ((Get-Item -LiteralPath $RegistryPath -ErrorAction Stop).Length -eq 0)
        }
        if ($needsHeader) {
            Set-Content -LiteralPath $RegistryPath -Value $CcRegistryHeader -Encoding utf8 -ErrorAction Stop
        }
        Add-Content -LiteralPath $RegistryPath -Value ("{0}={1}" -f $ProjectName, $color) -Encoding utf8 -ErrorAction Stop
    } catch {
        return $null
    }

    return $color
}
