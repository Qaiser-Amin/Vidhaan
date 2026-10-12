param([ValidateSet('evidence_only','lenovo_cpu','mac_m5')][string]$Profile = 'evidence_only')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (!(Test-Path $Python) -or !(Test-Path 'app.py')) { throw 'Run .\scripts\setup_windows.ps1 first in the extracted VIDHAAN project.' }
$env:VIDHAAN_PROFILE = $Profile
if (Test-Path 'data/bundled/manifest.json') {
    & $Python -m vidhaan.cli load-bundled
    if ($LASTEXITCODE -ne 0) { throw 'Bundled corpus validation/import failed.' }
}
& $Python app.py
exit $LASTEXITCODE
