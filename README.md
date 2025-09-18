# Bot-XML-GMS

Automação para download de arquivos XML, SPED e relatórios contábeis do sistema GMS.

## 🏛️ Arquitetura do Projeto

Este projeto foi estruturado para separar as responsabilidades em camadas, facilitando a manutenção, o teste e a escalabilidade da automação.

/BOT-XML-GMS  
├── 📂 config/  
│   ├── __init__.py  
│   ├── selectors.yaml        # Mapeamento de seletores CSS/XPath  
│   └── settings.py           # Configurações gerais: URLs, paths, constantes  
│  
├── 📂 downloads/  
│   ├── 📂 pending/             # Arquivos baixados que ainda não foram processados/movidos  
│   └── 📂 processed/           # Arquivos já processados e organizados  
│  
├── 📂 logs/  
│   └── bot.log                 # Arquivo de log gerado pela execução  
│  
├── 📂 src/  
│   ├── __init__.py  
│   ├── 📂 core/  
│   │   ├── __init__.py  
│   │   └── orchestrator.py     # Orquestra o fluxo principal da automação  
│   │  
│   ├── 📂 automation/  
│   │   ├── __init__.py  
│   │   ├── browser_handler.py  # Gerencia a instância do navegador (Selenium/Playwright)  
│   │   └── 📂 page_objects/  
│   │       ├── __init__.py  
│   │       ├── base_page.py  
│   │       ├── login_page.py  
│   │       ├── home_page.py  
│   │       └── export_page.py  
│   │  
│   └── 📂 utils/  
│       ├── __init__.py  
│       ├── file_handler.py     # Funções para mover, renomear, verificar arquivos  
│       ├── logger_config.py    # Módulo para configurar o sistema de logging  
│       └── data_handler.py     # Funções para ler dados de entrada (ex: lista de lojas de um CSV)  
│  
├── .env                      # Credenciais e variáveis de ambiente (NUNCA versionar)  
├── .gitignore  
├── main.py                   # Ponto de entrada da aplicação. Deve ser muito simples.  
├── requirements.txt          # Dependências do projeto  
└── README.md                 # Este arquivo  

## 📄 Descrição dos Componentes

### `main.py` (Ponto de Entrada)
**Responsabilidade:** Apenas iniciar a aplicação.
**O que faz:**
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