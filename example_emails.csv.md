# Exemplo de Estrutura do Arquivo de Emails

Este arquivo descreve a estrutura do arquivo CSV de emails que deve ser criado na pasta `data/`. 
**IMPORTANTE**: Arquivos CSV com dados reais NUNCA devem ser versionados no Git.

## Estrutura do Arquivo `emails_geral.csv`

O arquivo principal de emails deve ter a seguinte estrutura:

```csv
email,enviado,falhou,descadastro,nome,empresa,cargo
usuario1@exemplo.com,,,,,Empresa A,Engenheiro
usuario2@exemplo.com,,,,,Empresa B,Diretor
usuario3@exemplo.com,ok,,,,Empresa C,Gerente
usuario4@exemplo.com,,ok,,,Empresa D,Técnico
usuario5@exemplo.com,,,S,,Empresa E,Analista
```

### Colunas Obrigatórias

| Coluna | Descrição | Valores Possíveis |
|--------|-----------|-------------------|
| email | Endereço de email (obrigatório) | Endereço válido (ex: usuario@dominio.com) |
| enviado | Status de envio | "" (não enviado), "ok" (enviado com sucesso) |
| falhou | Status de falha | "" (sem falha), "ok" (falhou no envio) |
| descadastro | Flag de descadastramento | "" (enviar), "S" (não enviar) |

### Colunas Opcionais (Personalizáveis)

Você pode adicionar colunas extras conforme necessário para personalizar os emails:

| Coluna | Descrição |
|--------|-----------|
| nome | Nome do destinatário |
| empresa | Nome da empresa |
| cargo | Cargo do destinatário |
| [outros] | Qualquer outra informação necessária |

## Estrutura do Arquivo `test_emails.csv`

O arquivo para testes deve ter a mesma estrutura:

```csv
email,enviado,falhou,descadastro,nome,empresa,cargo
test@exemplo.com,,,,,Empresa Teste,Gerente
test2@exemplo.com,,,,,Empresa Teste 2,Diretor
```

## Estrutura do Arquivo `descadastros.csv`

O arquivo de emails descadastrados deve conter apenas uma coluna com os endereços:

```csv
email
usuario5@exemplo.com
descadastrado@exemplo.com
outro@exemplo.com
``` 