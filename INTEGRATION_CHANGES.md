# Mudanças de Integração - bot-xml-gms Worker

## Resumo das Alterações

O worker foi atualizado para integrar com os novos endpoints da API do Maestro (v1).

## Principais Mudanças

### 1. Formato da Mensagem RabbitMQ

**ANTES:**
```json
{
  "task_id": "task-123",
  "stores": ["Loja 001"],
  "document_type": "NFe",
  "start_date": "2025-10-01",
  "end_date": "2025-10-27",
  "gms_login_url": "https://gms.example.com/login",
  ...
}
```

**DEPOIS:**
```json
{
  "job_id": "job-uuid-123",
  "parameters": {
    "stores": ["Loja 001"],
    "document_type": "NFe",
    "start_date": "2025-10-01",
    "end_date": "2025-10-27",
    "gms_login_url": "https://gms.example.com/login",
    "headless": true,
    "emitter": "Qualquer",
    "operation_type": "Qualquer",
    "file_type": "XML",
    "invoice_situation": "Qualquer",
    "gms_user": "optional",
    "gms_password": "optional"
  }
}
```

### 2. Novos Endpoints do Maestro

O worker agora usa os seguintes endpoints da API v1:

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/jobs/{job_id}/start` | POST | Reporta início da execução |
| `/api/v1/jobs/{job_id}/log` | POST | Envia logs durante execução |
| `/api/v1/jobs/{job_id}/complete` | POST | Reporta conclusão bem sucedida |
| `/api/v1/jobs/{job_id}/fail` | POST | Reporta falha na execução |

### 3. Novas Funções de Reporte

#### `_make_request(method, endpoint, payload)`
Helper interno para fazer requisições HTTP ao Maestro.

#### `report_status_start(job_id)`
Reporta o início da execução do job.
```python
worker.report_status_start("job-123")
```

#### `report_log(job_id, level, message)`
Envia logs em tempo real para o Maestro.
```python
worker.report_log("job-123", "INFO", "Processando loja 001...")
worker.report_log("job-123", "WARNING", "Conexão lenta detectada")
worker.report_log("job-123", "ERROR", "Falha ao baixar arquivo")
```

Níveis suportados: `INFO`, `WARNING`, `ERROR`

#### `report_status_complete(job_id, result_data)`
Reporta conclusão bem sucedida com dados do resultado.
```python
result = {
    "status": "completed",
    "summary": {...},
    "duration_seconds": 120.5
}
worker.report_status_complete("job-123", result)
```

#### `report_status_fail(job_id, error_data)`
Reporta falha com informações do erro.
```python
error_data = {
    "error": "Credenciais inválidas",
    "error_type": "AuthenticationError"
}
worker.report_status_fail("job-123", error_data)
```

### 4. Fluxo de Execução Atualizado

```
1. Mensagem recebida do RabbitMQ
   ↓
2. Parse do JSON e extração de job_id e parameters
   ↓
3. Validação de campos obrigatórios
   ↓
4. report_status_start(job_id)
   ↓
5. report_log(job_id, "INFO", "Job iniciado...")
   ↓
6. Preparação dos parâmetros do BotRunner
   ↓
7. report_log(job_id, "INFO", "Processando X loja(s)...")
   ↓
8. Execução do bot_runner.run()
   ↓
9. Análise do resultado:
   - Se sucesso → report_log + report_status_complete
   - Se falha → report_log + report_status_fail
   ↓
10. ACK/NACK da mensagem RabbitMQ
```

## Campos Obrigatórios

### Na raiz da mensagem:
- `job_id` - Identificador único do job

### Dentro de `parameters`:
- `stores` - Array de lojas
- `document_type` - Tipo de documento
- `start_date` - Data inicial (formato: YYYY-MM-DD)
- `end_date` - Data final (formato: YYYY-MM-DD)
- `gms_login_url` - URL de login do GMS

## Campos Opcionais em `parameters`:
- `headless` - Modo headless (padrão: true)
- `emitter` - Emissor (padrão: "Qualquer")
- `operation_type` - Tipo de operação (padrão: "Qualquer")
- `file_type` - Tipo de arquivo (padrão: "XML")
- `invoice_situation` - Situação da nota (padrão: "Qualquer")
- `gms_user` - Usuário GMS (usa variável de ambiente se não fornecido)
- `gms_password` - Senha GMS (usa variável de ambiente se não fornecido)

## Tratamento de Erros

O worker agora reporta erros de forma mais detalhada:

1. **JSONDecodeError**: Mensagem com JSON inválido
2. **ValueError**: Campos obrigatórios faltando
3. **Exception genérica**: Erro inesperado durante execução

Em todos os casos:
- Log detalhado é gravado localmente
- `report_log` com nível ERROR é enviado ao Maestro
- `report_status_fail` é chamado com detalhes do erro
- Mensagem recebe NACK sem requeue

## Exemplo Completo de Mensagem

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "parameters": {
    "stores": [
      "Loja Central",
      "Loja Shopping",
      "Loja Matriz"
    ],
    "document_type": "NFe",
    "start_date": "2025-10-01",
    "end_date": "2025-10-27",
    "gms_login_url": "https://gms.minhaempresa.com.br/login",
    "headless": true,
    "emitter": "Qualquer",
    "operation_type": "Qualquer",
    "file_type": "XML",
    "invoice_situation": "Qualquer"
  }
}
```

## Compatibilidade

⚠️ **BREAKING CHANGE**: Esta versão não é compatível com o formato antigo de mensagens.

O Maestro deve enviar mensagens no novo formato para que o worker funcione corretamente.

## Logs e Monitoramento

O worker agora envia logs em tempo real para o Maestro, permitindo:
- Acompanhamento detalhado da execução
- Debugging facilitado
- Melhor visibilidade do status
- Identificação rápida de problemas

Logs são enviados em momentos chave:
- Início do job
- Informações de processamento
- Conclusão ou falha
- Erros e exceções
