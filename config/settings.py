from pathlib import Path

# Define o caminho da raiz do projeto.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- URLs ---
LOGIN_URL = "https://url.do.sistema.gms/login"

# --- Diretórios ---
LOGS_DIR = BASE_DIR / "logs"
DOWNLOADS_DIR = BASE_DIR / "downloads"
PENDING_DIR = DOWNLOADS_DIR / "pending"
PROCESSED_DIR = DOWNLOADS_DIR / "processed"

# --- Arquivos de Configuração ---
SELECTORS_FILE = BASE_DIR / "config" / "selectors.yaml"
STORES_DATA_FILE = BASE_DIR / "lojas.csv"

# --- Configurações do Robô ---
# Tempo máximo em segundos que o Selenium vai esperar por um elemento aparecer
DEFAULT_TIMEOUT = 30

# Criar os diretórios se eles não existirem
LOGS_DIR.mkdir(exist_ok=True)
PENDING_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)