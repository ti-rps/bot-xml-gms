# Correções Recomendadas - Bot XML GMS

## 🔴 CRÍTICO: Setar task_id para Logging Correto

### Problema
O `task_id` é declarado em `logger_config.py` mas nunca é setado durante a execução, fazendo com que todos os logs apareçam com `task_id=main_process`.

### Solução

**Arquivo:** `src/core/bot_runner.py`

```python
def setup(self):
    from src.utils.logger_config import set_task_id
    
    self._update_status("Preparando ambiente para a execução...", 5)
    
    # ✨ ADIÇÃO: Setar task_id se job_id for fornecido
    if self.job_id:
        set_task_id(self.job_id)
    
    if not self.stores_to_process:
        logger.warning("Nenhuma loja fornecida nos parâmetros para processar.")
        return False
    
    self.selectors = data_handler.load_yaml_file(config_settings.SELECTORS_FILE)
    if not self.selectors:
        logger.error("Falha ao carregar seletores. A automação não pode continuar.")
        return False
    
    return True
```

---

## 🟠 IMPORTANTE: Não Logar URLs com Dados Sensíveis

### Problema
URLs de login são logadas inteiras, expondo potencialmente dados sensíveis.

### Solução

**Arquivo:** `src/automation/page_objects/login_page.py`

```python
def navigate_to_login_page(self, login_url):
    # ✨ MUDANÇA: Log apenas o domínio, não a URL completa
    try:
        from urllib.parse import urlparse
        domain = urlparse(login_url).netloc
        logger.info(f"Navegando para página de login em: {domain}")
    except:
        logger.info("Navegando para página de login...")
    
    self.driver.get(login_url)
```

---

## 🟠 IMPORTANTE: Adicionar Validação de Configurações

### Problema
Se `selectors.yaml` não existir, o erro só ocorre durante `setup()`, não oferecendo feedback claro no início.

### Solução

**Arquivo:** `src/core/bot_runner.py` - Adicionar validações ao `__init__`

```python
def __init__(self, params: dict, job_id: str = None, log_callback: Callable = None):
    self.headless = params.get('headless', True)
    self.stores_to_process = params.get('stores', [])
    self.document_type = params.get('document_type')
    self.emitter = params.get('emitter')
    self.operation_type = params.get('operation_type')
    self.file_type = params.get('file_type')
    self.invoice_situation = params.get('invoice_situation')
    self.start_date = params.get('start_date')
    self.end_date = params.get('end_date')
    self.gms_user = params.get('gms_user')
    self.gms_password = params.get('gms_password')
    
    self.job_id = job_id
    self.log_callback = log_callback
    
    if not self.gms_user:
        self.gms_user = os.getenv('GMS_USER') or config_settings.gms_username
    if not self.gms_password:
        self.gms_password = os.getenv('GMS_PASSWORD') or config_settings.gms_password
        
    self.gms_login_url = params.get('gms_login_url')
    self.browser_handler = None
    self.selectors = None
    
    self.status = "idle"
    self.progress = 0
    self.current_message = ""
    
    # ✨ ADIÇÃO: Validações críticas
    if not self.gms_user or not self.gms_password:
        raise ValueError("Credenciais GMS_USER e GMS_PASSWORD não foram encontradas nem nos parâmetros da API nem nas variáveis de ambiente.")
    
    if not self.gms_login_url:
        raise ValueError("Parâmetro obrigatório 'gms_login_url' não fornecido.")
    
    if not config_settings.SELECTORS_FILE.exists():
        raise FileNotFoundError(f"Arquivo de seletores não encontrado em: {config_settings.SELECTORS_FILE}")
    
    if not self.stores_to_process:
        raise ValueError("Parâmetro obrigatório 'stores' não fornecido ou vazio.")
    
    logger.info(f"BotRunner inicializado com sucesso - Job ID: {job_id}")
```

---

## 🟠 IMPORTANTE: Remover Timeouts Hardcoded

### Problema
Timeouts são hardcoded em vários lugares em vez de usar configuração centralizada.

### Solução

**Arquivo:** `src/automation/page_objects/export_page.py`

**ANTES:**
```python
if self.is_element_present(self.selectors['alert_msg'], timeout=3):
```

**DEPOIS:**
```python
from config import settings
# ... no método:
if self.is_element_present(self.selectors['alert_msg'], timeout=settings.DEFAULT_TIMEOUT // 10):
```

---

## 🟡 Melhorar Tratamento de Erros em data_handler

### Problema
`data_handler.py` retorna dicionários vazios em erro, dificultando diagnóstico.

### Solução

**Arquivo:** `src/utils/data_handler.py`

```python
def load_yaml_file(file_path: str) -> Dict:
    from src.utils.exceptions import AutomationException
    
    logger.info(f"Carregando arquivo YAML de: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            if data is None:
                raise ValueError("Arquivo YAML está vazio")
            return data
    except FileNotFoundError:
        raise AutomationException(f"Arquivo YAML não encontrado: {file_path}")
    except yaml.YAMLError as e:
        raise AutomationException(f"Erro ao fazer parse do YAML: {e}")
    except Exception as e:
        raise AutomationException(f"Erro ao ler arquivo '{file_path}': {e}")
```

---

## 🟡 Adicionar .env.example

**Arquivo:** `.env.example`

```env
# Ambiente de execução
LOG_ENV=production

# Credenciais GMS (opcional - podem vir do orquestrador)
# GMS_USER=seu_usuario
# GMS_PASSWORD=sua_senha

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=automation_jobs

# Maestro API
MAESTRO_API_URL=http://localhost:8000

# Banco de Dados
MAESTRO_DB_HOST=postgres
MAESTRO_DB_PORT=5432
MAESTRO_DB_USER=user
MAESTRO_DB_PASSWORD=password
MAESTRO_DB_NAME=maestro_db
```

---

## 📋 Ordem de Implementação Recomendada

### Fase 1 (Hoje - Crítico)
1. Adicionar `set_task_id()` em `bot_runner.py` → `setup()`

### Fase 2 (Semana 1)
2. Adicionar validações em `__init__` de `BotRunner`
3. Não logar URLs sensíveis em `login_page.py`

### Fase 3 (Semana 2)
4. Melhorar `data_handler.py` para lançar exceções
5. Remover timeouts hardcoded em `export_page.py`
6. Criar `.env.example`

---

## ✅ Como Validar as Correções

### 1. Verificar task_id nos Logs
```bash
grep "task_id=" logs/bot_dev_*.log
# Esperado: task_id=<job_id> (não main_process)
```

### 2. Verificar Erros de Validação
```bash
# Tentar executar sem selectors.yaml
python main.py --params-file test.json
# Esperado: FileNotFoundError com mensagem clara
```

### 3. Verificar Logs Sensíveis
```bash
grep -i "https://" logs/bot_dev_*.log
# Esperado: Nenhuma URL sensível, apenas domínios
```

---

**Status:** Recomendado para implementação imediata  
**Prioridade:** 🔴 CRÍTICO > 🟠 IMPORTANTE > 🟡 MODERADO
