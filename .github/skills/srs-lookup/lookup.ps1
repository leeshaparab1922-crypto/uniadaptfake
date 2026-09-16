param([string]$Query = '')
$ErrorActionPreference = 'Stop'
& python -B (Join-Path $PSScriptRoot 'lookup.py') $Query
exit $LASTEXITCODE
