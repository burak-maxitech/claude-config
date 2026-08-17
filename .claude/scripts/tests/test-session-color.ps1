# test-session-color.ps1 - unit checks for Get-CcSessionColor.
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

    # --- Case-insensitive name matching (parity with the bash allocator) ---
    $regCase = Join-Path $tmp 'registry-case'
    Assert-Equal 'cyan' (Get-CcSessionColor -ProjectName 'TestProj' -RegistryPath $regCase) 'mixed-case project gets cyan'
    Assert-Equal 'cyan' (Get-CcSessionColor -ProjectName 'testproj' -RegistryPath $regCase) 'lowercase lookup finds existing mixed-case entry'
    # -clike, not -like: -like is case-insensitive and would pass either way.
    $caseLines = @(Get-Content -LiteralPath $regCase | Where-Object { $_ -clike 'TestProj=*' })
    Assert-Equal 1 $caseLines.Count 'case-insensitive lookup preserves original casing in registry'

    # --- A 0-byte registry is treated as missing, so it still gets a header ---
    $regEmpty = Join-Path $tmp 'registry-empty'
    New-Item -ItemType File -Path $regEmpty | Out-Null
    Assert-Equal 'cyan' (Get-CcSessionColor -ProjectName 'alpha' -RegistryPath $regEmpty) 'empty registry assigns cyan'
    Assert-Equal $true ((Get-Content -LiteralPath $regEmpty)[0].StartsWith('#')) '0-byte registry still gets a header'

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

# --- Regression guard: every .ps1 here must be pure ASCII ---
# These files ship without a BOM, and Windows PowerShell 5.1 decodes a BOM-less
# .ps1 as the ANSI codepage. A UTF-8 em-dash then becomes bytes ending in a
# quote character, which terminates whatever string it sits inside.
$scriptDir = Split-Path -Parent $PSScriptRoot
foreach ($ps1 in @(Get-ChildItem -Path $scriptDir -Filter *.ps1 -Recurse)) {
    $nonAscii = @([IO.File]::ReadAllBytes($ps1.FullName) | Where-Object { $_ -gt 127 }).Count
    Assert-Equal 0 $nonAscii ("{0} is pure ASCII" -f $ps1.Name)
}

if ($script:Failures -gt 0) { Write-Host "`n$script:Failures check(s) failed." -ForegroundColor Red; exit 1 }
Write-Host "`nAll checks passed." -ForegroundColor Green
