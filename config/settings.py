#config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Define o caminho da raiz do projeto.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Credenciais e URLs (carregadas do .env) ---
LOGIN_URL = os.getenv("GMS_LOGIN_URL")
GMS_USER = os.getenv("GMS_USER")
GMS_PASSWORD = os.getenv("GMS_PASSWORD")

# --- Diretórios ---
LOGS_DIR = BASE_DIR / "logs"
DOWNLOADS_DIR = BASE_DIR / "downloads"
PENDING_DIR = DOWNLOADS_DIR / "pending"
PROCESSED_DIR = DOWNLOADS_DIR / "processed"
DESTINATION_DIR = Path(str(PROCESSED_DIR))

# --- Configurações do Navegador ---
DEFAULT_TIMEOUT = 30

# --- Arquivos de Configuração ---
SELECTORS_FILE = BASE_DIR / "config" / "selectors.yaml"

# --- Setup de Diretórios ---
def create_dirs():
    LOGS_DIR.mkdir(exist_ok=True)
    PENDING_DIR.mkdir(exist_ok=True)
    PROCESSED_DIR.mkdir(exist_ok=True)
    DESTINATION_DIR.mkdir(exist_ok=True)

create_dirs()