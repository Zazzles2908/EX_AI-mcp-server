$env:VIRTUAL_ENV = Join-Path (Get-Location) "venvs/zhipuai"
$activate = Join-Path $env:VIRTUAL_ENV "Scripts/Activate.ps1"
. $activate

