# SPDX-License-Identifier: GPL-3.0-only
# Postgres de teste isolado, sem acesso aos volumes de produção.
param()
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$LogDir = Join-Path $env:USERPROFILE 'logs'
$ReportDir = Join-Path $env:USERPROFILE ('test-results\alece-' + $Stamp)
New-Item -ItemType Directory -Force -Path $LogDir,$ReportDir | Out-Null
$Log = Join-Path $LogDir ($Stamp + '.log')
$Project = ('alece-audit-' + (Get-Date -Format 'yyyyMMddHHmmss')).ToLowerInvariant()
$Compose = Join-Path $Root 'compose.audit.yaml'
$failed = $false
Start-Transcript -LiteralPath $Log | Out-Null
try {
    Write-Host "ALECE — Testes isolados | $Stamp | compose=$Project"
    Write-Host "Relatórios: $ReportDir"
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker indisponível. Nenhum banco foi acessado.'
    }
    & docker compose -p $Project -f $Compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw "Compose inválido: $LASTEXITCODE" }
    & docker compose -p $Project -f $Compose up --build --abort-on-container-exit --exit-code-from tests
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
        Write-Host "A suíte detectou falha (exit=$LASTEXITCODE). Extraindo evidências."
    }
} catch {
    $failed = $true
    Write-Host "Falha de execução: $_"
} finally {
    # Não remove logs, volumes, backups ou containers de testes.
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        & docker compose -p $Project -f $Compose cp tests:/app/test-results/. $ReportDir 2>&1
        if ($LASTEXITCODE -ne 0) { Write-Host 'Relatórios não puderam ser extraídos; verifique os containers preservados.' }
    }
    Write-Host "Fim: $(Get-Date -Format o)"
    Write-Host "Log de execução: $Log"
    Stop-Transcript | Out-Null
}
if ($failed) { throw "Testes não aprovados. Consulte $Log e $ReportDir" }
