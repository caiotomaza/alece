# ALECE — Protocolo de usabilidade (sem dados reais)

## Condições de teste

Teste com pessoas voluntárias em instalação separada, com usuário comum e administrador de teste, núcleos/perfis e transações **fictícias**. Não use contas bancárias ou dados de produção. Registre consentimento para observação e trate quaisquer gravações localmente; evite captura de rosto/voz e não habilite telemetria externa obrigatória. O facilitador anota somente identificador aleatório do cenário, status, duração e erros não identificáveis.

## Tarefas independentes

| Código | Meta e critério de conclusão observável | Erro relevante a observar |
| --- | --- | --- |
| T01 | Cadastrar nova conta bancária fictícia no perfil correto; conferir na visão geral | Seleção incorreta de perfil ou tentativa de salvar duas operações |
| T02 | Registrar despesa previsível e valor sintético; verificar persistência | Campo monetário inválido, modalidade errada, erro de validação invisível |
| T03 | Consultar saldo de uma conta e diferenciar saldo desconhecido de zero | Interpretar ausência de informação como R$ 0,00 |
| T04 | Confirmar movimentação de pagamento com conta de origem específica | Confirmar sem perceber efeito financeiro; cancelar e ainda gravar |
| T05 | Alterar perfil financeiro autorizado e confirmar retorno à seleção anterior | Editar perfil distinto ou descartar alterações por engano |
| T06 | Exportar dados financeiros do núcleo autorizado e conferir escopo | Exportar dados de outros perfis ou permissões inadvertidamente |
| T07 | Importar arquivo **sintético** em staging, revisar e confirmar conscientemente | Confirmação acidental, duplicação ou atribuição a perfil indevido |

Repetir quando viável em desktop (teclado) e mobile (toque), temas claro/escuro, usuário comum e administrador onde a autorização permite. Não peça a um usuário comum que execute tarefa administrativa: registre impedimento como controle esperado, não erro.

## Medições separadas (não combiná-las em escore único)

- **Conclusão:** cada tarefa `sucesso`, `falha`, `não autorizado` ou `interrompido`; taxa = sucessos / tarefas elegíveis iniciadas, com amostra `n` sempre informada.
- **Erros:** número e tipo de ações incorretas, com distinção entre erros recuperados, prevenção do sistema e erros que afetam lançamentos.
- **Tempo:** início na leitura da tarefa e término quando usuário confirma resultado na interface. Informar mediana e dispersão, sem excluir falhas silenciosamente.
- **Satisfação:** pergunta pós-tarefa em escala de 1 a 7 («Quão fácil foi realizar esta tarefa?»), reportando distribuição e `n`, sem transformar em medida de tempo.
- **Acessibilidade observada:** navegação por Tab/Shift+Tab, Escape, foco restaurado, mensagens associadas a campos, leitor de tela quando disponível, reflow e zoom; não representa certificado WCAG.

## Roteiro do facilitador

1. Mostrar objetivo, **sem indicar cliques**. Confirmar que a pessoa entende que todos os dados são fictícios.
2. Começar cronômetro quando o participante inicia a tarefa. Não intervir até desistência, risco ou bloqueio operacional.
3. Registrar sucesso/falha, duração, quantidade de erros, ajuda externa, comentários sobre rótulos («Perfil financeiro», «Conta de origem», «Confirmar pagamento», «Importar para staging») e satisfação 1–7.
4. Validar na UI que o registro foi criado exatamente no escopo correto, sem introduzir lançamento extra. Para importação, contar duplicatas e conferir revisão prévia.
5. Comparar resultados entre versões apenas com tarefas/ambientes e participantes equivalentes. Alterações de confirmação sensível precisam passar testes de segurança mesmo quando aumentarem segundos da tarefa.

**Situação da presente entrega:** nenhum participante foi recrutado nem tarefa humana observada. Taxa, tempo, erros e satisfação = **não medidos**. O protocolo não deve ser apresentado como resultado de pesquisa com usuários.
