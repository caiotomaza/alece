# Validação — Configurações por atalhos

- Base: `ALECE_COMPLETO_Correcao_Retorno_Saldo_Visao_Geral_2026-10-26.zip`
- Implementação: página de Configurações com cartões para conta e administração, janelas independentes para usuários, perfis e APIs, acesso ao backend restrito a administrador, rotas em pt-BR sem acentos.
- Validações locais: 23 testes independentes de Django aprovados; compilação dos módulos Python e estrutura do template/URL verificadas.
- Prévia estática Chromium: verificada em 390, 768 e 1280 px, nos temas claro/escuro. Sem transbordamento horizontal na simulação. Não substitui Django real.
- Pendente: testes de integração Django/PostgreSQL e navegação real no Docker.
- Aviso pytest: opção DJANGO_SETTINGS_MODULE não reconhecida no ambiente sem pytest-django.
- Redefinir ambiente: cartão não interativo; função destrutiva NÃO implementada, por falta de definição segura.
- Migrações: nenhuma.
