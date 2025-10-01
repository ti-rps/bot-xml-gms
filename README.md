# Bot-XML-GMS

![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)

`bot-xml-gms` é um projeto de automação robusto projetado para extrair arquivos XML de documentos fiscais (NF-e, NFC-e) de um sistema web GMS. A solução é encapsulada em uma API para facilitar a execução, o monitoramento e a integração com outros sistemas.

## ✨ Funcionalidades

* **API de Controle**: Uma API RESTful (criada com FastAPI) para iniciar e monitorar as execuções da automação.
* **Execução em Background**: As automações rodam como tarefas em segundo plano, permitindo que a API responda imediatamente.
* **Padrão Page Object Model (POM)**: A interação com o site é modular e fácil de manter.
* **Configuração Externalizada**: Credenciais, URLs e seletores de elementos são gerenciados fora do código-fonte (`.env`, `.yaml`).
* **Logging Detalhado**: Logs completos são gerados em console e em arquivos diários para fácil depuração.
* **Processamento de Arquivos**: O robô lida com o download, descompactação e organização dos arquivos XML em uma estrutura de pastas lógica (`ano/mês/período`).
* **Resumo da Execução**: Ao final do processo, um resumo em JSON é gerado com estatísticas sobre os documentos extraídos.

## 🏗️ Arquitetura

O sistema é dividido em duas partes principais:

1.  **Agente (Agent)**: Uma aplicação `FastAPI` que expõe endpoints para controlar o robô.
2.  **Executor (Executor)**: Um script `Selenium` que é invocado pelo agente para realizar a automação no navegador.

O fluxo de execução é o seguinte:
`Usuário/Sistema -> Requisição API -> Agente (agent.py) -> Inicia Subprocesso (main.py) -> Robô Selenium -> Interage com Sistema GMS -> Processa Arquivos`

## ⚙️ Pré-requisitos

* **Python 3.9** ou superior.
* **Google Chrome** instalado.
* Acesso ao sistema GMS.

## 🚀 Instalação e Configuração

1.  **Clone o repositório:**
    ```bash
    git clone https://seu-repositorio/bot-xml-gms.git
    cd bot-xml-gms
    ```

2.  **Crie e ative um ambiente virtual (Recomendado):**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux / macOS
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    Crie um arquivo chamado `.env` na raiz do projeto, copiando o exemplo de `.env.example`.

    `.env.example`:
    ```ini
    GMS_LOGIN_URL="[https://url.do.seu.sistema.gms/login](https://url.do.seu.sistema.gms/login)"
    GMS_USER="seu_usuario"
    GMS_PASSWORD="sua_senha"
    ```

    Preencha o arquivo `.env` com suas credenciais e a URL correta.

5.  **Configure os Seletores:**
    Abra o arquivo `config/selectors.yaml` e preencha com os seletores CSS ou XPath corretos para os elementos da interface do sistema GMS.

## ▶️ Como Usar

### 1. Iniciar o Agente da API

Com o ambiente virtual ativado, execute o seguinte comando na raiz do projeto:

```bash
uvicorn agent:app --reload
```

O servidor da API estará rodando em `http://127.0.0.1:8000`.

### 2. Acessar a Documentação da API

Acesse [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) no seu navegador para ver a documentação interativa da API (gerada automaticamente pelo FastAPI/Swagger).

### 3. Iniciar uma Execução

Envie uma requisição `POST` para o endpoint `/execute` com os parâmetros da automação no corpo da requisição.

**Exemplo usando `curl`:**
```bash
curl -X POST "[http://127.0.0.1:8000/execute](http://127.0.0.1:8000/execute)" -H "Content-Type: application/json" -d \
'{
  "parameters": {
    "headless": true,
    "stores": [1, 5, 10],
    "document_type": "55",
    "emitter": "1",
    "operation_type": "T",
    "file_type": "0",
    "invoice_situation": "T",
    "start_date": "01/10/2025",
    "end_date": "01/10/2025",
    "gms_user": "seu_usuario_api",
    "gms_password": "sua_senha_api",
    "gms_login_url": "[https://url.do.seu.sistema.gms/login](https://url.do.seu.sistema.gms/login)"
  }
}'
```

A resposta será um JSON com o `job_id` da execução:
```json
{
  "job_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
  "message": "Execução da automação iniciada."
}
```

### 4. Verificar o Status da Execução

Envie uma requisição `GET` para o endpoint `/status/{job_id}`, substituindo `{job_id}` pelo ID retornado no passo anterior.

**Exemplo usando `curl`:**
```bash
curl -X GET "[http://127.0.0.1:8000/status/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6](http://127.0.0.1:8000/status/a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6)"
```

A resposta mostrará o status atual (`pendente`, `rodando`, `concluído`, `falhou`), logs e o resumo final quando a execução terminar.

## 📂 Estrutura do Projeto

```
.  
├── agent.py              # Servidor da API (FastAPI) 
├── main.py               # Ponto de entrada para o robô de automação  
├── requirements.txt      # Dependências do projeto  
├── .env                  # Arquivo de variáveis de ambiente (local)  
├── config/  
│   ├── settings.py       # Configurações centrais e criação de pastas  
│   └── selectors.yaml    # Seletores de elementos da interface  
├── downloads/  
│   ├── pending/          # Pasta temporária para arquivos baixados  
│   └── processed/        # Destino final dos arquivos XML organizados  
├── logs/                 # Arquivos de log da execução  
└── src/  
    ├── automation/  
    │   ├── browser_handler.py  
    │   └── page_objects/ # Padrão Page Object Model  
    ├── core/  
    │   └── orchestrator.py # Orquestra o fluxo da automação  
    └── utils/  
        ├── data_handler.py  
        ├── exceptions.py  
        ├── file_handler.py  
        └── logger_config.py  
```