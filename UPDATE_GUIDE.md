# 🔄 Atualização de Integração - Worker bot-xml-gms

## 📝 O que mudou?

O worker `bot-xml-gms` foi atualizado para integrar com a nova API v1 do Maestro RPS.

---

## 🚀 Principais Mudanças

### 1️⃣ Novo Formato de Mensagem

**Antes (Antigo):**
```json
{
  "task_id": "123",
  "stores": ["Loja 001"],
  "document_type": "NFe",
  ...
}
```

**Agora (Novo):**
```json
{
  "job_id": "uuid-do-job",
  "parameters": {
    "stores": ["Loja 001"],
    "document_type": "NFe",
    ...
  }
}
```

### 2️⃣ Novos Endpoints de Reporte

| Antigo | Novo |
|--------|------|
| `POST /api/tasks/{id}/status` | ❌ Removido |
| - | ✅ `POST /api/v1/jobs/{id}/start` |
| - | ✅ `POST /api/v1/jobs/{id}/log` |
| - | ✅ `POST /api/v1/jobs/{id}/complete` |
| - | ✅ `POST /api/v1/jobs/{id}/fail` |

### 3️⃣ Logs em Tempo Real

Agora o worker envia logs durante a execução:
- ✅ Início da execução
- ✅ Progresso por loja
- ✅ Warnings e erros
- ✅ Conclusão ou falha

---

## 📦 Como Usar

### 1. Reconstruir a Imagem Docker

```bash
cd /home/enzzomaciel/Automations/bot-xml-gms
docker-compose build gms-xml-worker
```

### 2. Iniciar o Worker

```bash
docker-compose up -d gms-xml-worker
```

### 3. Ver Logs

```bash
docker-compose logs -f gms-xml-worker
```

---

## 🧪 Testando a Integração

### Opção 1: Script Python

```bash
# Instalar pika se necessário
pip install pika

# Executar script de teste
python test_send_message.py
```

### Opção 2: Enviar Mensagem Manualmente

Envie esta mensagem para a fila RabbitMQ `automation_jobs`:

```json
{
  "job_id": "test-001",
  "parameters": {
    "stores": ["Loja Teste"],
    "document_type": "NFe",
    "start_date": "2025-10-01",
    "end_date": "2025-10-27",
    "gms_login_url": "https://gms.exemplo.com/login"
  }
}
```

---

## 🔍 Verificando Funcionalidade

### O que o worker deve fazer:

1. ✅ Receber mensagem do RabbitMQ
2. ✅ Chamar `POST /api/v1/jobs/{id}/start`
3. ✅ Enviar logs via `POST /api/v1/jobs/{id}/log`
4. ✅ Executar a automação
5. ✅ Chamar `POST /api/v1/jobs/{id}/complete` ou `fail`

### Logs Esperados:

```
📨 Mensagem recebida: test-001
📤 Reportando início do job test-001
📝 Enviando log [INFO]: Job test-001 iniciado...
🚀 Iniciando execução do job test-001
...
✅ Job test-001 concluído com sucesso
✅ Mensagem processada e confirmada: test-001
```

---

## ⚙️ Variáveis de Ambiente

Certifique-se de que estas variáveis estão configuradas:

```env
# RabbitMQ
RABBITMQ_HOST=maestro_rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=automation_jobs

# Maestro API
MAESTRO_API_URL=http://maestro-api:8000

# GMS Credentials
GMS_USER=seu_usuario
GMS_PASSWORD=sua_senha

# Worker
WORKER_ID=gms-worker-01
LOG_LEVEL=INFO
```

---

## 🐛 Troubleshooting

### Worker não conecta ao RabbitMQ
```bash
# Verificar se RabbitMQ está rodando
docker ps | grep rabbitmq

# Testar conexão
telnet maestro_rabbitmq 5672
```

### Mensagem não é processada
```bash
# Ver logs detalhados
docker-compose logs -f gms-xml-worker

# Verificar fila no RabbitMQ
# Acesse: http://localhost:15672
# Login: guest / guest
```

### Erro ao reportar status
```bash
# Verificar se Maestro API está rodando
curl http://maestro-api:8000/health

# Ver logs do worker
docker-compose logs gms-xml-worker | grep "Erro"
```

---

## 📚 Documentação Adicional

- `INTEGRATION_CHANGES.md` - Detalhes técnicos completos
- `IMPLEMENTATION_SUMMARY.md` - Resumo da implementação
- `worker.py` - Código-fonte atualizado
- `test_send_message.py` - Script de teste

---

## ⚠️ Importante

**BREAKING CHANGE**: Esta versão não é retrocompatível.

O Maestro **DEVE** enviar mensagens no novo formato para funcionar.

---

## 🆘 Suporte

Se encontrar problemas:

1. Verifique os logs: `docker-compose logs gms-xml-worker`
2. Consulte a documentação em `INTEGRATION_CHANGES.md`
3. Teste com `test_send_message.py`
4. Verifique as variáveis de ambiente

---

## ✅ Checklist de Implantação

- [ ] Variáveis de ambiente configuradas
- [ ] RabbitMQ rodando e acessível
- [ ] Maestro API rodando e acessível
- [ ] Imagem Docker reconstruída
- [ ] Worker iniciado
- [ ] Teste de mensagem enviado
- [ ] Logs verificados
- [ ] Reporte de status funcionando

---

**Data da Atualização:** 27 de outubro de 2025  
**Versão:** 2.0.0 (Nova integração com Maestro v1)
