# Relatório técnico e riscos — 28/10/2026

| Item | Resultado real |
|---|---|
| Integridade do ZIP-base | SHA-256 verificado antes das modificações |
| Escopo | Novo modal de Renda na Visão geral; preservada a edição individual antiga |
| Testes estáticos locais | 19 aprovados, sem falhas; aviso de pytest-django ausente |
| Chromium preview isolada | Claro 1280px e escuro 390px: abertura sobre a página, foco inicial e lock de rolagem verificados |
| Interação do modal | Cancelar, Continuar editando, Descartar e restauração de foco verificados |
| Validação frontend | HTTP 422 simulado: erro vinculado ao campo, modal aberto |
| Compilação Python / sintaxe JS | Verificadas sem erro |
| Django/PostgreSQL em execução | **Não testado** — Django e PostgreSQL não disponíveis nesta execução |
| Integridade da aplicação real | **Pendente** de homologação; não presumir sucesso de POST |
| Migrations | Nenhuma criada |
| `.env` / `.env.example` | Preservados byte a byte do ZIP-base |

## Riscos residuais

1. **Alto:** sem teste Django/PostgreSQL real, ainda não há prova de criação/persistência/rollback em banco; executar `tests/finance/test_income_bulk_modal.py` em banco isolado antes de produção.
2. **Médio:** concorrência entre dois operadores editando rendas do mesmo perfil exige validação operacional; a escrita é serializada com locks, mas a interface ainda não exibe versão de edição otimista.
3. **Médio:** o modal apresenta *todos os perfis autorizados à edição* no núcleo mesmo com filtro de leitura em um único perfil. A interface comunica essa abrangência pelo título, linhas e escopo de salvar.
4. **Baixo:** a prévia Chromium usa HTML sintético, não DOM renderizado pelo Django. Revisar em navegador contra instalação de homologação, com CSRF/sessão reais, especialmente em mobile.

## Aceite pendente

- Login real e permissões (admin/comum); um único perfil e múltiplos perfis; todas as formas de renda (`None`, `0`, decimal).
- POST com falha de validação, perda de autorização, dados conflitantes e queda de rede.
- Atualização de valores nos cards e no planejamento; preferência de perfil preservada após reload.
- Teclado, Escape, clique fora, foco e zoom 200%/400% nas telas reais de tema claro e escuro.
- Inspeção de logs e do PostgreSQL para comprovar rollback integral em falhas intermediárias.

Não foram inventados resultados de Django/PostgreSQL ou evidências de produção.

### Histórico de repetição

Na primeira execução conjunta, a asserção do fechamento ocorria antes de terminar a resolução assíncrona da confirmação. A automação foi corrigida para aguardar o estado de fechamento efetivo e foi executada novamente com aprovação. A falha inicial e a repetição permanecem no log.
