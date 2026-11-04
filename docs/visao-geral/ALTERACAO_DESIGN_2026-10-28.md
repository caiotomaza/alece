# ALECE — Visão geral conforme wireframe (28/10/2026)

## Escopo e decisão de interface

Base exclusiva: `ALECE_COMPLETO_CORRIGIDO_PERFIL_POST_404_2026-10-28.zip`, conferida com o SHA-256 fornecido. A implementação conserva a arquitetura Django, as URLs em português, os formulários e ações de pagamento/estorno, a seleção de perfil, os dois temas e os tokens do Design System ALECE 1.0.

O wireframe `wireframe_referencia.png` especifica uma composição 2 × 2, com indicadores compactos acima de dois painéis principais. A versão implementada usa a paleta e densidade do ALECE, não os cinzas usados apenas para indicar os blocos no desenho.

1. **Renda:** indicador da renda mensal conhecida, com link para edição quando autorizado; rendas desconhecidas permanecem indicadas como desconhecidas.
2. **Saldo:** consolidado de saldos de contas conhecidas (não soma renda nem saldos desconhecidos); atalho para o detalhamento de contas.
3. **Planejamento mensal:** oito categorias na ordem existente do serviço de planejamento, cada uma com percentual calculado sobre a renda e valor em BRL. A interface exibe também categorias com valor zero, mas preserva a regra anterior de omiti-las do gráfico. O total alocado, não alocado e excedente continua sendo calculado com `Decimal` no servidor.
4. **Este mês:** mantém a tabela, botões de confirmação, formulários POST de estorno, CSRF, idempotência e os destinos de navegação originais. O cabeçalho referente a `due_on` passa a se chamar **Vencimento**, para não descrever uma data como periodicidade.
5. **Detalhes:** a antiga distribuição circular, o resumo de patrimônio investido e as contas continuam acessíveis em `<details>`, sem nova rota nem novas consultas.

Em telas estreitas, os indicadores e painéis passam para uma coluna; o planejamento se apresenta como lista acessível, sem rolagem horizontal. A tabela de compromissos conserva cabeçalhos e uma região própria de rolagem. `prefers-reduced-motion` é respeitado.

## Alterações de código

| Arquivo | Alteração |
|---|---|
| `src/view/templates/finance/workspace_page.html` | Reorganização exclusiva do ramo `active_nav == 'overview'`, mantendo os demais ramos; novos indicadores, tabela/lista, detalhes |
| `src/view/static/finance/alece_overview.css` | Estilos específicos da página e dos dois temas via tokens existentes |
| `src/view/static/finance/alece_overview.js` | Melhoria progressiva para expandir detalhes pelo atalho de saldo; sem alteração em AJAX/POST |
| `src/controller/apps/finance/services/metrics.py` | Propriedade adicional de apresentação `all_categories` com percentual, sem alterar a lista positiva `categories` nem valores financeiros |
| `tests/finance/test_visual_read_models.py` | Novas asserções para oito categorias e precisão decimal; execução integrada pendente |
| `tests/design_system/test_overview_wireframe_contract.py` | Contratos estáticos novos, sem banco |
| `scripts/quality/verify_overview_layout.py` | Catálogo isolado para verificar geometricamente 320/390/768/1280/1920 × claro/escuro |

**Sem migrations, sem alterações de modelos, permissões, roteamento, dados PostgreSQL, `.env` ou Docker Compose.**

## Validação efetivamente realizada

- Backup integral anterior criado e validado com SHA-256.
- **10 testes locais aprovados**: contratos novos e testes anteriores do Design System (sem Django).
- **10 combinações Chromium aprovadas** na prévia estática com dados fictícios: largura CSS 320, 390, 768, 1280 e 1920 × tema claro/escuro. O teste verifica ausência de overflow horizontal global, dimensões dos cards e a presença dos dois painéis.
- 4 screenshots (320 e 1280 × claro e escuro) e medições em `evidencias/`.
- `node --check` do JS e compilação sintática Python concluídos.
- A suíte ampliada foi iniciada, mas **excedeu o tempo limite**: não há aprovação dessa execução.

**Pendências:** Django e PostgreSQL não estão disponíveis no ambiente de edição. Não foram executados teste HTTP autenticado, teste de templates Django reais, regressão funcional do pagamento/estorno, regressão de CSS no aplicativo servido, nem testes manuais com leitores de tela. As imagens são de um catálogo fictício usando os CSS reais, não capturas de produção nem prova de conformidade WCAG.

## Critérios de homologação antes da produção

1. Em ambiente de homologação isolado, executar os testes Django, inclusive `test_visual_read_models.py`, sem apontar para banco de produção.
2. Autenticar como administrador e usuário comum; verificar visibilidade limitada aos perfis financeiros autorizados.
3. Conferir Renda e Saldo separadamente, com casos renda zero, renda desconhecida, conta com saldo desconhecido, múltiplos perfis e nenhum lançamento.
4. Validar detalhamento de contas e investimentos, alteração de renda, criação de despesa, pagamento, estorno e histórico auditável.
5. Verificar menu, rolagem da tabela, foco, zoom e temas em desktop e celular. Validar os recursos móveis por teclado e leitor de tela quando disponíveis.
6. Só promover a versão após verificação dos resultados, logs do serviço e rollback conhecido.

## Atualização e rollback

**Backup na máquina de destino:** antes da intervenção, exporte o código existente, o `.env`, os volumes relevantes e um backup nativo validado do PostgreSQL, preservando os arquivos e seus hashes SHA-256 em `$HOME/backups/` e registrando a intervenção em `$HOME/logs/`. O ZIP contém um `.env` da base recebida: não sobrescreva seu `.env` produtivo sem avaliar as diferenças.

Extraia o novo ZIP com os arquivos diretamente na pasta `alece`, sem criar uma subpasta, preservando a configuração da instalação. Depois reconstrua/recrie **somente o serviço web** pela rotina Docker Compose já validada para sua instalação, de modo que o CSS novo participe da publicação de estáticos. Não execute operações de exclusão de volume, reinicialização de banco nem limpeza de dados.

Em caso de regressão, recupere o código e estáticos do backup integral prévio com checksum validado e recarregue apenas o serviço web. **Não restaure o banco automaticamente**: não há mudança de esquema e lançamentos mais recentes não devem ser perdidos. Reavalie o histórico e os logs antes de qualquer intervenção no PostgreSQL.

## Referências técnicas

- [Django 5.2 — template inheritance](https://docs.djangoproject.com/en/5.2/ref/templates/language/)
- [W3C WCAG 2.2 — Reflow 1.4.10](https://www.w3.org/TR/WCAG22/#reflow)

A compatibilidade do aplicativo inteiro com essas normas não foi comprovada nesta rodada.
