# ALECE — Formulários, modais, confirmações e feedback (2026-10-27)

## Escopo e preservação

Implementação incremental sobre o Design System ALECE 1.0. O projeto permanece Django 5.2/PostgreSQL, self-hosted/GPLv3, sem dependências externas ou telemetria. As rotas continuam em português e a seleção de perfil financeiro não foi alterada. Os formulários normais e o CSRF continuam sob controle do Django; não foram alterados modelos, migrations, views ou transações financeiras.

## Contrato do componente

- `alece_modals.js`: API interna `window.AleceModal` com `confirm`, `confirmUnsaved`, `notify`, `linkErrors`, `labelDialog`, `focusStart`. Não exige biblioteca externa.
- `alece_modals.css`: estilos dos modais/confirmadores, tamanhos responsivos, rolagem própria, tokens dos dois temas e feedback por estado.
- `alece.js`: mantém aprimoramento progressivo, abertura remota de conteúdo Django, detecção de alteração e bloqueio de rolagem. Usa a API centralizada; não executa mais lote de POSTs de formulários distintos ao fechar.
- HTML `<dialog>.showModal()` torna conteúdo de fundo inerte; classe `alece-modal-open` bloqueia a rolagem do documento. `overscroll-behavior:contain` impede scroll chaining nos navegadores compatíveis.
- Título acessível vinculado via `aria-labelledby`; ausência de heading recebe nome genérico, registrada como cenário que exige título real na tela. Foco inicial em campo com erro/primeiro controle pertinente; foco retorna ao elemento invocador após fechar overlay remoto; Tab/Shift+Tab permanecem no modal. Escape e clique no fundo solicitam fechamento, nunca confirmam exclusão automaticamente.
- Campos de erros renderizados pelo Django usam o texto original. Quando o JavaScript está habilitado, `linkErrors` adiciona `aria-invalid=true` e `aria-describedby` referenciando a mensagem na região do campo. O Django 5.2 também associa erros em sua renderização padrão, desde que os templates mantenham a estrutura correta.
- Estados: `status` (informativo/sucesso) e `alert` (falha, conflito, falta de permissão). Status 403 e 409 recebem mensagens específicas, erros desconhecidos não expõem stack trace, tokens nem corpo do erro.

## Fechamento com campos modificados

| Situação | Opções / efeito |
|---|---|
| Nenhum formulário alterado | Fechar diretamente |
| Exatamente 1 formulário não sensível alterado | **Salvar**, **Descartar**, **Continuar editando** |
| Vários formulários alterados | **Descartar**, **Continuar editando** — salvar cada formulário em seu próprio botão |
| Senha, exclusão, revogação, arquivamento sensível | **Descartar**, **Continuar editando** — operação exige ação específica |
| Escape/clique externo no diálogo de confirmação | **Continuar editando** ou cancelar confirmação (jamais excluir/salvar) |

**Salvar** chama `form.requestSubmit()` exclusivamente no formulário modificado, preservando validação nativa, middleware CSRF, regras de negócio, autorização e possibilidade de resposta HTTP do servidor. Não presume êxito; o modal só abandona a página após resposta/redirect do fluxo original. Não há transação distribuída de formulários: não foi introduzida atomicidade no frontend.

## Uso em templates existentes

```html
<form method="post" data-alece-confirm="Excluir esta integração?"
      data-confirm-title="Excluir integração" data-confirm-label="Excluir">
  <!-- Django: csrf_token, validação e permissão continuam obrigatórios -->
  <button type="submit" class="button danger">Excluir</button>
</form>
```

Sem JavaScript, formulários continuam páginas HTML normais e links continuam navegáveis. Sem suporte a `<dialog>`, o aprimoramento não intercepta o POST e o backend mantém a responsabilidade de autenticar/autorizá-lo. Confirmação visual nunca deve substituir verificação de permissões, idempotência ou operações atômicas no servidor. Campos de exclusão que exigem confirmação digitada foram preservados.

## Referências verificadas

- W3C WAI-ARIA Authoring Practices — [Modal Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
- MDN — [`<dialog>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog) e [`showModal()`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLDialogElement/showModal).
- MDN — [`overscroll-behavior`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/overscroll-behavior).
- [Django 5.2 Forms API, erros e `aria-describedby`](https://docs.djangoproject.com/en/5.2/ref/forms/api/).
- W3C — [WCAG 2.2 2.4.3 (ordem de foco)](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html) e [3.3.1 (identificação de erros)](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html).

Estas referências norteiam a engenharia, não constituem declaração de conformidade WCAG.
