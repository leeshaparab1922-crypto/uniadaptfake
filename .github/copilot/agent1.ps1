param([string]$Prompt = 'Plan the next phase, then stop for human approval.')
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$previousRestriction = $env:UNIADAPT_AGENT1_SESSION
try {
    $env:UNIADAPT_AGENT1_SESSION = '1'
    & copilot -C $repoRoot --no-auto-update --agent=phase-planner-implementer --disable-builtin-mcps '--deny-tool=shell(git push)' '--deny-tool=shell(gh pr:*)' -i $Prompt
    $copilotExit = $LASTEXITCODE
} finally {
    $env:UNIADAPT_AGENT1_SESSION = $previousRestriction
}
exit $copilotExit
