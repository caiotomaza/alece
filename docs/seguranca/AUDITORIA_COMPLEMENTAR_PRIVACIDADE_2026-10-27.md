# ALECE — Auditoria complementar de segurança, privacidade e autorização

**Data:** 2026-10-27. **Base exclusiva:** ZIP `ALECE_COMPLETO_Seguranca_Privacidade_Autorizacao_2026-10-27(1).zip` entregue pelo usuário, SHA-256 `6b98bd3e03d8cf945878ca2c2c8bfd147c932212b58a528fda0a08a7ada6af1d`.

## Limite da verificação

Esta auditoria é **estática e parcialmente testada**, não um pentest nem uma homologação produtiva. Não foi possível executar Django/PostgreSQL/Playwright nesta máquina (bibliotecas ausentes, tentativa de instalação bloqueada por DNS). Não houve acesso a dados, segredos, banco ou volumes da implantação do operador. **Nenhuma afirmação de conformidade integral** com LGPD, WCAG ou proteção absoluta contra vazamentos é possível sem testes adicionais.

O ZIP de entrada **já continha** as correções da Etapa 3 (`docs/seguranca/ETAPA3_PRIVACIDADE_SEGURANCA_2026-10-27.md`), testes de sessões, chaves de IA, exportação e permissões. Essas correções foram mantidas. Esta entrega acrescenta controles localizados, sem mudança de banco, permissões, rotas, temas, licença ou arquitetura.

## Matriz de risco

| ID / área | Impacto | Evidência observada no código recebido | Medida / estado após revisão | Pendência residual |
| --- | --- | --- | --- | --- |
| P01 — XSS no dashboard de relatórios | Alto | `{{ dashboard.equity\|safe }}` e `{{ dashboard.investments\|safe }}` injetavam representação Python em contexto JS com nomes financeiros controláveis | **Corrigido:** somente campos necessários são serializados via `json_script` e lidos com `JSON.parse`; sem `safe` | Teste Django com payload `</script>` criado, mas execução HTTP pendente |
| P02 — integridade do JS dos gráficos | Médio | Blocos aninhados sem fechamentos de chaves no script | **Corrigido:** sintaxe aceita por Node.js em versão com tags Django substituídas por marcadores | Validação Chart.js/browser ainda pendente |
| P03 — HTML dinâmico em texto auxiliar | Médio | `object_form.html` usava `field.help_text\|safe` | **Endurecido:** autoescape Django preservado | Verificar apresentação de todos os formulários via navegador |
| P04 — vazamento em diagnósticos textuais | Alto | Sanitização cobria `token=`, mas não cobria adequadamente `access_token`, `refresh_token`, campos JSON com aspas nem senhas contendo espaços | **Endurecido:** linhas contendo campos de segredo são suprimidas integralmente na exportação diagnóstica; testes unitários incluídos | Não equivale à sanitização de TODOS os logs em disco; mensagens sem rótulo reconhecível ainda podem conter dados sensíveis |
| P05 — isolamento financeiro | Crítico | `require_module`, `require_workspace_admin`, `get_module_profiles` fazem avaliação server-side com workspace/grant; relatórios exigem módulos | **Mantido:** nenhum relaxamento | Exercitar IDOR e grant revogado contra PostgreSQL com múltiplos núcleos |
| P06 — gestão de contas/sessões | Crítico | Sessões revogadas por `get_decoded()`, limitação de alterações em contas multiworkspace e superusuários; senhas marcadas `sensitive_post_parameters` | **Mantido:** controles da Etapa 3 | Ensaiar concorrência, recuperação e revogação real no banco de sessões |
| P07 — chave de IA | Alto | Chaves em volume dedicado `app_ai_tokens`, arquivo 0600, rotação por substituição e exclusão local; endpoint HTTPS/preset ou host allowlisted | **Mantido:** sem mudança de endpoint/volume | Revogação externa não automática; risco de SSRF/controle DNS em endpoints personalizados deve ser avaliado pelo administrador |
| P08 — envio de informações a IA | Crítico | `analyze_imports` exige admin, POST + CSRF, `consent=yes`, provedor ativo e perfil no próprio workspace; até 40 itens; sem envio em segundo plano | **Mantido:** formulário identifica provedor, endpoint, campos e escopo | Revisar contratos, retenção, transferências internacionais e base legal específica com responsáveis pela operação; consentimento isolado não basta |
| P09 — unicidade da IA | Alto | `core` possui índice único parcial de provedor ativo por workspace (migration `0009`) e bloqueio `select_for_update` | **Mantido** | Validar concorrência em PostgreSQL real isolado |
| P10 — importação e concessões | Crítico | `MODEL_ORDER` permite só entidades financeiras; exclui usuários, hashes de senha, grants, sessões, logs, tokens; associa dados ao workspace de destino | **Mantido:** sem transferência de concessões anteriores | Importação administrativa solicita **nova** concessão de edição aos usuários *atuais* do destino (`grant_all=yes`); decisão de governança de alto impacto, revisar antes de confirmar |
| P11 — CSV/XLSX e cache | Alto | CSV com neutralização de fórmula, XLSX com valores como texto, download com `no-store` e nomes de arquivo não pessoais | **Mantido:** sem mudança financeira | Validar com planilhas e clientes HTTP; volumes `media/exports` não devem ser publicados pelo proxy |
| P12 — cookies e transporte | Crítico | `HttpOnly`, SameSite Lax, cabeçalhos `nosniff`, frame DENY e Referrer-Policy; `ALECE_SECURE_COOKIES` e proxy SSL configuráveis | **Mantido:** configuração local HTTP continua possível | Em acesso remoto, implantar TLS em proxy confiável e ativar cookies seguros; validar `X-Forwarded-Proto` e `check --deploy` |
| P13 — telemetria e privacidade | Médio | Biblioteca Chart.js servida de `/static/vendor`; sem chamada de analytics/telemetria obrigatória encontrada nos templates/código verificados | **Mantido** | Links externos de documentação e IA opt-in podem fazer requisições ao serem acionados; auditar tráfego em execução |
| P14 — logs operacionais do host | Alto | Saída de bibliotecas e rastros de exceção podem conter identificadores fora dos rótulos conhecidos | **Risco residual explícito:** nenhuma garantia genérica sobre loggers externos, scripts de implantação e logs históricos | Restringir acesso ao volume de logs, aplicar retenção e redatores por componente, revisar logs reais antes de compartilhá-los |

## Alterações de código nesta entrega

1. `src/controller/apps/finance/reports_views.py`: passa apenas data/saldos e nome/valor para as duas séries de gráficos em contexto JSON.
2. `src/view/templates/finance/reports_dashboard.html`: usa `json_script`, `JSON.parse`, corrige fechamento de blocos e remove `safe` sobre dataclasses.
3. `src/view/templates/finance/object_form.html`: remove `safe` do texto auxiliar de formulários.
4. `src/controller/apps/core/views.py`: exportação de diagnóstico mascara **a linha completa** quando há nome de campo de credencial, inclusive JSON e URLs.
5. `tests/reports/test_safe_dashboard_chart_data_20261027.py`: testes Django de payload XSS e proibição de leitura por usuário não autorizado.
6. `tests/operations/test_security_dashboard_and_diagnostic_no_django.py`: contrato estático e execução real da rotina de mascaramento, sem dependências de Django.

**Migrations:** nenhuma nova nem editada. **Dependências:** nenhuma nova. **.env e .env.example:** cópias byte-a-byte da base recebida; valores operacionais preservados. **Temas, arquitetura, seletores financeiros e rotas:** nenhuma alteração.

## Governança de privacidade

A LGPD exige avaliação contextual da finalidade, necessidade, bases legais, segurança, direitos dos titulares, contratos e incidentes. O opt-in visual para IA é uma salvaguarda de produto, não prova de base legal. Recomenda-se inventário de tratamentos e fornecedores, minimização do payload, avaliação de transferência internacional, política de retenção e fluxos de atendimento a titulares. Os critérios de Privacy by Design, ISO 9241-11/210, Nielsen, Gestalt e WCAG 2.2 AA são referências orientadoras; **nenhuma certificação ou alegação de conformidade foi produzida**.

## Fontes oficiais consultadas em 2026-10-27

- Django 5.2, uso de `json_script`: https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#json-script
- Django 5.2, proteção contra XSS e CSRF: https://docs.djangoproject.com/en/5.2/topics/security/
- Django 5.2, checklist de implantação: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- OWASP, DOM-based XSS: https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html
- OWASP, Logging: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- ANPD, guia de segurança de agentes de pequeno porte: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte
