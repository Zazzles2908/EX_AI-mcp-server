$ErrorActionPreference='Stop'
Write-Output '--- SYNC START ---'
$path = 'C:\Project\EX-AI-MCP-Server'
Set-Location $path

# Ensure git repo
if (-not (Test-Path -Path (Join-Path $path '.git'))) {
  git init -b main | Out-Host
  git add -A | Out-Host
  try { git commit -m 'Initial commit' | Out-Host } catch {}
}

# Determine branch
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ([string]::IsNullOrWhiteSpace($branch) -or $branch -eq 'HEAD') { $branch = 'main' }

# Ensure remote origin
$remoteUrl = 'https://github.com/Zazzles2908/EX_AI-mcp-server.git'
$remotes = git remote -v
if ($remotes -notmatch [regex]::Escape($remoteUrl)) {
  try { git remote remove origin | Out-Null } catch {}
  git remote add origin $remoteUrl | Out-Host
}

# Push with upstream
Write-Output ("PUSHING branch={0} to {1}" -f $branch, $remoteUrl)
git push -u origin $branch

# Report
$head = (git rev-parse HEAD).Trim()
Write-Output '--- SYNC DONE ---'
Write-Output (ConvertTo-Json @{ path=$path; branch=$branch; head=$head; remote=$remoteUrl })

