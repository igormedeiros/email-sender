# 🚀 Deployment Guide - Treineinsite Email Sender v2.0.1

**Data:** November 6, 2025  
**Status:** ✅ PRONTO PARA DEPLOY  
**Versão:** 2.0.1 (Bug fixes inclusos)

---

## ✅ Pré-Requisitos de Deploy

### Sistema
- [x] Python 3.12+
- [x] PostgreSQL 12+
- [x] uv (gerenciador de dependências)
- [x] Linux/Mac (ou WSL2 no Windows)

### Acesso
- [x] Credenciais PostgreSQL
- [x] Credenciais SMTP (smtplw.com.br)
- [x] Acesso SSH à VPS (se usar)

### Configuração
- [x] `.env` com credenciais
- [x] `config/config.yaml` com parametrizações
- [x] `config/email.yaml` com conteúdo dinâmico
- [x] `templates/email.html` com template

---

## 🔍 Verificação Pré-Deploy

### 1. Testar SQL Localmente
```bash
# Conectar ao PostgreSQL
psql -h easypanel.treineinsite.com.br -U treine -d treineinsite

# Testar SQL TEST mode (esperado: 1 contato)
SELECT * FROM select_recipients_for_message(1, true);

# Testar SQL PROD mode (esperado: 14.569 contatos)
SELECT * FROM select_recipients_for_message(1, false);
```

### 2. Testar CLI Localmente
```bash
# Entrar no diretório
cd /home/igormedeiros/projects/treineinsite/treineinsite

# Sincronizar dependências
uv sync

# Testar CLI com input automático
printf "1\n1\ns\n" | uv run -m email_sender.cli

# Esperado:
# - Menu interativo
# - Opção 1 (Enviar)
# - Mode 1 (TEST)
# - Confirm (s)
# - Email enviado para igor.medeiros@gmail.com
```

### 3. Verificar Git Status
```bash
# Ver commits mais recentes
git log --oneline -5

# Esperado:
# 8e5e8bd docs: Add project completion report
# a0cda9c docs: Add comprehensive bug fix summary
# 21e4e54 fix: SQL operator precedence and deduplication

# Verificar status limpo
git status
# Expected: working tree clean
```

---

## 📦 Deploy em Produção

### Opção 1: Deploy Manual em VPS

```bash
# 1. SSH para VPS
ssh user@seu-vps.com

# 2. Clone ou atualizar repositório
cd /path/to/treineinsite
git pull origin master

# 3. Sincronizar dependências
uv sync

# 4. Testar comando
printf "2\n1\nn\n" | timeout 30 uv run -m email_sender.cli
# (Opção 2 = PROD, Mode 1, Cancel para não enviar)

# 5. Pronto para produção
echo "✅ Deploy completo"
```

### Opção 2: Deploy com systemd (recomendado)

```bash
# 1. Criar arquivo de serviço
sudo nano /etc/systemd/system/treineinsite-emailer.service

# 2. Adicionar conteúdo:
[Unit]
Description=Treineinsite Email Sender
After=network.target postgresql.service

[Service]
Type=simple
User=treineinsite
WorkingDirectory=/home/treineinsite/projects/treineinsite
Environment="PATH=/home/treineinsite/.local/bin"
ExecStart=/home/treineinsite/.local/bin/uv run -m email_sender.cli
Restart=on-failure
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

# 3. Ativar serviço
sudo systemctl daemon-reload
sudo systemctl enable treineinsite-emailer.service
sudo systemctl start treineinsite-emailer.service

# 4. Verificar status
sudo systemctl status treineinsite-emailer.service

# 5. Ver logs
sudo journalctl -u treineinsite-emailer.service -f
```

### Opção 3: Deploy com Docker (avançado)

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Instalar uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copiar projeto
COPY . .

# Sincronizar dependências
RUN /root/.local/bin/uv sync

# Executar CLI
CMD ["/root/.local/bin/uv", "run", "-m", "email_sender.cli"]
```

Build e execute:
```bash
docker build -t treineinsite-emailer .
docker run -e DB_PASSWORD=... -e SMTP_PASSWORD=... treineinsite-emailer
```

---

## 🧪 Testes Pós-Deploy

### 1. Verificar Email Enviado
```bash
# Verificar inbox de igor.medeiros@gmail.com
# Procurar por email com assunto: "🔥 BLACK FRIDAY: 50% OFF..."
# Esperado: 1 email (do teste)
```

### 2. Verificar Database
```bash
# Conectar ao PostgreSQL
psql -h easypanel.treineinsite.com.br -U treine -d treineinsite

# Ver última mensagem enviada
SELECT m.id, m.subject, COUNT(l.id) as sent_count
FROM tbl_messages m
LEFT JOIN tbl_message_logs l ON m.id = l.message_id AND l.event_type = 'sent'
GROUP BY m.id, m.subject
ORDER BY m.id DESC
LIMIT 1;

# Esperado: 1 message, 1 sent
```

### 3. Verificar Logs
```bash
# Se usar systemd
sudo journalctl -u treineinsite-emailer.service -n 50

# Se usar direto
tail -100 reports/email_report_*.txt

# Esperado: "Envio concluído: 1 enviados, 0 falhas"
```

---

## 📊 Monitoramento em Produção

### Métricas a Monitorar
```
1. Emails enviados por dia
2. Taxa de sucesso vs falhas
3. Tempo médio de envio
4. Contatos com problemas
5. Bounces reportados
```

### Alertas Recomendados
```
⚠️ Se taxa de erro > 5%
⚠️ Se tempo de envio > 10 minutos
⚠️ Se serviço cai > 2 vezes em 1 dia
⚠️ Se emails com bounce > 100
```

### Health Check
```bash
# Script para verificar saúde do sistema
#!/bin/bash

# Teste 1: PostgreSQL
psql -h easypanel.treineinsite.com.br -U treine -d treineinsite \
  -c "SELECT 1" > /dev/null && echo "✅ DB OK" || echo "❌ DB FAIL"

# Teste 2: Últimas mensagens
psql -h easypanel.treineinsite.com.br -U treine -d treineinsite \
  -c "SELECT COUNT(*) FROM tbl_message_logs WHERE created_at > NOW() - INTERVAL '1 day'" \
  > /dev/null && echo "✅ Recent logs OK" || echo "❌ No recent logs"

# Teste 3: CLI
timeout 30 uv run -m email_sender.cli --help > /dev/null \
  && echo "✅ CLI OK" || echo "❌ CLI FAIL"
```

---

## 🔄 Rollback Plan (se necessário)

### Se algo der errado:

```bash
# 1. Identificar commit anterior
git log --oneline -5

# 2. Voltar para versão anterior
git revert HEAD
# OU
git reset --hard <previous-commit-hash>

# 3. Sincronizar dependências
uv sync

# 4. Testar novamente
printf "2\n1\nn\n" | uv run -m email_sender.cli

# 5. Push (se necessário)
git push origin master -f
```

---

## 📝 Checklist de Deploy Final

### Pré-Deploy
- [ ] Todos os testes passando
- [ ] SQL validated em isolation
- [ ] CLI testado locally
- [ ] Git status clean
- [ ] Credenciais configuradas

### Deploy
- [ ] Código updateado em produção
- [ ] Dependências sincronizadas
- [ ] Configurações atualizadas
- [ ] Database schema validado
- [ ] Serviço iniciado com sucesso

### Pós-Deploy
- [ ] Email enviado para test@example.com
- [ ] Verificar logs em produção
- [ ] Confirmar com usuário
- [ ] Monitorar por 24 horas
- [ ] Documentar qualquer issue

---

## 📞 Contatos e Suporte

### Se encontrar problemas:

1. **Verificar Logs:**
   ```bash
   tail -100 reports/email_report_*.txt
   sudo journalctl -u treineinsite-emailer.service -n 100
   ```

2. **Verificar Database:**
   ```bash
   # Conectar e rodar queries de debug
   psql -h easypanel.treineinsite.com.br -U treine -d treineinsite
   ```

3. **Testar CLI Localmente:**
   ```bash
   printf "2\n1\nn\n" | uv run -m email_sender.cli
   ```

4. **Consultar Documentação:**
   - `LESSONS_LEARNED.md` - Estratégias de debug
   - `bug_fix_sql_recipients_2025_11_06.md` - Análise técnica
   - `README.md` - Como usar o sistema

---

## ✅ Confirmação de Deploy

Quando deploy estiver completo:

```bash
# 1. Confirme localmente
echo "✅ Deploy em produção confirmado"

# 2. Notifique time
# "Treineinsite Email Sender v2.0.1 em produção"
# "Bugs de SQL operator precedence e deduplication corrigidos"
# "Sistema testado e operacional"

# 3. Monitore por 24h
# Observe métrica de emails enviados, bounces, etc
```

---

## 🎯 Success Criteria

Deploy será considerado sucesso quando:

- ✅ CLI responde em < 1 segundo
- ✅ Emails podem ser enviados sem deduplication em TEST mode
- ✅ Deduplication funciona em PROD mode
- ✅ Database queries executam em < 5 segundos
- ✅ Nenhum erro em logs por 24 horas
- ✅ Email chegou em igor.medeiros@gmail.com
- ✅ Sistema responde a health checks

---

**Próximo Passo:** Execute os testes de pré-deploy e vá para produção! 🚀

Status: ✅ PRONTO PARA DEPLOY

