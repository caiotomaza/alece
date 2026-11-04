# Atualização e rollback — modal de renda

1. Interrompa alterações simultâneas durante a publicação, se possível, e confirme acesso administrativo e método de recuperação.
2. Mantenha o ZIP da versão anterior `ALECE_COMPLETO_VISAO_GERAL_REFINADO_2026-10-28.zip`, acompanhado de SHA-256; preserve também o backup atual da instalação e dump PostgreSQL com hash verificado.
3. Confira o checksum do novo ZIP; extraia **os arquivos da raiz** para `alece`. Preserve o `.env` produtivo e volumes persistidos. Não faça limpeza destrutiva de arquivos, banco ou volumes.
4. Se o ambiente for Docker Compose compatível com `compose.yaml`, reconstrua apenas `web` pelo procedimento aprovado do operador, mantendo os demais serviços e volumes. Confirme que os estáticos coletados incorporaram `alece_overview_income.js` e a nova versão do CSS.
5. Homologue com base isolada; depois, na Visão geral, abra Renda, confira perfis autorizados, altere valores fictícios, Salvar, revise confirmação na página e log. Teste invalidade e a opção Cancelar sem gravação.
6. Em caso de falha, restaure os arquivos do ZIP-base anterior validado, reconstrua apenas `web` e verifique a rota de saúde e os fluxos anteriores. **Não restaure o PostgreSQL automaticamente**, pois não houve migrations e dados legítimos podem ter sido alterados após o backup.

A publicação requer validação funcional antes de declarar sucesso. Logs e backups não devem ser removidos automaticamente.
