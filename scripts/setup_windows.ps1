param([ValidateSet('base','dev','embeddings')][string]$Profile = 'base')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
if (!(Test-Path 'pyproject.toml') -or !(Test-Path 'app.py')) { throw 'Run this script from a complete VIDHAAN project.' }
function Checked { param([string]$Exe, [string[]]$Arguments) & $Exe @Arguments; if ($LASTEXITCODE -ne 0) { throw "Command failed: $Exe (exit $LASTEXITCODE)" } }
if (Get-Command py -ErrorAction SilentlyContinue) {
    $Version = & py -3.12 -c 'import sys; print(sys.version_info.major, sys.version_info.minor)'
    if ($LASTEXITCODE -ne 0 -or $Version.Trim() -ne '3 12') { throw 'Install Python 3.12 from python.org, including the Python launcher.' }
    Checked 'py' @('-3.12','-m','venv','.venv')
} else {
    $Version = & python -c 'import sys; print(sys.version_info.major, sys.version_info.minor)'
    if ($LASTEXITCODE -ne 0 -or $Version.Trim() -ne '3 12') { throw 'Python 3.12 is required. Install it and enable its launcher.' }
    Checked 'python' @('-m','venv','.venv')
}
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
Checked $Python @('-m','pip','install','-r',"requirements-$Profile.txt")
Checked $Python @('-m','pip','install','-e','.','--no-deps')
Checked $Python @('-m','pip','check')
if (Test-Path 'data/bundled/manifest.json') { Checked $Python @('-m','vidhaan.cli','load-bundled') }
Checked $Python @('-m','vidhaan.cli','diagnostics')
Write-Host 'Setup complete. Launch with .\scripts\run_windows.ps1. Downloads occur only during setup/acquisition/model caching.'
