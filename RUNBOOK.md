# RUNBOOK — Operação e recuperação do ALECE

> **Alvo:** laboratório e homologação self-hosted. **Não utilizar para finanças reais antes de concluir as etapas de segurança e integridade em `docs/ROADMAP.md`.**

## 1. Identificação do ambiente (obrigatória)

Antes de implantar, confirme: distribuição/versão, arquitetura CPU, espaço livre, volumes, estado do Docker e Compose, método de acesso administrativo, rota de recuperação e portas. No ZimaOS verifique permissões do terminal/App Store e caminhos persistentes pelo painel. **Não** presuma shell root ou endereço fixo.

Para hosts Linux/Bash comprovadamente compatíveis, comandos somente leitura úteis: `uname -m`, `docker version`, `docker compose version`, `docker info`, `df -h`. Registre a saída no log da intervenção. Não publique segredos retornados por `docker inspect` ou `docker compose config`.

## 2. Preparação de segredos e rede

```bash
bash scripts/bootstrap.sh
```

- `.env` não deve entrar no Git.
- Por padrão, `ALECE_BIND_IP=127.0.0.1` e `ALECE_ALLOWED_HOSTS=localhost,127.0.0.1`.
- Para acesso LAN no ZimaOS, ajuste **somente** o bind e `ALLOWED_HOSTS` depois de verificar a rede real. Exemplo ilustrativo, **não é um endereço detectado**: `ALECE_BIND_IP=0.0.0.0`, `ALECE_ALLOWED_HOSTS=192.168.1.10,localhost,127.0.0.1`.
- Não exponha o banco PostgreSQL (Compose não publica a porta 5432).
- HTTPS não é requisito para validar o processo no loopback; se houver acesso por redes não confiáveis, use TLS e cookies seguros antes de habilitar usuários reais.

## 3. Primeira instalação e atualização

```bash
bash scripts/deploy.sh
```

O script executa o procedimento:
1. pré-verificações sem alteração;
2. cria log em `HOME/logs/YYYY-MM-DD_HH-MM-SS.log`;
3. valida Compose sem revelar credenciais;
4. inicia o banco, gera backup pre-migration e valida o SHA-256;
5. constrói a imagem, valida Django e executa migrações;
6. sobe a aplicação e verifica saúde sem declarar sucesso prematuramente.

Na **primeira instalação** sem tabela de aplicação, o dump representa o estado anterior (potencialmente vazio). **Não** usar `docker compose down -v`, pois remove dados persistentes.

Criar superusuário (interação no terminal; evite valores em linha de comando):

```bash
docker compose exec web python manage.py createsuperuser
```

## 4. Monitoramento e diagnósticos

- `GET /health/live/`: processo web vivo (não comprova o banco).
- `GET /health/ready/`: executa `SELECT 1` no PostgreSQL, retorna HTTP 200/503.
- `docker compose ps`: estado e health dos serviços.
- `docker compose logs --tail=100 web`: logs; **antes de compartilhar, revise segredos/dados pessoais**.
- `docker compose exec web python manage.py check --deploy`: checklist de segurança (alguns avisos dependem do cenário HTTP LAN/TLS configurado).

Somente leitura: gerar um log é suficiente; backup é exigido **antes de alterar**.

## 5. Backup de dados

```bash
bash scripts/backup.sh
```

Produz em `$HOME/backups/`:

```text
YYYY-MM-DD_HH-MM-SS__alece-postgresql.dump
YYYY-MM-DD_HH-MM-SS__alece-postgresql.dump.sha256
```

O arquivo é `pg_dump -Fc` (somente DB); **não contém automaticamente os arquivos de mídia, `.env`, certificados ou configurações do host**. Faça cópias independentes desses itens conforme sua implantação, com SHA-256, e documente-as. Não descarte backups sem política explícita.

Valide o backup **após produzir e novamente antes de restaurar**. O script confirma hash e conteúdo básico via `pg_restore --list`, quando disponível no contêiner PostgreSQL.

## 6. Rollback / restore após falha

**Não existe rollback automático destrutivo.** O operador deve avaliar migrações já aplicadas, dependências de versão, integridade e a janela de dados que será perdida.

1. Preserve o último log e estado de `docker compose ps`.
2. Identifique o último backup **anterior** à atualização; valide `<backup>.sha256` no diretório em que foi criado.
3. Preserve também eventual atividade posterior ao backup antes de restaurar (não sobrescreva dados novos sem autorização).
4. Pare **apenas a aplicação web** afetada: `docker compose stop web`.
5. Restaure a imagem/código compatível com o esquema do backup.
6. **Somente com autorização explícita e janela de manutenção**, restaure o DB com `pg_restore` em banco de teste primeiro. A opção `--clean --if-exists` destrói objetos existentes e não deve ser executada como ação automática.
7. Teste `/health/ready/`, fluxos reais e permissões antes de liberar o serviço.

Para testar a integridade **sem modificar o banco**: `docker compose exec -T db pg_restore --list` recebe o dump pela entrada padrão, conforme instruções operacionais verificadas. Para restauração real, use operador e procedimento específico, nunca `docker compose down -v` como rollback.

## 7. Recuperação de usuário e acesso administrativo

O login por usuário/senha está disponível. A geração de um novo código de recuperação offline exige sessão autenticada e senha atual; o código aparece uma vez e deve ser guardado pelo proprietário fora do sistema. O endpoint público `/recovery/` não emite códigos. Códigos emitidos antes da migração `core.0002` são recusados por versão e precisam ser regenerados pelo titular. O resgate tem uso único e limites de tentativas no PostgreSQL. Não há recuperação por e-mail.

Antes de aplicar `finance.0002` em qualquer banco persistente, execute backup validado e confira se há posições de Reserva antigas com `target_amount IS NOT NULL`; a nova constraint as rejeita. A migração não corrige automaticamente dados financeiros. Investigue e decida com o titular antes de avançar. Para consulta de pré-verificação no PostgreSQL isolado/autorizado: `SELECT COUNT(*) FROM finance_investmentposition WHERE category = 'reserve' AND target_amount IS NOT NULL;`. Valor maior que zero exige plano de reconciliação, não substituição silenciosa da meta.

## 8. Incidentes financeiros

- Saldo negativo após pagamento: tratar como defeito de integridade, interromper atualizações do módulo, preservar backups e logs, comparar débitos e lançamentos.
- Importação duplicada: não excluir histórico por conveniência; investigar chaves idempotentes, origem do arquivo e reprocessamento.
- Dado de perfil exposto: isolar acesso, preservar evidências com cuidado e revisar grants por perfil.
- Migração falhada: **não** insistir executando migrations aleatórias; restaurar ambiente de homologação e analisar `showmigrations`.
- Bug após release: retornar à imagem anterior e avaliar se o banco demanda restauração. Recuo apenas do código não desfaz mudanças irreversíveis de schema.

## 9. Encerramento de intervenção

Anote versão da imagem, commit, resultado de CI, backup/hash, testes de leitura e escrita, horários, erros e caminho do rollback. Mantenha arquivos de log e backup; jamais delete automaticamente.
