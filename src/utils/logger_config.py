# src/utils/logger_config.py
import logging
from logging.handlers import TimedRotatingFileHandler 
from config import settings
from datetime import datetime

def setup_logger():
    log_dir = settings.LOGS_DIR
    
    log_filename = log_dir / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Evita adicionar handlers duplicados se a função for chamada mais de uma vez
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Formato do log
    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )

    # Handler para o console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # Handler para o arquivo com rotação
    file_handler = TimedRotatingFileHandler(
        log_filename, when='D', interval=1, backupCount=30, encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logging.info("Logger configurado com sucesso.")