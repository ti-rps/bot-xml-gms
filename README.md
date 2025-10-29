# Bot XML GMS - Automação de Extração de Dados

## 📋 Visão Geral

Bot XML GMS é uma aplicação de automação web que extrai dados de notas fiscais de um sistema de gestão (GMS). Utiliza Selenium para automação de browser e integra-se com RabbitMQ para processamento assíncrono de jobs.

**Status:** Em produção com melhorias implementadas (v1.1.0)

## 🏗️ Arquitetura

### Componentes Principais

```
bot-xml-gms/
├── src/
│   ├── automation/         # Selenium Page Objects
│   │   ├── browser_handler.py      # Gerenciador do WebDriver
│   │   └── page_objects/           # Page Object Model
│   │       ├── base_page.py        # Classe base
│   │       ├── login_page.py       # Login automático
│   │       ├── home_page.py        # Navegação
│   │       └── export_page.py      # Exportação de dados
│   ├── core/
│   │   └── bot_runner.py           # Orquestrador principal
│   └── utils/
│       ├── data_handler.py         # YAML, file handling
│       ├── exceptions.py           # Custom exceptions
│       ├── file_handler.py         # ZIP, file organization
│       └── logger_config.py        # Logging com TaskIdFilter
├── config/
│   ├── settings.py                 # Pydantic settings
│   └── selectors.yaml              # Seletores CSS/XPath
├── worker.py                       # RabbitMQ consumer
└── main.py                         # API HTTP
```

### Fluxo de Execução

```
[Maestro] --HTTP--> [main.py] --push--> [RabbitMQ]
   ↓                                        ↓
 Monitora            [worker.py] <-- consumes
 logs/status              ↓
   ↑              [BotRunner.run()] 
   |              ├─ setup()
   └─ callback    ├─ login
                  ├─ export_data
                  ├─ download
                  └─ process_files
```

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.9+
- Docker & Docker Compose
- Chrome/Chromium instalado

### Instalação

```bash
# Clone o repositório
git clone <repo-url>
cd bot-xml-gms

# Configure o ambiente
cp .env.example .env
# Edite .env com suas credenciais

# Instale dependências
pip install -r requirements.txt

# Inicie os serviços
docker-compose up -d

# Rode os testes (se houver)
pytest tests/
```

### Executar Localmente

```bash
# Terminal 1: Worker RabbitMQ
python worker.py

# Terminal 2: API HTTP
python main.py
```

## ⚙️ Configuração

### Variáveis de Ambiente

Veja `.env.example` para todas as variáveis disponíveis:

```env
# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# GMS Credentials
GMS_LOGIN_URL=https://gms.example.com/login
GMS_USER=seu_usuario
GMS_PASSWORD=sua_senha

# Maestro Callback
MAESTRO_API_URL=http://maestro-api:8000
MAESTRO_LOG_ENDPOINT=/api/logs

# Selectors
SELECTORS_FILE=config/selectors.yaml

# Database
DATABASE_URL=postgresql://user:pass@db:5432/bot_xml_gms
```

### Seletores CSS/XPath

Edite `config/selectors.yaml` com os seletores específicos do seu sistema GMS:

```yaml
login_page:
  username_field: "#user-input"
  password_field: "#password-input"
  login_button: "button[type='submit']"

home_page:
  sidebar_export: "a[href='/export']"
  sidebar_tax: "span.tax-module"

export_page:
  document_type_select: "select#document-type"
  start_date_input: "input#start-date"
  end_date_input: "input#end-date"
  export_button: "button.export-submit"
  download_link: "a.download-zip"
```

## 📊 Melhorias Implementadas (v1.1.0)

### FASE 1: Rastreabilidade
- ✅ **set_task_id()** - Task ID agora settável em logs para melhor rastreamento de jobs

### FASE 2: Segurança & Configuração
- ✅ **URL Security** - URLs não são mais completamente expostas nos logs (domínio apenas)
- ✅ **Configuration Validations** - Validação de `gms_login_url`, `SELECTORS_FILE`, stores no init
- ✅ **Timeout Centralization** - Removidos hardcoded `timeout=3` em favor de `settings.DEFAULT_TIMEOUT`
- ✅ **.env.example** - Todas as variáveis de ambiente documentadas

### FASE 3: Documentação & Observabilidade
- ✅ **Docstrings** - Todas as funções principais com documentação Google format
- ✅ **Debug Logging** - 14 pontos estratégicos de logger.debug() para rastreamento detalhado
- ✅ **Error Handling** - Custom exceptions com mensagens claras

### FASE 4: Documentação de Projeto
- ✅ **README.md** - Documentação completa (este arquivo)
- ✅ **CHANGELOG.md** - Histórico de mudanças versão 1.1.0

## 🔍 Logging

### Níveis de Log

```python
logger.debug()   # Informações detalhadas (job_id, parâmetros, progresso)
logger.info()    # Marcos importantes (login ok, exportação iniciada)
logger.warning() # Situações inesperadas (nenhuma fatura encontrada)
logger.error()   # Erros recuperáveis (falha em upload)
logger.critical() # Erros críticos (falha na automação)
```

### Task ID Filtering

Todos os logs incluem `task_id` quando settado:

```python
from src.utils.logger_config import set_task_id

# No início da execução
set_task_id(job_id)

# Logs subsequentes automaticamente incluem task_id
logger.info("Iniciando login")  # [job_id_123] Iniciando login
```

### Exemplo de Output

```
2025-10-28 14:30:45,123 [job_id_abc123] INFO: 🚀 --- INICIANDO AUTOMAÇÃO BOT-XML-GMS --- 🚀
2025-10-28 14:30:45,150 [job_id_abc123] DEBUG: Setup iniciado para job_id: abc123
2025-10-28 14:30:45,151 [job_id_abc123] DEBUG: Lojas a processar: ['LOJA_001', 'LOJA_002']
2025-10-28 14:30:45,200 [job_id_abc123] INFO: Preparando ambiente para a execução...
2025-10-28 14:30:50,300 [job_id_abc123] DEBUG: ✅ Driver do navegador iniciado com sucesso
2025-10-28 14:31:15,500 [job_id_abc123] INFO: ✅ Automação concluída com sucesso em 30.50s
```

## 📦 API Endpoints

### POST /api/jobs

Submete um novo job de extração:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123",
    "gms_user": "user@example.com",
    "gms_password": "senha",
    "document_type": "nota_fiscal",
    "stores": ["LOJA_001", "LOJA_002"],
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }'
```

### GET /api/jobs/{job_id}

Obtém status de um job:

```bash
curl http://localhost:8000/api/jobs/abc123
```

Resposta:
```json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "started_at": "2025-10-28T14:30:45Z",
  "completed_at": "2025-10-28T14:31:15Z",
  "duration_seconds": 30.5,
  "summary": {
    "files_processed": 45,
    "invoices_extracted": 1203,
    "total_value": "R$ 45.678,90"
  }
}
```

## 🐛 Troubleshooting

### Problema: "AttributeError: module 'config.settings' has no attribute 'SELECTORS_FILE'"

**Solução:** Certifique-se de importar a instância de Settings, não o módulo:
```python
# ✅ Correto
from config import settings

# ❌ Errado
from config import settings as config_settings  # se settings é um módulo
```

### Problema: Login falha com "Elemento não encontrado"

**Solução:** Verifique os seletores em `config/selectors.yaml`:
```bash
# Abra o GMS no Chrome e use DevTools
# Inspecione os elementos
# Atualize selectors.yaml com os seletores corretos
```

### Problema: Timeout na exportação

**Solução:** Aumentar timeout em `config/settings.py`:
```python
class Settings(BaseSettings):
    DEFAULT_TIMEOUT: int = 30  # segundos (aumento de 10)
```

## 📈 Métricas & Monitoring

### Arquivos de Log

- `logs/` - Logs estruturados com task_id
- `logs/error.log` - Erros críticos
- `logs/debug.log` - Informações detalhadas (apenas debug level)

### Arquivo de Status

Consultá o banco de dados PostgreSQL para histórico de jobs:

```sql
SELECT job_id, status, started_at, completed_at, duration_seconds
FROM jobs
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
```

## 🧪 Testes

```bash
# Rodar testes unitários
pytest tests/ -v

# Com coverage
pytest tests/ --cov=src

# Teste específico
pytest tests/test_login_page.py -v
```

## 🔒 Segurança

### Dados Sensíveis

- ❌ Senhas nunca são logadas
- ❌ URLs completas não aparecem em logs (apenas domínio)
- ✅ Credenciais vêm de variáveis de ambiente (.env)
- ✅ Seletores são versionados em Git (separados de dados)

### Best Practices

1. Não commite `.env` - sempre use `.env.example`
2. Renote credenciais regularmente
3. Use TLS/SSL para comunicação com Maestro
4. Monitore logs para tentativas de brute force

## 📝 Desenvolvimento

### Estrutura de Commits

Siga o padrão:
```
PHASE X.Y: Descrição breve da mudança

- Ponto 1 detalhado
- Ponto 2 detalhado
```

### Adicionando Novas Pages

1. Crie em `src/automation/page_objects/nova_page.py`
2. Herde de `BasePage`
3. Implemente métodos específicos
4. Adicione seletores a `config/selectors.yaml`
5. Integre em `bot_runner.py`

Exemplo:
```python
from src.automation.page_objects.base_page import BasePage

class NovaPage(BasePage):
    def fazer_algo(self):
        elemento = self.driver.find_element(By.CSS_SELECTOR, 
                                            self.selectors.get('elemento'))
        elemento.click()
```

## 📞 Suporte

Para questões ou problemas:

1. Verifique `README.md` e `CHANGELOG.md`
2. Consulte logs em `logs/` com task_id relevante
3. Abra issue no repositório com detalhes e logs

## 📄 Licença

Proprietary - Automações Bot XML GMS

## 🎯 Roadmap Futuro

- [ ] Suporte a múltiplos tipos de documentos
- [ ] Dashboard web em tempo real
- [ ] Retry automático com backoff exponencial
- [ ] Suporte a proxy HTTP
- [ ] Testes de carga (1000+ jobs/dia)
- [ ] Export de dados em formato Parquet

---

**Última atualização:** 2025-10-28  
**Versão:** 1.1.0  
**Maintainer:** Automações Team
