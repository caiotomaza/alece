# Relatório de acessibilidade e responsividade — 2026-10-27

## Escopo e linha de base

- Base única: `ALECE_COMPLETO_MODAIS_FORMULARIOS_FEEDBACK_2026-10-27.zip` (SHA-256 `5c0c0eae989b363ae5bdd45e06fa300c498db6bebfe424cd8e62c67e49d8e627`).
- Preservados backend Django, modelos, permissões, rotas, migrations, PostgreSQL, .env, .env.example, licença e dois temas.
- Backup integral anterior à alteração, SHA-256 validado, criado no HOME do operador; procedimento abaixo.
- Fontes oficiais: https://www.w3.org/TR/WCAG22/ ; https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/ ; https://playwright.dev/docs/accessibility-testing .

## Alterações verificáveis

1. `finance/base.html`: inclusão dos assets progressivos e do bloco `extra_js` ausente (scripts específicos das páginas podem executar novamente).
2. `finance/alece_accessibility.css`: foco, reflow, alvo de toque 44px *meta*, movimento reduzido, high contrast e leitura de tabelas extensas.
3. `finance/alece_accessibility.js`: associação de erros e pistas de tabelas largas, região rotulada/rolável via teclado; sem fetch, armazenamento ou telemetria.
4. `finance/alece_tokens.css`: borda semântica de controles mais contrastante em ambos os temas, sem troca de paleta principal.
5. Vários templates de tabela: `scope=col` nos cabeçalhos de coluna. Cabeçalhos especiais/agrupados necessitam auditoria manual adicional.
6. `finance/_history_chart.html`: tabela de série real completa em `<details>`, com gráfico decorativo para tecnologia assistiva.
7. `finance/reports_dashboard.html`: tabelas correspondentes aos dados efetivos dos gráficos, grid responsivo, correção de markup e remoção do gráfico mensal DRE composto por 12 valores fictícios zerados; tabela DRE real mantida.
8. Templates públicos de login e recuperação: carregamento dos estilos/associações de erro comuns.

## Testes (resultados deste ambiente)

- `tests/accessibility/test_accessibility_contract.py`: **15 aprovados**, temas claro/escuro × 320, 390, 768, 1280, 1920 CSS px, além de testes estáticos e teclado na prévia.
- Regra de regressão `tests/modals` + `tests/design_system`: **30 aprovados** em execução separada, sem failures finais.
- 20 PNGs de prévia estática isolada (antes/depois, 10 combinações), `medidas_responsividade.json` com largura de documento e da região rolável. Zero overflow horizontal do DOCUMENTO na prévia, mas rolagem interna necessária para dados tabulares.
- Medições matemáticas de contraste base: texto normal dos tokens >= 4.5:1 nos fundos medidos, foco >3:1; bordas de campos após ajuste acima de 3:1 nos fundos analisados. **Não é avaliação exaustiva de contraste.**
- `node --check` dos JS alterados e Python `compileall` passaram; validação de template Django é pendente.
- Uma tentativa conjunta expirou em timeout após os testes aparentarem terminar; foi desconsiderada. Separadamente, 15 e 30 passaram com summaries gerados.
- Aviso do pytest: config `DJANGO_SETTINGS_MODULE` não reconhecida (pytest-django não está instalado).

## Limites críticos da validação

- Não foi possível executar `axe-core`/`@axe-core/playwright` por DNS indisponível (`EAI_AGAIN`), nem a aplicação Django/PostgreSQL. Scanner automatizado apropriado **pendente**, não substituído por varredura própria.
- Capturas representam um catálogo fictício sem autenticação. Não são provas de layout das telas reais, relatórios reais ou estados de permissão.
- Não houve teste com NVDA/VoiceOver/TalkBack, teste de usuários com deficiência, zoom nativo 200%/400% nem reflow completo das páginas Django.
- Não foi validada a regressão de negócio de usuários, perfis, despesas, investimentos, integrações IA, importação/exportação ou permissões.
- Remoção do gráfico DRE fictício altera a apresentação; fornece apenas os agregados verdadeiros existentes. Para série mensal genuína, implementar endpoint/dataset com autorização no servidor e testes.

## Priorização de riscos residuais

| Severidade | Problema / pendência | Mitigação e aceite futuro |
|---|---|---|
| Alta | Sem validação com Django, DB, autenticação e perfis em dispositivos reais | Executar smoke tests integrados em banco isolado e Playwright contra servidor; validar acesso financeiro/permissões |
| Alta | Zoom 400%, reflow 320 CSS px e navegação por teclado sem teste nas telas reais | Inspecionar todos os fluxos e corrigir truncamento, sticky focus e diálogos |
| Alta | Relatório DRE possuía gráfico zerado fictício; substituído por texto e DRE agregado | Implementar série autêntica ou manter alternativa sem simular meses |
| Média | Leitores de tela e anúncios de status não testados | Roteiro de testes manuais NVDA, VoiceOver e TalkBack e correção segundo achados |
| Média | Contraste de todos os textos, bordas e estados não medido | Rodar axe + auditoria pixel/medição de fundos e estados em todas as telas |
| Média | Associação cabeçalho/célula de tabelas com colspan, rowspan e conteúdo complexo | Verificar coluna/linha no leitor de tela; usar headers/id se agrupamento exigir |
| Média | Conteúdo de diálogos carregado dinamicamente | Teste integrado de foco, avisos e erro em todas as jornadas; somente simulações anteriores passaram |
| Baixa | Meta 44px pode alterar densidade em views densas | Homologar visualmente responsividade antes de produção |

## Procedimento de atualização e rollback

1. Não implantar diretamente em produção: homologar com instância isolada primeiro.
2. Faça backup independente da instalação, `.env` produtivo, banco de dados e volumes persistidos; gere e valide SHA-256. O backup do ZIP-base e sua soma estão em HOME/backups no ambiente de construção.
3. Verifique SHA-256 do ZIP entregue e extraia **dentro da pasta `alece/`**, preservando o `.env` da instalação em uso. Arquivos ficam na raiz do ZIP.
4. Não há migrations novas. Recolha os estáticos segundo a configuração de deploy e recarregue apenas o necessário. Execute healthchecks, testes reais e comparação visual.
5. Se houver falha, restaure o ZIP anterior com SHA-256 verificado, os estáticos anteriores e revalide. Banco não foi alterado nesta intervenção; **não restaure PostgreSQL automaticamente** se houver operações posteriores.
6. Mantenha logs, backups e relatórios de falha. Não descarte evidências.
