# src/utils/logger_config.py
import logging
from logging.handlers import TimedRotatingFileHandler 
from config import settings
from datetime import datetime

def setup_logger():
    log_dir = settings.LOGS_DIR
    
    # Define o nome do arquivo com a data
    log_filename = log_dir / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        handlers=[
            # when='D' para rotação diária, interval=1 para a cada 1 dia.
            # backupCount=30 para manter os logs dos últimos 30 dias.
            TimedRotatingFileHandler(log_filename, when='D', interval=1, backupCount=30, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logging.getLogger("selenium").setLevel(logging.WARNING)
    return logging.getLogger(__name__)