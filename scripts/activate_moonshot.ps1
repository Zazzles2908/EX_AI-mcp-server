$env:VIRTUAL_ENV = Join-Path (Get-Location) "venvs/moonshot"
$activate = Join-Path $env:VIRTUAL_ENV "Scripts/Activate.ps1"
. $activate

