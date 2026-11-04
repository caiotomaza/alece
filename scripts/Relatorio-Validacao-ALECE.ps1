# SPDX-License-Identifier: GPL-3.0-only
# Diagnostico nao destrutivo: verifica Compose, startup e prontidao.
# Nao executa suite pytest e nao modifica o banco.
[CmdletBinding()]
param([string]$Projeto = (Split-Path -Parent $PSScriptRoot))
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$exitCode = 0
$logDir = Join-Path $env:USERPROFILE 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ((Get-Date -Format 'yyyy-MM-dd_HH-mm-ss') + '.log')
if (Test-Path -LiteralPath $log) { throw "Log já existente: $log" }
Start-Transcript -Path $log -ErrorAction Stop | Out-Null
try {
    Set-Location -LiteralPath $Projeto
    if (-not (Test-Path -LiteralPath '.\compose.yaml')) { throw 'compose.yaml não encontrado no projeto.' }
    $null = Get-Command docker -ErrorAction Stop
    Write-Host "ALECE DIAGNOSTICO START: $(Get-Date -Format o) | Host: $env:COMPUTERNAME | Usuario: $env:USERNAME"
    Write-Host 'IMPORTANTE: smoke/read-only; esta operacao NAO executa pytest.'

    function Invoke-DockerCheck {
        param([string]$Titulo, [string[]]$Parametros)
        Write-Host "`n== $Titulo =="
        & docker @Parametros
        if ($LASTEXITCODE -ne 0) { throw "Falhou: $Titulo (exit $LASTEXITCODE)" }
    }
    Invoke-DockerCheck -Titulo 'Docker Compose version' -Parametros @('compose', 'version')
    Invoke-DockerCheck -Titulo 'Compose services' -Parametros @('compose', 'config', '--services')
    Invoke-DockerCheck -Titulo 'Containers (inclui one-shot)' -Parametros @('compose', 'ps', '-a')
    Invoke-DockerCheck -Titulo 'Django system check (warnings aparecem no log)' -Parametros @('compose', 'exec', '-T', 'web', 'python', 'manage.py', 'check')
    Invoke-DockerCheck -Titulo 'Migration state (sem aplicar migracoes)' -Parametros @('compose', 'exec', '-T', 'web', 'python', 'manage.py', 'migrate', '--check', '--noinput')
    Invoke-DockerCheck -Titulo 'ALECE startup checks' -Parametros @('compose', 'exec', '-T', 'web', 'python', 'manage.py', 'alece_startup_check')
    Invoke-DockerCheck -Titulo 'Prontidao HTTP interna' -Parametros @('compose', 'exec', '-T', 'web', 'python', '-c', "import urllib.request; response=urllib.request.urlopen('http://127.0.0.1:8000/saude/pronto/', timeout=5); print('HTTP',response.status); assert response.status==200")
    Write-Host "`nDIAGNOSTICO: checks concluídos sem falhas de execução. A suite de testes completa nao foi executada."
} catch {
    $exitCode = 1
    Write-Error -Message ("ALECE DIAGNOSTICO FALHOU: " + $_.Exception.Message) -ErrorAction Continue
} finally {
    Write-Host "Log do diagnostico: $log"
    Stop-Transcript | Out-Null
}
exit $exitCode
