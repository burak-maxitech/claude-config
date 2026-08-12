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
