# ALECE — Etapa 3: segurança, privacidade e autorização

Data: 2026-10-27. Base única: `ALECE_COMPLETO_Suite_Testes_Modulares_CI_Playwright_2026-10-27.zip`.

## Escopo e regra de evidência

Auditoria focalizada de autenticação, troca administrativa de senhas, sessões,
segredos de provedores de IA, envio de dados financeiros, importações,
exportações, relatórios, auditoria HTTP e configurações de segurança.
Não houve migração de tecnologia, alteração de schema, de rotas ou de modelos.

**Não considerar a etapa homologada em produção:** a suíte Django/PostgreSQL e
os cenários de browser ainda exigem execução no ambiente isolado. Uma revisão
estática não constitui prova de inexistência de vulnerabilidades.

## Matriz de riscos e mitigação

| Risco | Antes | Ação nesta etapa | Resultado/status | Risco residual |
|---|---|---|---|---|
| S01 — revogar sessões | SQL `session_data__contains` tentava localizar JSON literal em sessão Django codificada | Decodificar com `Session.get_decoded()`, comparar `_auth_user_id` por igualdade e excluir as sessões reais | Corrigido no código; testes de integração adicionados | Sem execução PostgreSQL; suporte restrito ao backend `db` |
| S02 — conta compartilhada entre workspaces | Administrador local podia resetar senha e revogar sessões de conta compartilhada | `PermissionDenied` no servidor quando alvo participa de mais de um workspace, exceto superusuário de sistema já autorizado no workspace | Corrigido no código; testes adicionados | Revisar modelo de governança de contas multiworkspace |
| S03 — superusuário global | Admin local podia alterar credenciais/sessões de superusuário presente no workspace | Bloqueio server-side antes de qualquer ação | Corrigido no código; testes adicionados | Superusuários continuam privilegiados, conforme modelo Django |
| S04 — segredos em rastros de exceção | Dados de senha e token nem sempre estavam marcados como sensíveis | `sensitive_post_parameters` em setup, criação, reset administrativo, edição da própria conta e formulário de API | Corrigido no código | Aplicar a qualquer nova view que receba segredos; auditoria de logs operacionais ainda necessária |
| S05 — credenciais de IA revogadas | Excluir integração não removia seu arquivo de chave local | `delete_token`, recusa de symlinks, revogação em exclusão/desativação, remoção de env fallback, rollback em memória de rotação que falha no DB | Corrigido no código; testes adicionados | Revogação de chaves externas requer ação também no provedor; falha SQL após exclusão local exige nova chave |
| S06 — consentimento IA pouco específico | Texto genérico de até 40 registros | Identificar provedor, endpoint e campos enviados: data, descrição, valor, categoria | Melhorado no template; consentimento `POST` segue obrigatório | Uma chamada ao provedor externo ainda pode envolver transferência internacional; revisar contratos/base legal |
| S07 — informação em erro de importação | `str(OSError/ValueError)` era devolvido na UI | Mensagem pública neutra para exceções operacionais | Corrigido no código; teste adicionado | Validações específicas devem continuar sendo revisadas contra reflexão de dados |
| S08 — injeção de fórmula CSV | Perfil e categorias exportados sem `_csv_text` | Escapar texto com prefixos que aplicativos de planilha interpretam como fórmulas | Corrigido no código; testes adicionados | Manter testes para todos os novos exportadores CSV |
| S09 — nomes de relatório/HTTP | Nome do perfil entrava no filename da resposta e do arquivo persistido | Nome estável composto pelo tipo, ID interno de perfil, período e formato; `private, no-store`, nosniff | Corrigido no código | Arquivos ReportExport permanecem em MEDIA_ROOT; proxy não deve servir `/media/` publicamente |
| S10 — cabeçalhos de auditoria controlados pelo cliente | Manager legado aceitava request-id, user-agent e X-Forwarded-For arbitrários | Não confiar em cabeçalhos para auditoria; usar somente `REMOTE_ADDR` validado | Corrigido no código | Reverse proxy deve preservar origem de forma auditável no seu próprio log, separadamente |
| S11 — CSRF/XSS/autorização | Middleware CSRF e autoescape Django já presentes; administração por workspace no servidor | Adicionados testes explícitos de CSRF, escaping de nomes e negação a usuário comum | Tests pendentes Django | Scanner e revisão manual necessários; não há certificado WCAG/OWASP |
| S12 — exportações/importações de dados | `MODEL_ORDER` tem somente entidades financeiras e rejeita tabelas adicionais; importação recria grants para membros existentes mediante confirmação `grant_all` | Preservado, com limite de escopo e testes existentes | Implementação existente preservada | **Importação concede acesso de edição aos membros atuais do destino se confirmada.** Revisar permissões após importar |
| S13 — HTTPS/cookies | `SECURE_COOKIES` e reconhecimento de proxy HTTPS já parametrizados | Não forçar cookies seguros em HTTP local, para não quebrar instalações self-hosted | Mantido deliberadamente | Implantação pública exige HTTPS, cookies Secure, configuração correta do proxy e HSTS planejado |
| S14 — SSRF por endpoint customizado | Host allowlist e HTTPS pinados na execução; admin pode adicionar host customizado | Política existente preservada | Não houve correção de DNS rebinding | Permitir somente hosts controlados, revisar IPs privados e egress na implantação |

## Autorização e segregação

- Login e redefinição de senha continuam com limites por usuário/IP e códigos de recuperação offline.
- Revogar sessões depende de banco Django (`django.contrib.sessions.backends.db`) e falha explicitamente se alguém trocar para backend incompatível.
- Admin de workspace não pode redefinir senha nem revogar sessões de uma conta com acesso a outros workspaces ou de um superusuário, salvo superusuário legítimo já autorizado.
- O usuário comum não ganha acesso ao painel de gestão, logs, importações administrativas nem às chaves de IA.
- Exportação financeira portátil mantém somente as entidades financeiras explicitamente listadas; contas e grants da origem nunca são importados.
- *Atenção:* o produto permite, via confirmação explícita, criar novas permissões `edit` para os usuários atuais do destino. Isso não é transmissão de permissões antigas, mas é uma decisão administrativa relevante.

## Exposição de dados e cabeçalhos

- Dados financeiros continuam armazenados no PostgreSQL local e em volumes Docker.
- Relatórios enviados por HTTP exigem autorização por módulo/perfil; respostas CSV/JSON agora trazem `Cache-Control: private, no-store` e `X-Content-Type-Options: nosniff`.
- A exportação financeira administrativa também tem `no-store` e mantém ZIP restrito às entidades financeiras.
- Os templates Django utilizam escaping padrão; não usar `|safe` em valores de usuários ou provedores sem revisão específica.
- Arquivos `MEDIA_ROOT/exports/` **não são publicados pelo URLconf incluído**. Não configure Nginx, Caddy ou outro proxy para servir o diretório `media` de forma pública.
- Diagnósticos HTTP com trechos de logs operacionais continuam reservados a superusuários; a sanitização é de melhor esforço. Nunca publique esses relatórios ou volumes Docker.

## Transporte de dados a IA

A submissão de análise continua restrita a administradores, por `POST` com proteção CSRF e opt-in `consent=yes`. O conteúdo transferido atualmente corresponde a até 40 linhas confirmadas: data, descrição até 160 caracteres, valor monetário em BRL e classificação; os campos e destinatário aparecem na UI. Nunca transmite senhas ou chaves como parte do payload financeiro; a chave da API segue apenas no cabeçalho Authorization, para o endpoint allowlisted. É necessária revisão de retenção/uso dos dados no provedor escolhido.

## Plano de implantação seguro

1. Verifique sistema operacional, Docker/Compose, privilégios, diretório atual, serviços e volumes; não presuma valores.
2. Faça backup verificável do projeto, banco PostgreSQL e volumes com SHA-256. Preserve o `.env` real da instalação.
3. Execute a suíte Django/PostgreSQL e Chromium em ambiente isolado, sem acesso à base de produção: no Windows PowerShell, `./scripts/Executar-Testes-Isolados.ps1` (adequando o shell conforme o sistema); na CI consulte `.github/workflows/ci.yml`.
4. Caso os testes falhem, **não** promova para produção. Registre exceções e corrija, usando apenas dados sintéticos.
5. Compare migrations `python manage.py makemigrations --check --dry-run` e execute `python manage.py check --deploy` em ambiente configurado conforme proxy/HTTPS, interpretando seus avisos no contexto de self-hosting.
6. Extraia o ZIP integral no diretório `alece` após backup e reconstrução controlada de `web`, sem apagar volumes nem reiniciar PostgreSQL à força.
7. Valide login, recuperação, revogação de sessões, CSRF, autorização de usuários comuns, exclusão e rotação de credenciais, importação/exportação, temas e páginas financeiras.

### Rollback

Se houver regressão, interrompa ações de escrita, preserve logs e evidências; restaure **os arquivos do projeto** do backup SHA-256 da versão anterior e reconstrua apenas o serviço afetado. Como não há migrations novas, normalmente não é preciso reverter esquema. Dados criados após o backup devem ser avaliados separadamente antes de qualquer restauração PostgreSQL (restaurar banco pode sobrescrever novos lançamentos). Uma chave de IA já revogada deverá ser cadastrada novamente; não restaure automaticamente chaves antigas a partir de arquivos de backup inseguros.

## Referências primárias

- Django 5.2 — Segurança: https://docs.djangoproject.com/en/5.2/topics/security/
- Django 5.2 — Sessões e `get_decoded`: https://docs.djangoproject.com/en/5.2/topics/http/sessions/
- Django 5.2 — Security checks: https://docs.djangoproject.com/en/5.2/ref/checks/
- OWASP — Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- OWASP — REST Security: https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
