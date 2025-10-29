# src/utils/logger_config.py
import logging
import logging.handlers
from config import settings
from datetime import datetime
import os
from threading import local

_thread_locals = local()

class TaskIdFilter(logging.Filter):
    def filter(self, record):
        record.task_id = getattr(_thread_locals, 'task_id', 'main_process')
        return True

def set_task_id(task_id):
    _thread_locals.task_id = task_id

def setup_logger():
    """Configura o logging para o projeto.
    
    Define handlers para console e arquivo (apenas em ambiente de desenvolvimento).
    Filtra logs de bibliotecas externas (Selenium, urllib3).
    
    Variáveis de ambiente:
        - LOG_ENV: 'development' para ativar logging em arquivo
        - LOG_LEVEL: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - [task_id=%(task_id)s] - [%(filename)s:%(lineno)d] - %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addFilter(TaskIdFilter())

    # Handler para console (sempre ativo)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # Handler para arquivo (apenas em desenvolvimento)
    log_env = os.getenv('LOG_ENV', '').strip().lower()
    if log_env == 'development':
        try:
            log_dir = settings.LOGS_DIR
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Usar arquivo único com rotação, não diário
            log_filename = log_dir / "bot_dev.log"

            file_handler = logging.handlers.RotatingFileHandler(
                log_filename, 
                maxBytes=int(os.getenv('LOG_MAX_BYTES', '10485760')),  # 10MB padrão
                backupCount=int(os.getenv('LOG_BACKUP_COUNT', '5')),
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(log_format)
            root_logger.addHandler(file_handler)
            
            root_logger.info("✅ LOG_ENV=development - Logs também salvos em: bot_dev.log")
        except Exception as e:
            root_logger.warning(f"⚠️  Falha ao configurar file handler: {e}")

    # Suprimir logs verbosos de bibliotecas externas
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)
    
    root_logger.info(f"✅ Logger configurado com sucesso. Level: {log_level}")