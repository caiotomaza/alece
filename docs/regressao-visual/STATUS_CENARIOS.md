# Estado dos cenários de regressão visual (27/10/2026)

Legenda: **IMPLEMENTADO/NÃO EXECUTADO** = existe teste Playwright que usa servidor
Django real em banco efêmero, mas a CI com PostgreSQL não foi executada neste
ambiente. Não implica aprovação funcional ou visual.

| Grupo | Cenários | Viewports CSS | Temas | Estado |
|---|---|---|---|---|
| Visão geral | vazio; preenchido | 320, 390, 768, 1280, 1920 | claro, escuro | Implementado/não executado |
| Despesas | vazio; preenchido | idem | ambos | Implementado/não executado |
| Investimentos | vazio; preenchido | idem | ambos | Implementado/não executado |
| Movimentações | preenchido | idem | ambos | Implementado/não executado |
| Importação | formulário de arquivo | idem | ambos | Implementado/não executado |
| Conta comum | configurações; negação administrativa | idem | ambos | Implementado/não executado |
| Administração | usuários; perfis; IA | idem | ambos | Implementado/não executado |
| Edição | perfil; despesa | idem | ambos | Implementado/não executado |
| Logs e relatórios | logs; técnicos; gráficos | idem | ambos | Implementado/não executado |
| Estados | dropdown aberto; campo de filtro focado; botão hover | idem | ambos | Implementado/não executado |
| Modal | formulário com erro de validação | idem | ambos | Implementado/não executado |
| Mensagens | sucesso; falha; HTTP 403 | idem | ambos | Implementado/não executado |
| Teclado | Enter; Escape; retorno de foco | 390, 1280 | herdado | Implementado/não executado |
| Acesso | cinco rotas administrativas bloqueadas para usuário comum | Chromium | n/a | Implementado/não executado |

**Baselines PNG aprovadas: nenhuma.** Sua ausência deve reprovar o modo
`compare`. O primeiro job deve ser executado em modo `capture` e revisado antes
de admitir as referências no repositório.
