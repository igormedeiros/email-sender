# 📈 Proposta de Melhorias de Performance - Email Sender

**Data:** 11 de Novembro de 2025  
**Status:** Análise Completa  
**Impacto Estimado:** 5-10x mais rápido

---

## 🔍 Análise de Gargalos Identificados

### 1. **Tempo de Envio SMTP - CRÍTICO ⚠️**

**Problema:**
- Cada `SMTP.send_message()` leva ~2-5 segundos (network round-trip)
- Para 1.000 emails = 2.000-5.000 segundos (~33-83 minutos!)
- Envio **sequencial** (um de cada vez)

**Evidência no código:**
```python
# ❌ LENTO - Sequencial
for i, contact_data in enumerate(contacts):
    self.smtp.send_email(...)  # Aguarda resposta do servidor
    time.sleep(batch_delay)     # Aguarda 5s depois de cada 200 emails
```

**Impacto atual:**
- Batch size: 200 emails
- Batch delay: 5 segundos
- = **1 pausa de 5s a cada 200 emails**
- = Overhead de ~2% por pausa

---

### 2. **Verificação de Duplicatas em BD - MODERADO ⚠️**

**Problema:**
- Query SQL a cada email em MODO PRODUÇÃO: `check_email_already_sent.sql`
- 1 query por email = N roundtrips ao banco
- Network latency: ~50-100ms por query
- Para 10.000 emails = 500-1000s (~8-16 minutos extras!)

**Evidência no código:**
```python
# ❌ LENTO - Query por email
if not is_test_mode:
    already_sent = self.db.fetch_one(check_query_path, [contact_id, message_id])
    # Round-trip de rede ~50-100ms
```

**Impacto atual:**
- Em PRODUÇÃO com 10.000 emails: **+8-16 minutos**
- Em TESTE: ✅ Sem impacto (bypassa esse passo)

---

### 3. **Gravação de Logs por Email - LEVE ⚠️**

**Problema:**
- `INSERT` no `tbl_message_logs` a cada email enviado
- Sem batching = N transactions
- Para 10.000 emails = 10.000 transactions individuais

**Evidência no código:**
```python
# ❌ LENTO - Transação por email
insert_log_path = "sql/messages/insert_message_sent_log.sql"
self.db.execute(insert_log_path, [contact_id, message_id])
```

**Impacto atual:**
- Sem impacto crítico (rodando em paralelo com SMTP)
- Mas adiciona overhead de BD

---

### 4. **Sem Conexão Reutilizável - LEVE ⚠️**

**Situação Atual:**
- ✅ SMTP: Conexão reutilizada (bom!)
- ❌ PostgreSQL: Conexão única mas múltiplos queries

---

## 🚀 Soluções Propostas

### **SOLUÇÃO 1: Paralelização com Threading (RECOMENDADO)**

**Descrição:** Usar threads para enviar múltiplos emails em paralelo

**Código Proposto:**
```python
from concurrent.futures import ThreadPoolExecutor
import threading

max_workers = 5  # 5 threads paralelos
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = []
    for contact in contacts:
        future = executor.submit(send_single_email, contact)
        futures.append(future)
    
    # Aguardar conclusão
    for future in futures:
        future.result()
```

**Benefício:**
- Enquanto 1 thread aguarda resposta SMTP (2-5s)
- Outras 4 threads já estão enviando
- **Ganho: ~3-5x mais rápido**
- 10.000 emails em ~40-60 minutos → ~10-15 minutos

**Desvantagens:**
- Requer sincronização cuidadosa
- Limite de conexões simultâneas do servidor SMTP

**Implementação:**
- ⏱️ ~2-3 horas
- Risco: Médio
- Impacto: Muito Alto

---

### **SOLUÇÃO 2: Pré-carregar Duplicatas em Memória**

**Descrição:** Em PRODUÇÃO, carregar lista de emails já enviados ANTES do loop

**Código Proposto:**
```python
# ✅ RÁPIDO - Carregar tudo uma vez
already_sent_ids = set()
if not is_test_mode:
    query = "SELECT contact_id FROM tbl_message_logs WHERE message_id = $1"
    logs = self.db.fetch_all(query, [message_id])
    already_sent_ids = {log['contact_id'] for log in logs}

# Loop
for contact in contacts:
    if contact['id'] in already_sent_ids:
        continue  # O(1) lookup em memória
    # ... enviar email
```

**Benefício:**
- Elimina 10.000 queries SQL
- **Ganho: +8-16 minutos economizados em PRODUÇÃO**
- 1 query ao invés de 10.000

**Desvantagens:**
- Usa um pouco mais de memória (negligenciável)
- Carrega todos os IDs de uma vez

**Implementação:**
- ⏱️ ~30 minutos
- Risco: Baixo
- Impacto: Alto em PRODUÇÃO

---

### **SOLUÇÃO 3: Batching de INSERTs**

**Descrição:** Agrupar múltiplos INSERTs em 1 query

**Código Proposto:**
```python
# ❌ ATUAL - 10.000 queries
for contact in contacts:
    db.execute("INSERT INTO tbl_message_logs VALUES ($1, $2)", [contact_id, message_id])

# ✅ OTIMIZADO - 1 query com batch
batch_insert = []
for contact in contacts:
    batch_insert.append((contact_id, message_id))

# Inserir em batch (ex: 1000 por vez)
for i in range(0, len(batch_insert), 1000):
    batch = batch_insert[i:i+1000]
    placeholders = ','.join(['($%d,$%d)' % (j*2+1, j*2+2) for j in range(len(batch))])
    db.execute(f"INSERT INTO tbl_message_logs VALUES {placeholders}", flatten(batch))
```

**Benefício:**
- Reduz de 10.000 queries para ~10 queries
- **Ganho: ~200-500ms economizados**

**Desvantagens:**
- SQL um pouco mais complexo
- Requer cuidado com grandes batches

**Implementação:**
- ⏱️ ~1 hora
- Risco: Baixo
- Impacto: Leve

---

### **SOLUÇÃO 4: Compilar Template HTML Uma Única Vez**

**Descrição:** Template HTML é processado PARA CADA EMAIL (desnecessário)

**Código Atual - LENTO:**
```python
# ❌ Processado a cada email!
for contact in contacts:
    message_html = Path(template_path).read_text()  # I/O DISCO
    message_html = message_html.replace('{data}', ...)
    # ... enviar
```

**Código Otimizado:**
```python
# ✅ Carregar e processar ANTES do loop
template = Path(template_path).read_text()  # Uma vez
template = template.replace('{data}', evento['data'])  # Placeholders estáticos
template = template.replace('{link}', evento['link'])

for contact in contacts:
    # Apenas substituir placeholders dinâmicos (email, nome)
    personalized = template.replace('{email}', contact['email'])
    # ... enviar
```

**Benefício:**
- Elimina leitura de disco a cada email
- Elimina processamento repetitivo
- **Ganho: ~100-300ms no total**

**Desvantagens:**
- Nenhuma significativa

**Implementação:**
- ⏱️ ~30 minutos
- Risco: Muito baixo
- Impacto: Leve-Médio

---

## 📊 Comparação de Impactos

| Solução | Implementação | Ganho | Impacto | Risco |
|---------|--------------|-------|--------|-------|
| **1. Paralelização (5 threads)** | 2-3h | 🚀 3-5x | Muito Alto | Médio |
| **2. Pré-carregar Duplicatas** | 30m | ⭐ +8-16m | Alto (PROD) | Baixo |
| **3. Batching de INSERTs** | 1h | 📈 +200-500ms | Leve | Baixo |
| **4. Template Uma Vez** | 30m | 📈 +100-300ms | Leve | Muito Baixo |

---

## 🎯 Recomendação de Implementação

### **Fases:**

#### **FASE 1: Rápido (30 minutos) - Implementar Agora**
- ✅ **Solução 4:** Template Uma Vez
- ✅ **Solução 2:** Pré-carregar Duplicatas (PROD)
- 📈 **Ganho imediato:** ~2% para TESTE, ~20% para PRODUÇÃO

#### **FASE 2: Médio (1 hora) - Próxima Sprint**
- ✅ **Solução 3:** Batching de INSERTs
- 📈 **Ganho adicional:** +5%

#### **FASE 3: Avançado (2-3 horas) - Quando Necessário**
- ✅ **Solução 1:** Paralelização com Threading
- 📈 **Ganho massivo:** 3-5x mais rápido

---

## 📋 Plano de Implementação - FASE 1

### Arquivo: `src/email_sender/email_service.py`

**Mudança 1:** Pré-processar template antes do loop

```python
# ANTES: (linha ~115)
for i, contact_data in enumerate(contacts):
    try:
        # Cada iteração relê e processa template
        message_html = Path(template_path).read_text(encoding='utf-8')
        message_html = message_html.replace('{data_evento}', evento.get('data', ''))
        # ... 10 substituições
        
        # ENVIAR
        self.smtp.send_email(to_email=email, content=message_html, ...)

# DEPOIS:
# Carregar template UMA VEZ (antes do loop)
template_path = self.config.email_config.get('template_path', 'config/templates/email.html')
try:
    message_html_template = Path(template_path).read_text(encoding='utf-8')
    
    # Processar placeholders ESTÁTICOS (evento data, link, etc)
    evento = content_config.get('evento', {})
    message_html_template = message_html_template.replace('{data_evento}', evento.get('data', ''))
    message_html_template = message_html_template.replace('{link_evento}', evento.get('link', ''))
    message_html_template = message_html_template.replace('{cidade}', evento.get('cidade', ''))
    message_html_template = message_html_template.replace('{uf}', evento.get('uf', ''))
    message_html_template = message_html_template.replace('{local}', evento.get('local', ''))
    message_html_template = message_html_template.replace('{horario}', evento.get('horario', ''))
except Exception as e:
    message_html_template = '<p>Sem conteúdo</p>'

# Usar no loop
for i, contact_data in enumerate(contacts):
    try:
        # ... checar duplicatas
        
        # Usar template pré-processado
        message_html = message_html_template  # Sem reprocessamento
        
        # ENVIAR
        self.smtp.send_email(to_email=email, content=message_html, ...)
```

**Mudança 2:** Pré-carregar IDs de duplicatas (PRODUÇÃO)

```python
# ANTES: (linha ~155)
if not is_test_mode:
    already_sent = self.db.fetch_one(check_query_path, [contact_id, message_id])
    if already_sent:
        continue

# DEPOIS:
# Carregar TODOS os já-enviados uma única vez (antes do loop)
already_sent_contact_ids = set()
if not is_test_mode:
    try:
        check_all_sent = "sql/messages/check_all_emails_already_sent.sql"
        all_sent = self.db.fetch_all(check_all_sent, [message_id])
        already_sent_contact_ids = {row['contact_id'] for row in all_sent}
    except Exception as e:
        log.warning(f"Erro ao pré-carregar duplicatas: {e}")

# Usar no loop
for i, contact_data in enumerate(contacts):
    try:
        # ... extrair contact_id
        
        # Verificação em O(1) - memória
        if contact_id in already_sent_contact_ids:
            continue
        
        # ... enviar
```

---

## 🧪 Testes de Performance

### Cenários de Teste:

**Teste 1: 1.000 emails (TESTE mode)**
```bash
# ANTES
Time: ~2 minutos
Throughput: 500 emails/min

# DEPOIS (Fase 1)
Time: ~1:55 min (-3% para TESTE, template é negligenciável)
Throughput: 510 emails/min
```

**Teste 2: 10.000 emails (PRODUÇÃO mode)**
```bash
# ANTES
Time: ~20 minutos
- SMTP: 16-20 min
- BD Query Duplicatas: +8-16 min
- = ~25-35 minutos total

# DEPOIS (Fase 1)
Time: ~18-22 minutos (-20%)
- SMTP: 16-20 min (igual)
- BD Query Duplicatas: -8 min (pré-carregado)
- = ~18-22 minutos
```

**Teste 3: 10.000 emails (PRODUÇÃO mode + Paralelização)**
```bash
# COM Fase 3 (5 threads)
Time: ~4-6 minutos (-80%)
- 5 threads paralelos
- Cada thread envia ~2000 emails
- = ~4-6 minutos total
```

---

## 🔧 Arquivos a Modificar

### FASE 1 (Implementar Agora):

1. **`src/email_sender/email_service.py`**
   - Linhas ~115-135: Pré-processar template
   - Linhas ~140-160: Pré-carregar duplicatas

### FASE 2 (Próxima):

2. **`src/email_sender/db.py`**
   - Adicionar método `execute_batch()` para batching de INSERTs

### FASE 3 (Quando Necessário):

3. **`src/email_sender/email_service.py`**
   - Refatorar loop com `ThreadPoolExecutor`

---

## 📌 Próximos Passos

1. ✅ **Revisar esta proposta**
2. ⏳ **Aprovar Fase 1** 
3. 🔧 **Implementar Fase 1** (30 minutos)
4. 🧪 **Testar com 10.000 emails**
5. 📊 **Medir ganho real**
6. 🚀 **Deploy**

---

**Estimativa Total de Ganho (Todas as Fases):** 🚀 **5-10x mais rápido**

