<#
.SYNOPSIS
    SDLE launcher (PowerShell — Windows-native callers).

.DESCRIPTION
    Resolves a Python 3.11+ interpreter and runs scripts/sdle.py through it.
    Callers (hooks, slash commands, the skill) invoke this rather than sdle.py
    directly, because they cannot ask sdle.py where Python is.

    Resolution order: py -3 -> python3 -> python -> uv run -> refuse.
    A candidate qualifies only if it successfully REPORTS a version >= 3.11.
    Gating on a reported version rather than on the command merely existing is
    what disposes of the Windows Store stub, which resolves on PATH but is not
    an interpreter.
#>

$ErrorActionPreference = 'Continue'
$target = Join-Path $PSScriptRoot 'sdle.py'
$probe = 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)'

function Test-Interpreter {
    param([string]$Exe, [string[]]$Prefix)
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { return $false }
    try {
        & $Exe @Prefix '-c' $probe *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if ($env:SDLE_PYTHON) {
    & $env:SDLE_PYTHON $target @args
    exit $LASTEXITCODE
}

$candidates = @(
    @{ Exe = 'py';      Prefix = @('-3') },
    @{ Exe = 'python3'; Prefix = @() },
    @{ Exe = 'python';  Prefix = @() }
)

foreach ($candidate in $candidates) {
    if (Test-Interpreter -Exe $candidate.Exe -Prefix $candidate.Prefix) {
        & $candidate.Exe @($candidate.Prefix) $target @args
        exit $LASTEXITCODE
    }
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run --python 3.11 $target @args
    exit $LASTEXITCODE
}

# Refuse in the same envelope shape every other refusal uses.
@'
{
  "ok": false,
  "command": "launcher",
  "reason": "no_interpreter",
  "message": "SDLE requires Python 3.11+. Tried: py -3, python3, python, uv run. Install Python 3.11 or newer, or install uv (https://docs.astral.sh/uv/), then retry.",
  "data": {"tried": ["py -3", "python3", "python", "uv run"]}
}
'@
[Console]::Error.WriteLine('sdle: no Python 3.11+ interpreter found (tried py -3, python3, python, uv run).')
exit 1
