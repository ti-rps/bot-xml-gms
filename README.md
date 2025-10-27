# 🤖 Bot XML GMS - Worker# Bot-XML-GMS



Worker para automação de download e processamento de documentos fiscais eletrônicos (NF-e/NFC-e) do portal GMS, controlado pelo **RPS Maestro** via RabbitMQ.`bot-xml-gms` é um projeto de automação projetado para extrair arquivos XML de documentos fiscais (NF-e, NFC-e) do sistema web contábil do Grupo Maria Selma (GMS) ```https://cp10307.retaguarda.grupoboticario.com.br/```. A solução é encapsulada em uma API moderna e escalável para facilitar a execução, o monitoramento e a integração com outros sistemas.



## 📋 Descrição## ✨ Funcionalidades



Este bot é um **worker "burro"** que:  * **API de Controle Robusta**: Uma API RESTful (criada com FastAPI) para enfileirar, monitorar, cancelar e obter logs das tarefas de automação.

- ✅ Escuta mensagens em uma fila RabbitMQ  * **Execução Assíncrona e Escalável**: As automações rodam como tarefas em background com Celery e Redis, permitindo que a API responda imediatamente e que múltiplos workers possam processar tarefas em paralelo.

- ✅ Executa tarefas de download conforme instruções recebidas  * **Padrão Page Object Model (POM)**: A interação com o site é modular, reutilizável e fácil de manter, desacoplando a lógica de automação da estrutura das páginas web.

- ✅ Reporta status de execução via HTTP para o Maestro  * **Configuração Externalizada**: Credenciais, URLs e seletores de elementos são gerenciados fora do código-fonte (`.env`, `.yaml`), permitindo fácil adaptação a diferentes ambientes sem alterar o código.

- ✅ Processa e organiza arquivos XML baixados  * **Containerização Completa**: O ambiente inteiro (API, Worker, Redis) é gerenciado com Docker e Docker Compose, garantindo consistência e facilitando o deploy.

  * **Logging Detalhado por Tarefa**: Logs completos são gerados com um `task_id` associado, permitindo rastrear a execução de cada requisição de forma isolada.

## 🏗️ Arquitetura  * **Processamento Inteligente de Arquivos**: O robô lida com o download, descompactação de arquivos ZIP aninhados e organização dos XMLs em uma estrutura de pastas lógica (`ano/mês/período`).

  * **Resumo da Execução**: Ao final do processo, um resumo em JSON é gerado com estatísticas detalhadas sobre os documentos extraídos.

```

┌─────────────────┐## 🏗️ Arquitetura

│  RPS Maestro    │ (Sistema principal em Go)

│   (Go API)      │O sistema é arquitetado em um modelo de microserviços desacoplado, ideal para tarefas de longa duração:

└────────┬────────┘

         │1.  **API (`api`)**: O ponto de entrada do sistema. Uma aplicação FastAPI que recebe as requisições, valida os parâmetros e enfileira a tarefa de automação.

         │ HTTP Status Reports2.  **Broker (`redis`)**: Um servidor Redis que atua como intermediário (message broker), gerenciando a fila de tarefas a serem processadas.

         ▼3.  **Worker (`worker`)**: Um processo Celery que consome as tarefas da fila do Redis e as executa. É o worker que efetivamente instancia o robô Selenium para realizar a automação no navegador.

    ┌────────┐

    │ Worker │◄──── RabbitMQ MessagesO fluxo de execução é o seguinte:

    └────────┘`Cliente -> POST /execute -> API (FastAPI) -> Enfileira Tarefa (Redis) -> Worker (Celery) -> Robô Selenium -> Interage com Sistema GMS -> Processa Arquivos -> Salva Resultado`

         │

         ▼## ⚙️ Pré-requisitos

    ┌────────┐

    │  GMS   │ (Portal Web)  * **Docker** e **Docker Compose**.

    └────────┘  * Acesso e credenciais para o sistema GMS.

```

## 🚀 Instalação e Configuração

## 🚀 Início Rápido

1.  **Clone o repositório:**

### Pré-requisitos

    ```bash

- Docker & Docker Compose    git clone https://github.com/EnzzoHosaki/bot-xml-gms.git

- Acesso ao RPS Maestro    cd bot-xml-gms

- Credenciais do portal GMS    ```



### Configuração2.  **Configure as variáveis de ambiente:**

    Crie um arquivo chamado `.env` na raiz do projeto. Você pode copiar o conteúdo abaixo como ponto de partida.

1. **Clone o repositório**

```bash    **Arquivo `.env`:**

git clone <repository-url>

cd bot-xml-gms    ```ini

```    GMS_USER="seu_usuario"

    GMS_PASSWORD="sua_senha"

2. **Configure as variáveis de ambiente**    ```



Edite o arquivo `.env`:    *Observação: As credenciais também podem ser enviadas diretamente no corpo da requisição da API, o que sobrescreverá os valores do `.env`.*



```bash3.  **Configure os Seletores:**

# Identificação do Worker    Se a interface do sistema GMS for customizada, ajuste os seletores CSS ou XPath no arquivo `config/selectors.yaml` para corresponder aos elementos da sua interface.

WORKER_ID=worker-gms-01

## ▶️ Como Usar

# Credenciais GMS

GMS_USER="seu_usuario"### 1\. Iniciar a Aplicação com Docker

GMS_PASSWORD="sua_senha"

Com o Docker em execução, inicie todos os serviços (API, Worker e Redis) com um único comando:

# RabbitMQ (apontar para o Maestro)

RABBITMQ_HOST=maestro-rabbitmq-host```bash

RABBITMQ_PORT=5672docker-compose up --build

RABBITMQ_USER=admin```

RABBITMQ_PASSWORD=admin123

RABBITMQ_QUEUE=bot-xml-tasksO servidor da API estará disponível em `http://localhost:8000`.



# Maestro API### 2\. Acessar a Documentação da API

MAESTRO_API_URL=http://maestro-host:8080

Acesse **[http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)** no seu navegador para ver a documentação interativa da API (Swagger UI), onde você pode testar os endpoints diretamente.

# Logging

LOG_LEVEL=INFO### 3\. Enfileirar uma Nova Extração

```

Envie uma requisição `POST` para o endpoint `/execute` com os parâmetros da automação no corpo da requisição.

3. **Inicie o worker**

**Exemplo usando `curl`:**

```bash

# Desenvolvimento (com RabbitMQ local)```bash

docker-compose up -dcurl -X POST "http://localhost:8000/execute" -H "Content-Type: application/json" -d \

'{

# Produção (conecta ao RabbitMQ do Maestro)  "headless": true,

docker-compose up -d worker  "stores": [101, 550, 105],

```  "document_type": "NFE",

  "emitter": "PROPRIO",

## 📨 Formato de Mensagens  "operation_type": "TODAS",

  "file_type": "XML",

O worker espera mensagens JSON na fila RabbitMQ com o seguinte formato:  "invoice_situation": "TODAS",

  "start_date": "01/10/2025",

```json  "end_date": "01/10/2025",

{  "gms_login_url": "https://cp10307.retaguarda.grupoboticario.com.br/app/#/login",

  "task_id": "uuid-da-tarefa",  "gms_user": "usuario_opcional_api",

  "stores": ["LOJA001", "LOJA002"],  "gms_password": "senha_opcional_api"

  "document_type": "NFE",}'

  "emitter": "Qualquer",```

  "operation_type": "Qualquer",

  "file_type": "XML",A resposta será um JSON com o `task_id` da execução, que você usará para monitorá-la:

  "invoice_situation": "Qualquer",

  "start_date": "01/01/2024",```json

  "end_date": "31/01/2024",{

  "gms_user": "usuario_opcional",  "task_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",

  "gms_password": "senha_opcional",  "message": "Automação enfileirada para execução."

  "gms_login_url": "https://portal.gms.com.br/login",}

  "headless": true```

}

```### 4\. Verificar o Status da Tarefa



### Campos ObrigatóriosUse os endpoints de status para acompanhar o progresso. Substitua `{task_id}` pelo ID retornado no passo anterior.



- `task_id`: ID único da tarefa  * **Verificar o status geral:**

- `stores`: Array com códigos das lojas

- `document_type`: Tipo do documento (`NFE` ou `NFCE`)    ```bash

- `start_date`: Data inicial (DD/MM/YYYY)    curl -X GET "http://localhost:8000/status/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"

- `end_date`: Data final (DD/MM/YYYY)    ```

- `gms_login_url`: URL de login do portal GMS

    A resposta mostrará o status (`PENDING`, `PROGRESS`, `SUCCESS`, `FAILURE`), informações sobre o progresso e o resumo final quando a execução terminar.

### Campos Opcionais

  * **Ver os logs completos:**

- `gms_user`: Usuário GMS (usa `.env` se não informado)

- `gms_password`: Senha GMS (usa `.env` se não informado)    ```bash

- `emitter`: Filtro de emitente (padrão: "Qualquer")    curl -X GET "http://localhost:8000/logs/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"

- `operation_type`: Tipo de operação (padrão: "Qualquer")    ```

- `file_type`: Tipo de arquivo (padrão: "XML")

- `invoice_situation`: Situação da nota (padrão: "Qualquer")  * **Acompanhar logs em tempo real (streaming):**

- `headless`: Executar em modo headless (padrão: true)

    ```bash

## 📊 Reportes de Status    curl -X GET "http://localhost:8000/logs/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6/stream"

    ```

O worker reporta status para o Maestro via HTTP POST em `/api/tasks/{task_id}/status`:

## 📂 Estrutura do Projeto

### Status: `started`

```json```

{.

  "task_id": "uuid",├── api.py                  # Servidor da API (FastAPI)

  "status": "started",├── tasks.py                # Definição das tarefas do Celery

  "timestamp": 1234567890,├── main.py                 # Ponto de entrada para execução via linha de comando (CLI)

  "worker_id": "worker-gms-01",├── Dockerfile              # Instruções para construir a imagem da aplicação

  "data": {├── docker-compose.yml      # Orquestração dos serviços para desenvolvimento

    "document_type": "NFE",├── docker-compose.prod.yml # Orquestração dos serviços para produção

    "start_date": "01/01/2024",├── requirements.txt        # Dependências do projeto

    "end_date": "31/01/2024",├── .env                    # Arquivo de variáveis de ambiente (local)

    "stores": ["LOJA001"]├── config/

  }│   ├── settings.py         # Configurações centrais e criação de pastas

}│   └── selectors.yaml      # Seletores de elementos da interface

```├── downloads/

│   ├── pending/            # Pasta temporária para arquivos baixados

### Status: `completed`│   └── processed/          # Destino final dos arquivos XML organizados

```json├── logs/                   # Arquivos de log da execução

{└── src/

  "task_id": "uuid",    ├── automation/

  "status": "completed",    │   ├── browser_handler.py  # Gerencia a inicialização e configuração do Selenium

  "timestamp": 1234567890,    │   └── page_objects/   # Classes do Padrão Page Object Model

  "worker_id": "worker-gms-01",    ├── core/

  "data": {    │   └── bot_runner.py   # Orquestra o fluxo da automação

    "status": "completed",    └── utils/

    "duration_seconds": 123.45,        ├── data_handler.py     # Funções para ler arquivos de dados (JSON, YAML)

    "summary": {        ├── exceptions.py       # Exceções customizadas da aplicação

      "total_xml_files_analyzed": 100,        ├── file_handler.py     # Lógica de processamento dos arquivos baixados

      "valid_invoices_found": 95        └── logger_config.py    # Configuração do sistema de logging

    }```
  }
}
```

### Status: `failed`
```json
{
  "task_id": "uuid",
  "status": "failed",
  "timestamp": 1234567890,
  "worker_id": "worker-gms-01",
  "data": {
    "status": "failed",
    "error": "Mensagem de erro",
    "error_type": "AutomationException"
  }
}
```

## 📂 Estrutura de Diretórios

```
bot-xml-gms/
├── worker.py              # Ponto de entrada do worker
├── config/
│   ├── settings.py        # Configurações (Pydantic)
│   └── selectors.yaml     # Seletores CSS/XPath
├── src/
│   ├── core/
│   │   └── bot_runner.py  # Lógica principal da automação
│   ├── automation/
│   │   ├── browser_handler.py
│   │   └── page_objects/  # Page Objects para Selenium
│   └── utils/
│       ├── file_handler.py
│       ├── data_handler.py
│       └── exceptions.py
├── downloads/
│   ├── pending/           # Arquivos temporários
│   └── processed/         # Arquivos organizados
└── logs/                  # Logs de execução
```

## 🐳 Docker

### Build da Imagem

```bash
docker build -t bot-xml-gms:latest .
```

### Variáveis de Ambiente

Todas as configurações podem ser passadas via variáveis de ambiente:

```bash
docker run -d \
  -e WORKER_ID=worker-01 \
  -e RABBITMQ_HOST=rabbitmq \
  -e MAESTRO_API_URL=http://maestro:8080 \
  -e GMS_USER=usuario \
  -e GMS_PASSWORD=senha \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  bot-xml-gms:latest
```

## 📝 Logs

Os logs são salvos em:
- Console (stdout): Todos os níveis configurados
- Arquivo: `logs/bot.log` (rotacionado automaticamente)

Níveis de log:
- `DEBUG`: Detalhes completos da execução
- `INFO`: Informações gerais (padrão)
- `WARNING`: Avisos
- `ERROR`: Erros recuperáveis
- `CRITICAL`: Erros fatais

## 🔧 Desenvolvimento

### Executar Localmente

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar worker
python worker.py
```

## 🛠️ Tecnologias

- **Python 3.9+**: Linguagem principal
- **Selenium**: Automação web
- **Pika**: Cliente RabbitMQ
- **Requests**: Cliente HTTP
- **Pydantic**: Validação de configurações
- **Docker**: Containerização

## 📊 Monitoramento

### RabbitMQ Management UI

Acesse `http://localhost:15672` para monitorar:
- Mensagens na fila
- Conexões ativas
- Taxa de consumo

**Credenciais:** admin/admin123

### Logs do Worker

```bash
# Ver logs em tempo real
docker-compose logs -f worker

# Últimas 100 linhas
docker-compose logs --tail=100 worker
```

## 🔒 Segurança

- ⚠️ **Nunca commite** o arquivo `.env` com credenciais reais
- ✅ Use secrets management em produção (Docker Secrets, Vault, etc.)
- ✅ Rode o worker em rede privada isolada
- ✅ Use TLS para comunicação com RabbitMQ e Maestro

## 🤝 Integração com RPS Maestro

O RPS Maestro (sistema em Go) é responsável por:
- 📋 Gerenciar a fila de tarefas
- 📊 Coordenar múltiplos workers
- 📈 Agregar estatísticas
- 🔔 Notificar usuários
- 💾 Persistir resultados

Este worker é um **componente passivo** que apenas:
- 👂 Escuta comandos
- ⚙️ Executa tarefas
- 📣 Reporta status

## 📞 Troubleshooting

### Worker não conecta ao RabbitMQ

```bash
# Verificar conectividade
docker exec bot-xml-worker ping rabbitmq

# Verificar logs
docker-compose logs rabbitmq
```

### Timeout no download

Ajuste os timeouts no `.env`:
```bash
DOWNLOAD_TIMEOUT=600  # 10 minutos
PAGE_LOAD_TIMEOUT=60
```

### Erro de credenciais GMS

Verifique no `.env`:
```bash
GMS_USER="usuario_correto"
GMS_PASSWORD="senha_correta"
```

## 📄 Licença

Proprietário - RPS

## 👥 Autores

RPS - Robotic Process Solutions

---

**Nota:** Este é um worker controlado pelo RPS Maestro. Para informações sobre a API principal, consulte a documentação do Maestro.
