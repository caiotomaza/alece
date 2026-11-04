# Pipeline de importação financeira (projeto futuro)

CSV/PDF são entrada **não confiável**. Nada é debitado após upload. Modelo esperado:

```text
upload → validação (extensão, MIME, tamanho, formato) → parsing em staging →
normalização → detecção de duplicatas (fingerprint + contexto) → sugestão explicável →
revisão/edição do usuário → confirmação atômica no ledger → auditoria
```

- Um adaptador por banco/formato, sem parser monolítico de extratos.
- CSV: charset detectado com limite, delimitador explícito e controle de cabeçalho; CSV formula injection também deve ser tratada em **exportações**.
- PDF: detectar texto nativo vs imagem, isolamento, limite de páginas/tempo/recursos e tratamento de PDFs malformados. OCR apenas depois de validar a necessidade.
- Guardar origem, hash, data, perfil, versão do parser e mapeamentos escolhidos pelo usuário; retenção/eliminação de documentos sensíveis definida na política antes de lançar.
- Duplicidade: o identificador do banco pode não ser global; usar contexto transacional e ação explícita de revisão.
- Sem integração real de Open Finance nesta versão. Não coletar credenciais bancárias para simular importação.
