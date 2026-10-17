# Changelog

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