# DEPRECATION NOTICE
# E2E orchestration script deprecated in favor of EXAI MCP-first workflows.
# See docs/sweep_reports/current_exai_reviews/scripts_sweep_2025-09-15.md


[CmdletBinding()]
param(
  [string]$Src = "C:\\Project\\zen-mcp-server",
  [string]$Dst = "C:\\Project\\EX-AI-MCP-Server",
  [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Ok($m) { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Err($m) { Write-Host "[ERR] $m" -ForegroundColor Red }
function Remove-Safe([string]$Path) {
  try {
    Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
    Ok "Removed: $Path"
  } catch {
    Warn "Skip remove: $Path - $($_.Exception.Message)"
  }
}


Write-Step "EX-AI End-to-End: Copy → Diagnose → (Launch Auggie)"

# 1) Clean destination (except our config/scripts)
Write-Step "Cleaning destination (safe)"
$preserve = @('scripts','mcp-config.json','mcp-config.pylauncher.json','.env','.env.example','.gitignore','README.md','README-PUBLIC.md')
if (Test-Path $Dst) {
  Get-ChildItem $Dst -Force | Where-Object { $_.Name -notin $preserve } | ForEach-Object {
    Remove-Safe -Path $_.FullName
  }
} else {
  New-Item -Path $Dst -ItemType Directory -Force | Out-Null
}

# 2) Clone full code using robust path logic
Write-Step "Cloning from zen → EX-AI"
$clone = Join-Path $Dst "scripts/clone_from_zen.ps1"
if (!(Test-Path $clone)) { Err "clone_from_zen.ps1 missing at $clone"; exit 1 }
& powershell -NoProfile -ExecutionPolicy Bypass -File $clone -Src $Src -Dst $Dst
Ok "Clone completed"

# 3) Diagnose
Write-Step "Diagnostics"
$diag = Join-Path $Dst "scripts/exai_diagnose.py"
if (Test-Path $diag) {
  $ran = $false
  try { & py -3 $diag; $ran = $true } catch {}
  if (-not $ran) {
    try { & python $diag; $ran = $true } catch {}
  }
  if (-not $ran) { Warn "No Python runtime found (py -3 or python); skipped diagnose" }
} else { Warn "exai_diagnose.py missing" }

# 4) Launch Auggie (unless suppressed)
if (-not $NoLaunch) {
  Write-Step "Launching Auggie (EX-AI)"
  $mcp = Join-Path $Dst "mcp-config.json"
  $mcpPy = Join-Path $Dst "mcp-config.pylauncher.json"
  if ((-not (Test-Path $mcp)) -and (-not (Test-Path $mcpPy))) { Err "No MCP config found. Expected either '$mcp' or '$mcpPy'."; exit 1 }

  # Workaround: some Auggie builds choke on Windows-style backslashes and certain folder names like 'conf'.
  # Temporarily rename 'conf' → '_conf' for launch if present, then restore after.
  $confDir = Join-Path $Dst "conf"
  $confBak = Join-Path $Dst "_conf"
  $renamed = $false
  if (Test-Path $confDir) {
    try { Rename-Item -LiteralPath $confDir -NewName "_conf" -Force; $renamed = $true; Warn "Temporarily renamed 'conf' → '_conf' to avoid ignore parsing issues" } catch { Warn "Could not rename 'conf': $($_.Exception.Message)" }
  }

  try {
    $auggie = $null
    try { $auggie = (Get-Command auggie -ErrorAction SilentlyContinue).Source } catch {}
    if ($auggie) {
      # Detect available Python runner
    $usePy = $false
    try {
      $null = Get-Command py -ErrorAction Stop
      & py -3 --version *> $null
      if ($LASTEXITCODE -eq 0) { $usePy = $true }
    } catch {}

    $usePythonExe = $false
    if (-not $usePy) {
      try {
        $null = Get-Command python -ErrorAction Stop
        & python --version *> $null
        if ($LASTEXITCODE -eq 0) { $usePythonExe = $true }
      } catch {}
    }

    Ok "Found Auggie at: $auggie"
    if ($usePy -and (Test-Path $mcpPy)) {
      & $auggie --mcp-config $mcpPy
    } elseif ($usePythonExe -and (Test-Path $mcp)) {
      & $auggie --mcp-config $mcp
    } else {
      Err "No suitable Python runtime found. Install Python 3.11 or 3.12 from python.org and ensure either 'py -3 --version' or 'python --version' works."; exit 1
    }
    } else {
    Warn "Auggie not found in PATH. Trying npx..."
    $usePy = $false
    try {
      $null = Get-Command py -ErrorAction Stop
      & py -3 --version *> $null
      if ($LASTEXITCODE -eq 0) { $usePy = $true }
    } catch {}
    $usePythonExe = $false
    if (-not $usePy) {
      try {
        $null = Get-Command python -ErrorAction Stop
        & python --version *> $null
        if ($LASTEXITCODE -eq 0) { $usePythonExe = $true }
      } catch {}
    }
    if ($usePy -and (Test-Path $mcpPy)) {
      & npx @augmentcode/auggie --mcp-config $mcpPy
    } elseif ($usePythonExe -and (Test-Path $mcp)) {
      & npx @augmentcode/auggie --mcp-config $mcp
    } else {
      Err "No suitable Python runtime found. Install Python 3.11 or 3.12 from python.org and ensure either 'py -3 --version' or 'python --version' works."; exit 1
    }
  }
  } finally {
    if ($renamed -and (Test-Path $confBak)) {
      try { Rename-Item -LiteralPath $confBak -NewName "conf" -Force; Ok "Restored '_conf' → 'conf'" } catch { Warn "Could not restore 'conf': $($_.Exception.Message)" }
    }
  }
}

Ok "End-to-end script finished"

