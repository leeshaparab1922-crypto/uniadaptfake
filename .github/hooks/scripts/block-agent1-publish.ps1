# PowerShell 7+, Python 3.11+. No execution-policy changes.
$ErrorActionPreference = 'Stop'
try {
    $payload = [Console]::In.ReadToEnd()
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { $pythonCommand = Get-Command python3 -ErrorAction Stop }
    $result = $payload | & $pythonCommand.Source -B (Join-Path $PSScriptRoot 'policy.py') publish
    if ($LASTEXITCODE -ne 0) { throw 'Hook interpreter failed' }
    $result
} catch {
    '{"permissionDecision":"deny","permissionDecisionReason":"UniAdapt safety hook could not run; Python 3 is required."}'
}
exit 0
