# Roteiro de homologação de tecnologia assistiva (a executar)

> **Estado:** não realizado neste ambiente. Documenta como executar e registrar reprovações com URL/tela, conta de teste, viewport, navegador/versão, problema, passo e evidência, sem dados financeiros verdadeiros.

## Jornadas obrigatórias por plataforma

- **Windows + NVDA + Firefox/Chrome**: com Tab/Shift+Tab, Enter, Espaço, Escape e setas, navegar menu, selecionar perfil, abrir modal, editar/cancelar/excluir com confirmação, validar campos, ver retorno de erro, ler tabelas financeiras por cabeçalhos e acessar os `<details>` de cada gráfico. Registrar pronúncia de valores monetários e os avisos de status.
- **macOS/iOS + VoiceOver + Safari**: repetir login, recuperação, perfis, despesas, investimentos e IA; testar rotor de landmarks, títulos, tabelas e campos e retorno de foco após modal.
- **Android + TalkBack + Chrome**: repetir tarefas equivalentes com gestos de swipe/foco, explorar por toque, navegação por cabeçalhos, lista de controles e leitura das tabelas extensas.
- **Teclado sem leitor de tela**: iniciar com Tab; skip link visível; foco sempre perceptível, não encoberto, não preso; Escape protege mudanças pendentes; restaurar foco após diálogos; menu e details operáveis; sem dependência de mouse.

## Matriz visual manual

Verificar: 320/390/768/1280/1920 CSS px × claro/escuro; Chrome/Firefox/Safari conforme disponíveis; zoom nativo 200% e 400%; texto até 200%; orientação retrato/paisagem; `prefers-reduced-motion`; high contrast/forced colors; hover/foco e drag se existir. Capturar antes/depois **das telas autenticadas reais** com fixture isolado e sem PII, não confundir com catálogo.

## Scanner

Instalar `@axe-core/playwright` em ambiente com rede e executar scanner por jornada/tema/viewport seguindo https://playwright.dev/docs/accessibility-testing . Arquivar JSON bruto e corrigir achados, exceto não aplicáveis justificados. Passagem no scanner **não declara conformidade WCAG 2.2 AA**.
