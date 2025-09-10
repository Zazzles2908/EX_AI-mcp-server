param(
  [string]$Src = "C:\\Project\\zen-mcp-server",
  [string]$Dst = "C:\\Project\\EX-AI-MCP-Server"
)

$ErrorActionPreference = 'Stop'

Write-Host "=== EX-AI Copier ==="
Write-Host "Source:      $Src"
Write-Host "Destination: $Dst"

if (-not (Test-Path $Src)) {
  Write-Error "Source folder not found: $Src"
  exit 1
}

New-Item -ItemType Directory -Path $Dst -Force | Out-Null
# Normalize source/destination absolute paths and build URI for robust relative paths
$srcRoot = (Resolve-Path $Src).Path
$dstRoot = (Resolve-Path $Dst).Path
$srcUri = [System.Uri](($srcRoot.TrimEnd('\') + '\'))


# Copy all content except venv/logs/caches and certain files we manage separately
$exclude = @(
  "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", ".zen_venv", "logs"
)

# Recursively copy
Get-ChildItem -Path $srcRoot -Recurse | ForEach-Object {
  $itemUri = New-Object System.Uri($_.FullName)
  $rel = [System.Uri]::UnescapeDataString($srcUri.MakeRelativeUri($itemUri).ToString()).Replace('/', '\')
  if ($exclude | ForEach-Object { $rel -like "*$_*" } | Where-Object { $_ }) { return }
  if ($_.PSIsContainer) {
    New-Item -ItemType Directory -Path (Join-Path $Dst $rel) -Force | Out-Null
  } else {
    if ($_.Name -match "\\.(pyc|pyo|log)$") { return }
    if ($_.Name -in @("mcp-config.json","mcp-config.pylauncher.json",".env",".env.example")) { return }
    Copy-Item -Path $_.FullName -Destination (Join-Path $Dst $rel) -Force
  }
}

# Ensure .env files
$envExample = Join-Path $Dst ".env.example"
$envFile = Join-Path $Dst ".env"
if (-not (Test-Path $envExample)) {
  @"
# EX-AI-MCP-Server environment (copy to .env and set values)
KIMI_API_KEY=
# KIMI_API_URL=https://api.moonshot.ai/v1
GLM_API_KEY=
# GLM_API_URL=https://api.z.ai/api/paas/v4
DEFAULT_MODEL=glm-4.5-flash
LOCALE=
MAX_MCP_OUTPUT_TOKENS=4096
# OPENROUTER_API_KEY=
# CUSTOM_API_URL=
# CUSTOM_API_KEY=
"@ | Out-File -FilePath $envExample -Encoding UTF8
}
if (-not (Test-Path $envFile)) {
  @"
# Fill in your keys
KIMI_API_KEY=
GLM_API_KEY=
DEFAULT_MODEL=glm-4.5-flash
LOCALE=
MAX_MCP_OUTPUT_TOKENS=4096
"@ | Out-File -FilePath $envFile -Encoding UTF8
}

# Write EX-AI mcp-config.json (UTF-8 without BOM)
$mcp = Join-Path $Dst "mcp-config.json"
$cwdFs = ($Dst -replace '\\','/')
$envFileFs = ((Join-Path $Dst ".env") -replace '\\','/')
$cfg = @{
  mcpServers = @{
    exai = @{
      type = "stdio"
      trust = $true
      command = "python"
      args = @("-u", "scripts/mcp_server_wrapper.py")
      cwd = $cwdFs
      env = @{
        ENV_FILE = $envFileFs
        AUGGIE_CLI = "true"
        ALLOW_AUGGIE = "true"
        PYTHONPATH = $cwdFs
        MCP_SERVER_ID = "exai-server"
        MCP_SERVER_NAME = "exai"
      }
    }
  }
}
$json = $cfg | ConvertTo-Json -Depth 6
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($mcp, $json, $utf8NoBom)

# Also write an alternative config that uses the Python launcher (py -3)
$mcpPy = Join-Path $Dst "mcp-config.pylauncher.json"
$cfgPy = $cfg | ConvertTo-Json -Depth 6 | ConvertFrom-Json
$cfgPy.mcpServers.exai.command = "py"
$cfgPy.mcpServers.exai.args = @("-3", "-u", "scripts/mcp_server_wrapper.py")
$cfgPy.mcpServers.exai.cwd = $cwdFs
$cfgPy.mcpServers.exai.env.ENV_FILE = $envFileFs
$cfgPy.mcpServers.exai.env.PYTHONPATH = $cwdFs
$jsonPy = $cfgPy | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($mcpPy, $jsonPy, $utf8NoBom)

# Patch server identity defaults to EX-AI if present
$serverPy = Join-Path $Dst "server.py"
if (Test-Path $serverPy) {
  try {
    $content = Get-Content $serverPy -Raw
    $content = $content -replace 'os.getenv\("MCP_SERVER_ID",\s*"zen-server"\)', 'os.getenv("MCP_SERVER_ID", "exai-server")'
    $content = $content -replace 'os.getenv\("MCP_SERVER_NAME",\s*"zen"\)', 'os.getenv("MCP_SERVER_NAME", "exai")'
    Set-Content -Path $serverPy -Value $content -Encoding UTF8
  } catch {
    Write-Host "WARN: Could not patch server identity defaults: $($_.Exception.Message)" -ForegroundColor Yellow
  }
}

Write-Host "Done. EX-AI at: $Dst"

