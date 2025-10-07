# Bot-XML-GMS

`bot-xml-gms` é um projeto de automação projetado para extrair arquivos XML de documentos fiscais (NF-e, NFC-e) do sistema web contábil do Grupo Maria Selma (GMS) ```https://cp10307.retaguarda.grupoboticario.com.br/```. A solução é encapsulada em uma API moderna e escalável para facilitar a execução, o monitoramento e a integração com outros sistemas.

## ✨ Funcionalidades

  * **API de Controle Robusta**: Uma API RESTful (criada com FastAPI) para enfileirar, monitorar, cancelar e obter logs das tarefas de automação.
  * **Execução Assíncrona e Escalável**: As automações rodam como tarefas em background com Celery e Redis, permitindo que a API responda imediatamente e que múltiplos workers possam processar tarefas em paralelo.
  * **Padrão Page Object Model (POM)**: A interação com o site é modular, reutilizável e fácil de manter, desacoplando a lógica de automação da estrutura das páginas web.
  * **Configuração Externalizada**: Credenciais, URLs e seletores de elementos são gerenciados fora do código-fonte (`.env`, `.yaml`), permitindo fácil adaptação a diferentes ambientes sem alterar o código.
  * **Containerização Completa**: O ambiente inteiro (API, Worker, Redis) é gerenciado com Docker e Docker Compose, garantindo consistência e facilitando o deploy.
  * **Logging Detalhado por Tarefa**: Logs completos são gerados com um `task_id` associado, permitindo rastrear a execução de cada requisição de forma isolada.
  * **Processamento Inteligente de Arquivos**: O robô lida com o download, descompactação de arquivos ZIP aninhados e organização dos XMLs em uma estrutura de pastas lógica (`ano/mês/período`).
  * **Resumo da Execução**: Ao final do processo, um resumo em JSON é gerado com estatísticas detalhadas sobre os documentos extraídos.

## 🏗️ Arquitetura

O sistema é arquitetado em um modelo de microserviços desacoplado, ideal para tarefas de longa duração:

1.  **API (`api`)**: O ponto de entrada do sistema. Uma aplicação FastAPI que recebe as requisições, valida os parâmetros e enfileira a tarefa de automação.
2.  **Broker (`redis`)**: Um servidor Redis que atua como intermediário (message broker), gerenciando a fila de tarefas a serem processadas.
3.  **Worker (`worker`)**: Um processo Celery que consome as tarefas da fila do Redis e as executa. É o worker que efetivamente instancia o robô Selenium para realizar a automação no navegador.

O fluxo de execução é o seguinte:
`Cliente -> POST /execute -> API (FastAPI) -> Enfileira Tarefa (Redis) -> Worker (Celery) -> Robô Selenium -> Interage com Sistema GMS -> Processa Arquivos -> Salva Resultado`

## ⚙️ Pré-requisitos

  * **Docker** e **Docker Compose**.
  * Acesso e credenciais para o sistema GMS.

## 🚀 Instalação e Configuração

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/EnzzoHosaki/bot-xml-gms.git
    cd bot-xml-gms
    ```

2.  **Configure as variáveis de ambiente:**
    Crie um arquivo chamado `.env` na raiz do projeto. Você pode copiar o conteúdo abaixo como ponto de partida.

    **Arquivo `.env`:**

    ```ini
    GMS_USER="seu_usuario"
    GMS_PASSWORD="sua_senha"
    ```

    *Observação: As credenciais também podem ser enviadas diretamente no corpo da requisição da API, o que sobrescreverá os valores do `.env`.*

3.  **Configure os Seletores:**
    Se a interface do sistema GMS for customizada, ajuste os seletores CSS ou XPath no arquivo `config/selectors.yaml` para corresponder aos elementos da sua interface.

## ▶️ Como Usar

### 1\. Iniciar a Aplicação com Docker

Com o Docker em execução, inicie todos os serviços (API, Worker e Redis) com um único comando:

```bash
docker-compose up --build
```

O servidor da API estará disponível em `http://localhost:8000`.

### 2\. Acessar a Documentação da API

Acesse **[http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)** no seu navegador para ver a documentação interativa da API (Swagger UI), onde você pode testar os endpoints diretamente.

### 3\. Enfileirar uma Nova Extração

Envie uma requisição `POST` para o endpoint `/execute` com os parâmetros da automação no corpo da requisição.

**Exemplo usando `curl`:**

```bash
curl -X POST "http://localhost:8000/execute" -H "Content-Type: application/json" -d \
'{
  "headless": true,
  "stores": [101, 550, 105],
  "document_type": "NFE",
  "emitter": "PROPRIO",
  "operation_type": "TODAS",
  "file_type": "XML",
  "invoice_situation": "TODAS",
  "start_date": "01/10/2025",
  "end_date": "01/10/2025",
  "gms_login_url": "https://cp10307.retaguarda.grupoboticario.com.br/app/#/login",
  "gms_user": "usuario_opcional_api",
  "gms_password": "senha_opcional_api"
}'
```

A resposta será um JSON com o `task_id` da execução, que você usará para monitorá-la:

```json
{
  "task_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
  "message": "Automação enfileirada para execução."
}
```

### 4\. Verificar o Status da Tarefa

Use os endpoints de status para acompanhar o progresso. Substitua `{task_id}` pelo ID retornado no passo anterior.

  * **Verificar o status geral:**

    ```bash
    curl -X GET "http://localhost:8000/status/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"
    ```

    A resposta mostrará o status (`PENDING`, `PROGRESS`, `SUCCESS`, `FAILURE`), informações sobre o progresso e o resumo final quando a execução terminar.

  * **Ver os logs completos:**

    ```bash
    curl -X GET "http://localhost:8000/logs/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"
    ```

  * **Acompanhar logs em tempo real (streaming):**

    ```bash
    curl -X GET "http://localhost:8000/logs/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6/stream"
    ```

## 📂 Estrutura do Projeto

```
.
├── api.py                  # Servidor da API (FastAPI)
├── tasks.py                # Definição das tarefas do Celery
├── main.py                 # Ponto de entrada para execução via linha de comando (CLI)
├── Dockerfile              # Instruções para construir a imagem da aplicação
├── docker-compose.yml      # Orquestração dos serviços para desenvolvimento
├── docker-compose.prod.yml # Orquestração dos serviços para produção
├── requirements.txt        # Dependências do projeto
├── .env                    # Arquivo de variáveis de ambiente (local)
├── config/
│   ├── settings.py         # Configurações centrais e criação de pastas
│   └── selectors.yaml      # Seletores de elementos da interface
├── downloads/
│   ├── pending/            # Pasta temporária para arquivos baixados
│   └── processed/          # Destino final dos arquivos XML organizados
├── logs/                   # Arquivos de log da execução
└── src/
    ├── automation/
    │   ├── browser_handler.py  # Gerencia a inicialização e configuração do Selenium
    │   └── page_objects/   # Classes do Padrão Page Object Model
    ├── core/
    │   └── bot_runner.py   # Orquestra o fluxo da automação
    └── utils/
        ├── data_handler.py     # Funções para ler arquivos de dados (JSON, YAML)
        ├── exceptions.py       # Exceções customizadas da aplicação
        ├── file_handler.py     # Lógica de processamento dos arquivos baixados
        └── logger_config.py    # Configuração do sistema de logging
```