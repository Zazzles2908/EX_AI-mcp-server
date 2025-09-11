param(
  [switch]$Shim,
  [switch]$Restart
)

$ErrorActionPreference = "Stop"

# Resolve repo root as parent of the scripts folder containing this file
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$StopScript = Join-Path $Root "scripts\ws_stop.ps1"

Push-Location $Root
try {
  if (!(Test-Path $Py)) {
    throw "Python not found at $Py. Ensure the virtualenv exists (see run-server.sh or create .venv)."
  }
  if ($Restart) {
    Write-Host "Restart requested: stopping any running daemon..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File $StopScript | Write-Host
  }
  if ($Shim) {
    Write-Host "Starting stdio shim..." -ForegroundColor Cyan
    & $Py "scripts\run_ws_shim.py"
  } else {
    Write-Host "Starting WS daemon..." -ForegroundColor Cyan
    # If a daemon is running, stop it first for a friendly single-command start
    powershell -ExecutionPolicy Bypass -File $StopScript | Write-Host
    & $Py "scripts\run_ws_daemon.py"
  }
}
finally {
  Pop-Location
}

