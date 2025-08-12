# Instruções para Copilot/IA no projeto

- Não misturar SQL ou prompts de IA dentro de código Python.
- Centralizar SQL em `sql/` com subpastas temáticas (`contacts/`, `messages/`, `events/`, `leads/`, `tags/`).
  - Cada `.sql` começa com cabeçalho de origem (workflow/nó) e variáveis usadas.
- Prompts devem ficar fora do código:
  - Regras de negócio: `.github/business_rules.prompt.md`
  - Diretrizes ao Copilot/IA: `.github/copilot-instructions.md`
  - Prompts operacionais (se houver): `prompts/`
- O código deve referenciar arquivos externos (SQL/Prompts) por caminho via configuração; nunca inline.
- Seguir `PADROES_DE_PROJETO.md` para arquitetura, imports e organização.
