# Bot-XML-GMS

Automação para download de arquivos XML, SPED e relatórios contábeis do sistema GMS.

## 🏛️ Arquitetura do Projeto

Este projeto foi estruturado para separar as responsabilidades em camadas, facilitando a manutenção, o teste e a escalabilidade da automação.

/BOT-XML-GMS  
|  
|-- 📂 config/  
|   |-- init.py  
|   |-- selectors.yaml        # Mapeamento de seletores CSS/XPath  
|   |-- settings.py           # Configurações gerais: URLs, paths, constantes  
|  
|-- 📂 logs/  
|   |-- bot.log               # Arquivo de log gerado pela execução  
|  
|-- 📂 downloads/  
|   |-- pending/              # Arquivos baixados que ainda não foram processados/movidos  
|   |-- processed/            # Arquivos já processados e organizados  
|  
|-- 📂 src/  
|   |-- init.py  
|   |  
|   |-- 📂 core/  
|   |   |-- init.py  
|   |   |-- orchestrator.py   # Orquestra o fluxo principal da automação  
|   |  
|   |-- 📂 automation/  
|   |   |-- init.py  
|   |   |-- browser_handler.py # Gerencia a instância do navegador (Selenium/Playwright)  
|   |   |-- 📂 page_objects/  
|   |       |-- init.py  
|   |       |-- base_page.py  
|   |       |-- login_page.py  
|   |       |-- home_page.py  
|   |       |-- export_page.py  
|   |  
|   |-- 📂 utils/  
|       |-- init.py  
|       |-- file_handler.py     # Funções para mover, renomear, verificar arquivos  
|       |-- logger_config.py    # Módulo para configurar o sistema de logging  
|       |-- data_handler.py     # Funções para ler dados de entrada (ex: lista de lojas de um CSV)  
|  
|-- main.py                     # Ponto de entrada da aplicação. Deve ser muito simples.  
|-- requirements.txt            # Dependências do projeto  
|-- .env                        # Credenciais e variáveis de ambiente (NUNCA versionar)  
|-- .gitignore  
|-- README.md                   # Este arquivo  

## 📄 Descrição dos Componentes

### `main.py` (Ponto de Entrada)
**Responsabilidade:** Apenas iniciar a aplicação.
**O que faz:**
- Carrega as variáveis de ambiente do `.env`.
- Configura o logger.
- Instancia e executa o `Orchestrator`.

### `src/` (Código Fonte)
A pasta `src` (source) centraliza todo o código da sua aplicação, mantendo a raiz do projeto limpa.

### `src/core/orchestrator.py`
**Responsabilidade:** O "cérebro" da automação. Define o fluxo de trabalho.
**O que faz:**
- Lê a lista de lojas que precisam ser processadas (usando o `data_handler`).
- Inicia um loop `for loja in lojas:`.
- Coordena as ações:
    - Chama o `browser_handler` para iniciar o navegador.
    - Executa o processo de login usando a `LoginPage`.
    - Navega para a página de exportação usando a `HomePage`.
    - Realiza o download dos arquivos usando a `ExportPage`.
    - Chama o `file_handler` para organizar os arquivos baixados.
- Controla o fluxo com `try/except` para lidar com erros de uma loja específica sem parar o robô inteiro.

### `src/automation/browser_handler.py`
**Responsabilidade:** Gerenciar o ciclo de vida do navegador.
**O que faz:**
- Inicia a instância do driver (Selenium, Playwright).
- Configura opções do navegador (headless, diretório de download, user-agent).
- Fornece o objeto `driver` para os page_objects.
- Fecha o navegador de forma segura no final.

### `src/automation/page_objects/`
**Responsabilidade:** Mapear páginas e seus elementos, e encapsular as interações.
**O que faz:** Cada classe (ex: `LoginPage`) representa uma página e contém métodos para interagir com ela (ex: `fazer_login(usuario, senha)`, `clicar_botao_entrar()`). Eles recebem o `driver` do `browser_handler`.

### `src/utils/`
- **`file_handler.py`**: Funções como `mover_para_pasta_da_loja`, `renomear_relatorio`, `verificar_download_concluido`.
- **`logger_config.py`**: Uma função `setup_logger()` que configura o formato, nível (INFO, DEBUG) e local do arquivo de log.
- **`data_handler.py`**: Funções para ler dados de entrada. É muito melhor ler a lista de lojas de um arquivo `.csv` ou `.xlsx` do que deixá-la "hardcoded" no código. Ex: `ler_lojas_de_csv()`.

## 🚀 Planejamento da Refatoração (Passo a Passo)

1.  **Estrutura**: Crie as pastas e arquivos vazios conforme a sugestão acima. Mova seus arquivos existentes para os novos locais.
2.  **Configuração**: Centralize todas as configurações em `config/settings.py` e os segredos (usuário, senha) em um arquivo `.env` (use a biblioteca `python-dotenv` para carregá-los).
3.  **Logging**: Implemente o `logger_config.py` e chame a função de setup no início do `main.py`. Substitua todos os `print()` por `logger.info()`, `logger.error()`, etc.
4.  **Browser Handler**: Crie a classe `BrowserHandler` para encapsular a lógica do Selenium/Playwright. O `Orchestrator` irá instanciar esta classe.
5.  **Orchestrator**: Mova a lógica principal do seu script atual para o `Orchestrator`. Ele não deve mais conter código de Selenium diretamente, apenas chamadas para os page_objects.
6.  **Handlers (Utils)**: Isole as funções de manipulação de arquivos e de leitura de dados nos seus respectivos handlers na pasta `utils`.

Essa abordagem deixará seu projeto muito mais profissional, fácil de depurar (com logs detalhados), de dar manutenção (se um seletor mudar, você só mexe no `selectors.yaml`) e de estender no futuro.

O que acha desta proposta? Podemos começar a detalhar o código de algum desses arquivos se quiser!