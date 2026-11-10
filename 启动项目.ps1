$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath "$PSScriptRoot\frontend\dist\index.html")) {
    Push-Location -LiteralPath "$PSScriptRoot\frontend"
    try {
        if (-not (Test-Path -LiteralPath '.\node_modules')) {
            & npm.cmd ci
            if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' }
        }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
    } finally { Pop-Location }
}
Write-Host '拾序股票工作台：http://127.0.0.1:8006'
& "$PSScriptRoot\.venv\Scripts\python.exe" main.py serve
