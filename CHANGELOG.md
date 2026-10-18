# Changelog

## 0.4.0 (em desenvolvimento) — 2026-10-18

- Auditoria do Sprint 01 em PostgreSQL isolado, com correção da emissão anônima de recuperação, proteção contra replay e força bruta, validação de senha e redirecionamento de login.
- Admin de workspace acessa todos os perfis do próprio núcleo; grants para usuários comuns são verificados por workspace. Escrita financeira direta pelo Django Admin bloqueada.
- Sprint 02: perfis ativos/arquivados, renda ausente/zero/positiva, contas com saldo conhecido/desconhecido, despesas previsíveis e imprevisíveis, posições de investimento, Reserva e consultas isoladas por mês/perfil.
- Ações de cadastro, edição, arquivamento e exclusão autorizadas por objeto, via serviços transacionais. Cadastros de renda, despesas e investimento não criam movimentações bancárias.
- Visão geral, Despesas, Investimentos, seletor de perfis, formulários com melhoria progressiva, tema Claro/Escuro e adaptação a mobile. Migração `finance.0002_sprint02_catalogs` adiciona arquivamento, data opcional da posição e checks de vencimento e meta da Reserva.
- Pipeline de publicação exige acionamento manual explícito em tag versionada. CI audita dependências de produção; a imagem local atualiza o instalador `pip` antes de instalar a aplicação.

## 0.3.0 — 2026-10-18

- Primeiro fluxo financeiro após login: seleção de núcleo, listagem e criação de perfis financeiros, consulta e criação de contas bancárias ou dinheiro físico por perfil.
- Criação de perfis restrita a administradores do núcleo, com limite de cinco aplicado pelo serviço transacional e grant de visualização/edição para o criador.
- Visualização e criação de contas protegidas por grants; vínculos de permissão entre núcleos diferentes são ignorados. Acesso de administrador aos perfis do seu núcleo é implementado na auditoria do Sprint 01.
- Formulários com validação de nomes duplicados, valores não negativos e distinção entre renda/saldo desconhecido e zero informado; navegação, estados vazios e mensagens em português.
- Testes do fluxo autenticado, autorização, isolamento, validação e limite. Modelos existentes reutilizados, sem nova migration.

## 0.2.0 — 2026-10-15

### Fase 1 — Autenticação, Usuários, Workspaces, Perfis Financeiros e Permissões

- **Autenticação Django**: Login, logout, alteração de senha com views personalizadas e templates consistentes com o design system ALECE.
- **Recuperação offline**: Código de recuperação único (SHA-256 hash, uso único, sem e-mail) para redefinição de senha.
- **Modelo UserProfile**: Campos estendidos para recovery code, preferência de tema (light/dark/auto).
- **Sistema de permissões granular** (`apps.core.permissions`):
  - Isolamento por workspace (núcleo familiar) via `WorkspaceMembership` (roles: admin/common).
  - Isolamento por perfil financeiro via `ProfileGrant` (can_view, can_edit).
  - Funções de verificação: `user_can_view_profile`, `user_can_edit_profile`, `get_accessible_profiles`, `get_editable_profiles`.
  - Decorators/guards: `require_profile_view`, `require_profile_edit`, `require_workspace_admin`.
  - Filtro de queryset por acesso do usuário: `filter_queryset_by_user_access`.
- **Home page protegida**: `@login_required` na view principal, redirecionamento para login customizado.
- **Configuração de URLs**: `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "home"`, `LOGOUT_REDIRECT_URL = "login"`.
- **Testes abrangentes**: 26 novos testes de autenticação, recuperação e permissões (total 40 testes passando).
- **Documentação**: Atualização do CHANGELOG e README.

## 0.1.0 — 2026-10-15

- Starter de engenharia organizado em monólito modular Django.
- PostgreSQL + Compose + Gunicorn + healthchecks.
- Modelos financeiros iniciais, reserva 9 meses, cálculo decimal e serviço de débito multi-conta.
- GitHub Actions CI / publicação de imagem em tags, Dependabot e documentação operacional.
- Protótipo visual v1.32.1 e especificação original preservados como referência sem integração.

**Não é release funcional do aplicativo ALECE completo.**
