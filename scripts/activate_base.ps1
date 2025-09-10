$env:VIRTUAL_ENV = Join-Path (Get-Location) "venvs/base"
$activate = Join-Path $env:VIRTUAL_ENV "Scripts/Activate.ps1"
. $activate

