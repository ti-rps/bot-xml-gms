#config/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LOGS_DIR = BASE_DIR / "logs"
DOWNLOADS_DIR = BASE_DIR / "downloads"
PENDING_DIR = DOWNLOADS_DIR / "pending"
PROCESSED_DIR = DOWNLOADS_DIR / "processed"
DESTINATION_DIR = Path(str(PROCESSED_DIR))

DEFAULT_TIMEOUT = 30

SELECTORS_FILE = BASE_DIR / "config" / "selectors.yaml"

def create_dirs():
    LOGS_DIR.mkdir(exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DESTINATION_DIR.mkdir(exist_ok=True)

create_dirs()