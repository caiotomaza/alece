#Requires -Version 5.1
<#
Corrige imagem obsoleta do web, preservando volumes e criando backups com SHA-256.
Executar no Windows PowerShell com Docker Desktop iniciado.
Nao imprime chaves secretas e nao remove volumes ou backups.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Started = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$BackupDir = Join-Path $env:USERPROFILE 'backups'
$LogDir = Join-Path $env:USERPROFILE 'logs'
New-Item -ItemType Directory -Force -Path $BackupDir, $LogDir | Out-Null
$LogFile = Join-Path $LogDir ($Started + '.log')
Start-Transcript -Path $LogFile -ErrorAction Stop | Out-Null
function Invoke-Docker {
    param([string[]]$CliArgs)
    & docker @CliArgs
    if ($LASTEXITCODE -ne 0) { throw ('Docker retornou codigo ' + $LASTEXITCODE + ' para: docker ' + ($CliArgs -join ' ')) }
}
function Assert-Hash {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw ('Backup nao existe: ' + $Path) }
    if ((Get-Item -LiteralPath $Path).Length -eq 0) { throw ('Backup vazio: ' + $Path) }
    $Hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    $ShaFile = $Path + '.sha256'
    ($Hash + '  ' + (Split-Path -Leaf $Path)) | Set-Content -LiteralPath $ShaFile -Encoding Ascii
    $Verified = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Hash -ne $Verified) { throw ('SHA-256 divergente: ' + $Path) }
    Write-Host ('Backup validado: ' + (Split-Path -Leaf $Path) + ' SHA256=' + $Hash)
}
function Backup-Volume {
    param([string]$Name, [string]$Suffix)
    $TargetName = $Started + '__alece-' + $Suffix + '.tar.gz'
    # Volume e montado somente para leitura. Nao cria volume nao existente.
    Invoke-Docker -CliArgs @('run','--rm','--network','none',
        '--mount',('type=volume,source=' + $Name + ',target=/origem,readonly'),
        '--mount',('type=bind,source=' + $BackupDir + ',target=/saida'),
        'python:3.12-alpine','sh','-ec',('tar -czf /saida/' + $TargetName + ' -C /origem .'))
    Assert-Hash -Path (Join-Path $BackupDir $TargetName)
}
$OldLocation = Get-Location
try {
    $ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    Set-Location -LiteralPath $ProjectRoot
    Write-Host ('Inicio=' + $Started + '; Host=' + $env:COMPUTERNAME + '; User=' + $env:USERNAME)
    Write-Host ('Projeto=' + $ProjectRoot)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker nao localizado no PATH.' }
    Invoke-Docker -CliArgs @('compose','version')
    Invoke-Docker -CliArgs @('info','--format','{{.ServerVersion}}')
    if (-not (Test-Path -LiteralPath '.\compose.yaml') -or -not (Test-Path -LiteralPath '.\docker\start.sh')) {
        throw 'Arquivos ALECE nao encontrados no diretorio indicado.'
    }
    if (-not ((Get-Content '.\compose.yaml' -Raw) -match 'ALECE_SECRET_KEY_FILE')) {
        throw 'compose.yaml nao corresponde ao pacote com segredos por arquivo. Nao alterar a stack.'
    }
    Invoke-Docker -CliArgs @('compose','config','-q')

    # Backup da configuracao e do codigo que governa a inicializacao.
    $Stage = Join-Path $env:TEMP ('alece-backup-' + $Started)
    if (Test-Path -LiteralPath $Stage) { throw 'Pasta temporaria ja existente. Operacao interrompida.' }
    foreach ($Relative in @('compose.yaml','.env','docker\start.sh','docker\Dockerfile','src\controller\config\settings.py')) {
        $Source = Join-Path $ProjectRoot $Relative
        if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw ('Arquivo ausente: ' + $Relative) }
        $Destination = Join-Path $Stage $Relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
        Copy-Item -LiteralPath $Source -Destination $Destination
    }
    $ConfigBackup = Join-Path $BackupDir ($Started + '__alece-config.zip')
    Compress-Archive -LiteralPath $Stage -DestinationPath $ConfigBackup -CompressionLevel Optimal
    Assert-Hash -Path $ConfigBackup
    # Compress-Archive pode ignorar arquivos ocultos; .env e salvo separadamente.
    $EnvBackup = Join-Path $BackupDir ($Started + '__alece-env.txt')
    Copy-Item -LiteralPath '.\.env' -Destination $EnvBackup
    Assert-Hash -Path $EnvBackup
    Remove-Item -LiteralPath $Stage -Recurse -Force

    $Json = & docker compose config --format json
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao resolver volumes do Compose.' }
    $Cfg = ($Json | Out-String | ConvertFrom-Json)
    $PgVol = [string]$Cfg.volumes.app_pgdata.name
    $MediaVol = [string]$Cfg.volumes.app_media.name
    $SecretVol = [string]$Cfg.volumes.app_secrets.name
    if (-not $PgVol -or -not $MediaVol -or -not $SecretVol) { throw 'Nomes de volumes inesperados no Compose.' }
    $Volumes = @(& docker volume ls --format '{{.Name}}')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao listar volumes.' }
    $HasPg = $Volumes -contains $PgVol
    $HasSecret = $Volumes -contains $SecretVol
    if ($HasSecret) { Backup-Volume -Name $SecretVol -Suffix 'secrets' }
    if ($Volumes -contains $MediaVol) { Backup-Volume -Name $MediaVol -Suffix 'media' }
    if ($HasPg -and -not $HasSecret) {
        throw 'Banco existente sem volume de segredos: nao gerar credenciais novas. Recuperacao manual necessaria.'
    }

    # Inicializa apenas dependencias, nunca roda as migracoes antes do dump.
    Invoke-Docker -CliArgs @('compose','up','-d','secrets-init','db')
    if ($HasPg) {
        $DumpName = '/tmp/alece-prebuild-' + $Started + '.dump'
        $PgCmd = 'set -eu; export PGPASSWORD="$(cat /run/alece-secrets/db_password)"; pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "' + $DumpName + '"; pg_restore -l "' + $DumpName + '" >/dev/null'
        Invoke-Docker -CliArgs @('compose','exec','-T','db','sh','-c',$PgCmd)
        $DbId = ((& docker compose ps -q db) | Out-String).Trim()
        if (-not $DbId -or $LASTEXITCODE -ne 0) { throw 'Container de banco indisponivel.' }
        $DumpBackup = Join-Path $BackupDir ($Started + '__alece-postgresql.dump')
        Invoke-Docker -CliArgs @('cp',($DbId + ':' + $DumpName),$DumpBackup)
        Assert-Hash -Path $DumpBackup
    }
    Write-Host 'Backups preparados. Reconstruindo apenas o servico web.'
    Invoke-Docker -CliArgs @('compose','up','--build','--force-recreate','--no-deps','-d','web')
    $WebId = ((& docker compose ps -q web) | Out-String).Trim()
    if (-not $WebId -or $LASTEXITCODE -ne 0) { throw 'Container web nao criado.' }
    $Healthy = $false
    for ($i=0; $i -lt 30; $i++) {
        $State = ((& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $WebId) | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel verificar a saude do web.' }
        Write-Host ('web health=' + $State)
        if ($State -eq 'healthy') { $Healthy = $true; break }
        if ($State -in @('exited','restarting','dead','unhealthy')) { break }
        Start-Sleep -Seconds 4
    }
    Invoke-Docker -CliArgs @('compose','ps','-a')
    if (-not $Healthy) {
        Invoke-Docker -CliArgs @('compose','logs','--no-color','--tail','100','web')
        throw 'Web nao ficou healthy; consulte o log e nao exclua volumes.'
    }
    Invoke-Docker -CliArgs @('compose','exec','-T','web','python','-c',"import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/live/',timeout=10); assert r.status==200; print('HTTP 200 health/live')")
    Write-Host 'VALIDADO: o container web esta healthy e o endpoint local respondeu 200.'
    Write-Host 'Backups e logs permanecem em HOME. Dados do PostgreSQL nao foram removidos.'
}
catch {
    Write-Host ('FALHA: ' + $_.Exception.Message)
    Write-Host 'Nao execute docker compose down -v; os backups ja produzidos foram preservados.'
    throw
}
finally {
    Set-Location $OldLocation
    Stop-Transcript | Out-Null
}
