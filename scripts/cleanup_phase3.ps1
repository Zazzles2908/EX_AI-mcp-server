# DEPRECATION NOTICE
# Superseded by current consolidation and EXAI MCP-first workflows.
# See docs/sweep_reports/current_exai_reviews/scripts_sweep_2025-09-15.md


param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Args
)

$scriptPath = Join-Path $PSScriptRoot "cleanup_phase3.py"

# Find Python
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue) }
if (-not $python) {
  Write-Error "Python not found. Please run: python scripts\cleanup_phase3.py <mode> [options]"
  exit 1
}

# Echo what will be executed for clarity
Write-Host "[cleanup] Running:" -ForegroundColor Cyan -NoNewline; Write-Host " $($python.Path) `"$scriptPath`" $Args"

# Execute
& $python.Path $scriptPath @Args
exit $LASTEXITCODE

