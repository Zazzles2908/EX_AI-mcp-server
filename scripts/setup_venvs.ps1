param(
  [string]$Python = "python"
)

# Create venvs directory
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Split-Path -Parent $root
$venvs = Join-Path $proj "venvs"
New-Item -ItemType Directory -Path $venvs -Force | Out-Null

# Base
$base = Join-Path $venvs "base"
$moon = Join-Path $venvs "moonshot"
$zhipu = Join-Path $venvs "zhipuai"

$envs = @($base, $moon, $zhipu)
foreach ($e in $envs) { New-Item -ItemType Directory -Path $e -Force | Out-Null }

Write-Host "Creating base venv..."
& $Python -m venv $base
Write-Host "Installing base deps..."
& (Join-Path $base "Scripts\python.exe") -m pip install -U pip
& (Join-Path $base "Scripts\python.exe") -m pip install -e .

Write-Host "Creating Moonshot venv..."
& $Python -m venv $moon
& (Join-Path $moon "Scripts\python.exe") -m pip install -U pip
& (Join-Path $moon "Scripts\python.exe") -m pip install -e .[moonshot]

Write-Host "Creating ZhipuAI venv..."
& $Python -m venv $zhipu
& (Join-Path $zhipu "Scripts\python.exe") -m pip install -U pip
& (Join-Path $zhipu "Scripts\python.exe") -m pip install -e .[zhipuai]

Write-Host "Done. Activate with:"
Write-Host "  base:    venvs/base/Scripts/activate"
Write-Host "  moonshot: venvs/moonshot/Scripts/activate"
Write-Host "  zhipuai:  venvs/zhipuai/Scripts/activate"

