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

Antes de aplicar `finance.0002`, `finance.0003` e `finance.0004` em qualquer banco persistente, execute backup validado com SHA-256 e rode o comando de validação prévia:
`docker compose exec web python manage.py preflight_finance --strict`.
Esse comando confere contas com saldo inicial não conciliado e posições inválidas de Reserva. O preflight deve retornar `"safe_to_apply_reserve_constraint": true` e zero pendências antes de avançar.

### Imutabilidade do Ledger e Partidas Dobradas
As movimentações financeiras gravadas (`TransactionBatch`, `LedgerLeg` e `JournalEntry`) são protegidas por triggers no PostgreSQL (`finance_guard_posted_history` e `finance_assert_journal_balance`).
- Lançamentos contábeis postados não aceitam UPDATE nem DELETE no banco. Tentativas de alteração direta disparam exceção `Posted financial history is immutable`.
- Para anular uma movimentação, use sempre o fluxo oficial de **Estorno** (`reverse_batch`), que gera uma contrapartida contábil simétrica preservando toda a trilha de auditoria.

## 8. Incidentes financeiros

- Saldo negativo após pagamento: tratar como defeito de integridade, interromper atualizações do módulo, preservar backups e logs, comparar débitos e lançamentos.
- Violação de gatilho de imutabilidade: investigar scripts ou comandos diretos que tentem alterar `TransactionBatch` ou `LedgerLeg`; utilizar exclusivamente o serviço transacional `reverse_batch`.
- Importação duplicada: não excluir histórico por conveniência; investigar chaves idempotentes, origem do arquivo e reprocessamento.
- Dado de perfil exposto: isolar acesso, preservar evidências com cuidado e revisar grants modulares por perfil (`ProfileGrant`).
- Migração falhada: **não** insistir executando migrations aleatórias; restaurar ambiente de homologação e analisar `showmigrations`.
- Bug após release: retornar à imagem anterior e avaliar se o banco demanda restauração. Recuo apenas do código não desfaz mudanças irreversíveis de schema.

## 9. Operações de Importação Bancária (Sprint 04)

### 9.1 Fluxo de Importação
1. **Upload** via interface web (`/finance/workspaces/<id>/imports/new/`) — aceita CSV e OFX.
2. **Staging** — arquivo validado, parseado, hash SHA-256 computado, transações normalizadas e gravadas em `ImportBatch` + `ImportRow`.
3. **Detecção de duplicidades** — por FITID (OFX), hash de arquivo (reimportação), comparação contextual (data ±1 dia, valor exato, descrição similar).
4. **Reconciliação assistida** — sugestões automáticas: vincular a despesa existente, pagamento parcial, nova despesa imprevisível, aplicação/resgate em investimento, transferência, recebimento.
5. **Prévia editável** — usuário revisa cada linha, ajusta valor/descrição/tipo/conta/competência, define splits multi-conta.
6. **Commit atômico** — confirmação humana obrigatória, idempotência por chave, criação/vinculação de `TransactionBatch` com ledger balanceado.

### 9.2 Formatos Suportados
- **CSV**: UTF-8, ISO-8859-1, Windows-1252; delimitadores `;`, `,`, tab, `|`; cabeçalho opcional; colunas crédito/débito separadas ou valor único com sinal.
- **OFX 1.x**: Formato SGML (ex: bancos brasileiros legados).
- **OFX 2.x**: Formato XML com proteção contra XXE e expansão de entidades.

### 9.3 Segurança
- Processamento 100% local (self-hosted), zero transmissão externa.
- Limites: 5 MiB por arquivo, 5.000 transações.
- Sanitização de textos (remoção de caracteres de controle, XSS, formula injection).
- Hash SHA-256 do arquivo original para auditoria e deduplicação.
- Validação de codificação, estrutura, limites antes de processar.

### 9.4 Permissões
- Requer `accounts:edit` e `movements:edit` no perfil alvo.
- Administrador do workspace tem acesso irrestrito.
- Usuário comum depende de `ProfileGrant` explícito.
- Revogação de grant vale na próxima requisição (invalida cache/sessão).

### 9.5 Monitoramento de Importações
- Lista em `/finance/workspaces/<id>/imports/` mostra status: `staged`, `validated`, `reviewed`, `committed`, `failed`.
- Relatório pós-commit (`/imports/<id>/report/`) detalha: confirmadas, vinculadas, ignoradas, duplicatas, erros, trilha de auditoria (hash, idempotency key, autor, timestamp).
- Logs em `HOME/logs/YYYY-MM-DD_HH-MM-SS.log` registram upload, parse, commit.

## 10. Encerramento de intervenção

Anote versão da imagem, commit, resultado de CI, backup/hash, testes de leitura e escrita, horários, erros e caminho do rollback. Mantenha arquivos de log e backup; jamais delete automaticamente.
