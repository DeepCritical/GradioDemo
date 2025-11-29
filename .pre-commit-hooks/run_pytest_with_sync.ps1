# PowerShell wrapper for pytest runner
# Ensures uv is available and runs the Python script

param(
    [Parameter(Position=0)]
    [string]$TestType = "unit"
)

$ErrorActionPreference = "Stop"

# Check if uv is available
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv not found. Please install uv: https://github.com/astral-sh/uv"
    exit 1
}

# Get the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "run_pytest_with_sync.py"

# Run the Python script using uv
uv run python $PythonScript $TestType

exit $LASTEXITCODE

