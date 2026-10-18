# ALECE — Base de desenvolvimento (Sprint 08 concluido)

**Gestao financeira pessoal e familiar, gratuita, self-hosted e codigo aberto.**

![status](https://img.shields.io/badge/estado-sprint%2008%20conclu%C3%ADdo-215d40)
![license](https://img.shields.io/badge/licen%C3%A7a-GPL--3.0--only-215d40)

**Estado real:** fluxos Django persistentes e auditados para autenticacao, perfis, cadastros, pagamentos parciais e divididos entre multiplas contas, competencias mensais, transferencias, aplicacoes, resgates, estornos simetricos e imutabilidade de ledger com partidas dobradas no PostgreSQL. Interface alinhada ao prototipo v1.32.1 (temas Claro/Escuro, modais com acoes no rodape e lapis por linha). **Importacoes OFX/CSV/PDF com adaptadores modulares, deteccao conservadora de duplicidades (FITID + contextual), reconciliacao assistida com vinculo a lancamentos existentes, categorizacao De-Para persistida com prioridade e regex segura, relatorios financeiros consolidados (DRE, evolucao patrimonial, investimentos, metas/Reserva), exportacao CSV/JSON, graficos Chart.js self-hosted, previa editavel com confirmacao humana obrigatoria e relatorio detalhado.** **Comandos de limpeza de arquivos expirados e backup/restore com validacao SHA-256 e reconciliacao ledger (AC-08).** **Endpoint `/healthz/` para orquestracao, Docker hardening para ZimaOS.** **Nao usar com financas reais antes da revisao final de seguranca, restore e implantacao oficial.**

## Objetivos

- Python + **Django 5.2 LTS**, PostgreSQL 16 e Docker Compose; compatível com hospedagem em servidor Linux e implantação planejada no ZimaOS.
- Código em módulos, modelos de domínio, serviços de transação, testes, CI e releases de imagens.
- Finanças isoladas por perfil: permissões granulares por módulo explicitamente concedidas em views/services; o código não assume que todo usuário vê todas as finanças.
- Interface consistente com o protótipo: duas aparências (Claro/Escuro), sidebar e ações localizadas por seção (`+` para criar, lápis para editar), sem botões redundantes.
- **GPL versão 3** aplicada como `GPL-3.0-only`. O texto em `LICENSE` foi copiado **integralmente** do anexo do projeto.

## Visão rápida dos recursos

| Camada | Implementado | Planejado |
|---|---|---|
| App Django | Login/recuperação auditados, saúde, visão geral, despesas, investimentos, movimentações, perfis, grants granulares, **importação OFX/CSV/PDF** | Categorização inteligente, REST e isolamento autorizado por endpoint |
| Domínio | Workspaces, perfis, contas, despesas, investimentos, reserva, ledger contábil, partidas dobradas, competências, **ImportBatch/ImportRow, CategorizationRule** |  |
| Finanças | Pagamentos parciais e multi-conta, quitação, estornos, transferências, aplicações, resgates, reserva 6–12 meses, distinção NULL vs 0, **reconciliação assistida, categorização De-Para, relatórios DRE/patrimônio/investimentos/metas** |  |
| Auth/Permissões | **Login/logout, recuperação offline protegida, roles admin/common, grants modulares por perfil, limites de tentativas** | MFA, convites e gestão de múltiplos usuários |
| Infra | Dockerfile não-root com hash-pinning, Compose com healthcheck, Postgres sem porta externa, bootstrap/deploy/backup | Observabilidade e retenção institucional |
| Entrega | GitHub Actions CI, publicação manual e explícita por tag, auditoria de dependências pip-audit | CD para ZimaOS após validação |

## Organização do repositório

```text
.
├── apps/
│   ├── core/                  # healthchecks, auth views, permissions, UserProfile
│   └── finance/
│       ├── domain/            # regras puras de finanças
│       ├── services/          # casos de uso transacionais
│       ├── migrations/        # schema versionado
│       └── models.py          # entidades e invariantes persistidos
├── config/                    # configurações por ambiente, ASGI e WSGI
├── docs/                      # arquitetura, domínio, segurança, ZimaOS, ADR
├── reference/prototype/       # HTML v1.32.1 (somente referência visual)
├── requirements/              # dependências restritas por faixa
├── scripts/                   # bootstrap, backup, deploy e validação
├── tests/                     # testes unitários e de integração (consulte relatório atual)
├── .github/workflows/         # CI e publicação de imagens
├── Dockerfile
├── compose.yaml
├── .env.example
├── LICENSE
├── RUNBOOK.md
└── README.md
```

## Antes de executar

Use uma máquina com **Docker Engine + Docker Compose v2**, Bash, Python 3, SHA-256, acesso ao diretório do projeto e permissão para Docker. Verifique o SO e os privilégios do host; não presuma que o ZimaOS disponibiliza um terminal idêntico a outra distribuição. Não copie `.env` para um repositório público.

**Preparação (não altera a instalação atual de outros serviços):**

```bash
bash scripts/bootstrap.sh
```

Esse comando confere dependências, cria `.env` **somente quando não existe**, gera segredos novos e grava um log sem segredos em `$HOME/logs/`. Confira **`ALECE_ALLOWED_HOSTS`** e **`ALECE_BIND_IP`** antes do deploy. O padrão `127.0.0.1` só permite acesso local.

**Primeira implantação (requer Docker operacional):**

```bash
bash scripts/deploy.sh
```

O script valida Compose, sobe o banco, cria dump anterior à migração, confere SHA-256, migra e inicia a web, verificando saúde. Após subir:

```bash
docker compose exec web python manage.py createsuperuser
```

Acesse **http://127.0.0.1:8000/** ou o IP/porta que configurou no host. Acesse `/admin/` somente para administração de usuários e memberships; modelos financeiros são somente leitura ali. **Nunca exponha a porta de administração diretamente à internet sem autenticação de perímetro e TLS.** O produto ainda não está pronto para dados financeiros reais.

### ZimaOS

O ZimaOS suporta aplicativos personalizados via Docker Compose, mas a instalação pela interface gráfica geralmente espera **uma imagem publicada**, não o contexto `build: .` deste repositório. Após a CI publicar em GHCR, altere `build:` para `image:` com a tag aprovada; siga `docs/ZIMAOS.md`. **Não** execute a documentação de exemplo sem verificar o host e as portas.

## Como contribuir

Leia `CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, `docs/ADR/0001-modular-monolith.md`, `docs/UX_DESIGN_SYSTEM.md` e `docs/CI_CD.md`. Mudanças financeiras exigem testes de invariantes, migrações revisadas, changelog, backup e plano de rollback. Mantenha arquivos existentes, não apague históricos de forma automática.

## Licença e direitos

Código-fonte sob **GNU GPL v3 somente**, conforme `LICENSE` anexado. Distribuições de versões modificadas devem respeitar os termos da licença e disponibilizar o código-fonte correspondente quando exigido. O licenciamento do **software** não transfere automaticamente direitos sobre bandeiras, marcas, fontes ou imagens de terceiros incluídas no protótipo. Veja `docs/LICENSING.md`.

O ALECE homenageia **Alice**, mãe do criador e profissional de economia. Links de referência: [site do criador](https://caiotomaza.github.io/) e [site do ALECE](https://caiotomaza.github.io/alece/).

## Documentação essencial

- [RUNBOOK.md](RUNBOOK.md) — instalação, saúde, backup, atualização, incidentes e recuperação.
- [docs/PRODUCT.md](docs/PRODUCT.md) — como a ferramenta deve funcionar.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — camadas e extensibilidade.
- [docs/DOMAIN.md](docs/DOMAIN.md) — invariantes do domínio financeiro.
- [docs/CI_CD.md](docs/CI_CD.md) — fluxo de branches, testes, imagens, entregas.
- [docs/ROADMAP.md](docs/ROADMAP.md) — o que falta implementar.
- [docs/SPEC_ORIGINAL_COMPLETA.md](docs/SPEC_ORIGINAL_COMPLETA.md) — histórico completo de requisitos e protótipo.