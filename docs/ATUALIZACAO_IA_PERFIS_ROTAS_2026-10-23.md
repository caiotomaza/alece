# ALECE — Presets de IA, modal de Perfis e rotas PT-BR

Atualização incremental da versão com seis códigos de recuperação. **Não substitua** `.env`, os volumes Docker, backups ou logs. Nenhuma migração Django nova foi introduzida.

## IA: uso

`Configurações > API de IA > +`: selecione OpenAI, Google Gemini, DeepSeek, Groq, Mistral AI ou OpenRouter. Informe somente a API key/token, confirme e salve. Nome, endpoint HTTPS, modelo padrão, seções de análise (despesas, investimentos e movimentações) e habilitação são resolvidos pelo servidor. Chaves existentes podem ser mantidas sem reenviar.

| Provedor | Endpoint fixo | Modelo inicial |
|---|---|---|
| OpenAI | https://api.openai.com/v1/chat/completions | gpt-4.1-mini |
| Google Gemini | https://generativelanguage.googleapis.com/v1beta/openai/chat/completions | gemini-2.5-flash |
| DeepSeek | https://api.deepseek.com/chat/completions | deepseek-chat |
| Groq | https://api.groq.com/openai/v1/chat/completions | llama-3.3-70b-versatile |
| Mistral | https://api.mistral.ai/v1/chat/completions | mistral-small-latest |
| OpenRouter | https://openrouter.ai/api/v1/chat/completions | openai/gpt-4.1-mini |

As APIs e os modelos podem mudar; se um fornecedor retirar um modelo, a requisição falhará de maneira explícita, sem alteração de dados. A implementação usa compatibilidade Chat Completions: ela não suporta automaticamente todo modelo/provedor do mercado (ex.: API nativa Anthropic Claude). Para os presets, apenas o endpoint exato do catálogo é autorizado sem `ALECE_AI_ALLOWED_HOSTS`. Integrações personalizadas já existentes continuam exigindo allowlist.

### Proteção do token

A chave é escrita pelo usuário não privilegiado do serviço web em `app_ai_tokens` (`/app/private/ai/provider-<id>.key`), com diretório `0700` e arquivo `0600`, e **não é enviada ao PostgreSQL**. A chave não é exibida depois da gravação e não é incluída em logs. O volume é persistente e deve ser protegido e incluído no backup de segredos: são arquivos em texto claro protegidos por permissões do sistema, **sem criptografia adicional em repouso**. A segurança pressupõe host e volume Docker protegidos. Não publique diretório, dump ou volume em repositórios.

`ALECE_AI_ALLOWED_HOSTS` continua necessário exclusivamente para integrações personalizadas antigas. A emissão de análises permanece manual: administrador informa perfil e área e marca consentimento para enviar até 40 registros importados confirmados à API escolhida. Nenhum envio automático.

## Perfis

Em `Configurações > Perfis`, o botão `+` cria. O lápis de cada linha abre **um único modal** que permite atualizar nome, ícone, renda e arquivamento, e gerenciar níveis de acesso para usuários comuns por módulo. Não existe exclusão física do perfil financeiro; `Arquivado` preserva lançamentos e rastreabilidade. O salvamento das permissões usa o serviço de autorização existente, com verificação de administrador no backend.

## Rotas canônicas

- `/visao-geral/`, `/despesas/`, `/investimentos/`, `/movimentacoes/`, `/configuracoes/`
- `/entrar/`, `/sair/`, `/senha/alterar/`, `/recuperacao/`, `/recuperacao/usar/`, `/recuperacao/gerar/`, `/configuracao-inicial/`
- `/financas/nucleos/{id}/perfis/`, `/financas/perfis/{id}/gerenciar/`, `/financas/perfis/{id}/permissoes/`, `/financas/perfis/{id}/importacoes/novo/`
- `/sistema/usuarios/{nucleo_id}/{usuario_id}/editar/`, `/sistema/logs-sistema/`, `/saude/ativo/`, `/saude/pronto/`, `/administracao/`

Nomes internos das rotas Django foram preservados; os `reverse()` geram os caminhos PT-BR. Os caminhos antigos em `/finance/`, `/core/`, `/login/` e similares ainda resolvem as views anteriores para não interromper POSTs e favoritos. Serão removidos somente em uma versão futura após auditoria de consumidores externos.

## Implantação

1. Pare somente a atualização da aplicação; mantenha banco e volumes preservados. Verifique espaço em disco e acesso administrativo ao Docker.
2. Faça dump consistente do PostgreSQL, e backup do código, `.env` e volumes críticos, registrando SHA-256 e validando imediatamente. O patch inclui `Aplicar-ALECE-Atualizacao.ps1` que automatiza o backup de **arquivos do patch**, mas não substitui o backup do banco e dos volumes de segredos.
3. Na raiz da instalação, execute `docker compose config --quiet`, e `docker compose up -d --build web` somente após aplicação.
4. Confirme login, edição de perfis e permissões, a renderização do modal, `GET /saude/ativo/`, rotas canônicas e antiga `/login/`.
5. Rollback: restaure os arquivos do arquivo ZIP de backup e seu `.env` original, valide SHA-256, então reconstrua somente `web`. O volume `app_ai_tokens` não precisa ser excluído. **Nunca use `docker compose down -v`**.

## Fontes oficiais de compatibilidade de API

- https://platform.openai.com/docs/api-reference/chat/create
- https://ai.google.dev/gemini-api/docs/openai/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://console.groq.com/docs/api-reference
- https://docs.mistral.ai/api/endpoint/chat
- https://openrouter.ai/docs/api-reference/overview
