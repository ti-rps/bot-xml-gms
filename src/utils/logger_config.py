# src/utils/logger_config.py
import logging
from logging.handlers import TimedRotatingFileHandler
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
    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - [task_id=%(task_id)s] - [%(filename)s:%(lineno)d] - %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addFilter(TaskIdFilter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    if os.getenv('LOG_ENV') == 'development':
        log_dir = settings.LOGS_DIR
        log_filename = log_dir / f"bot_dev_{datetime.now().strftime('%Y-%m-%d')}.log"

        file_handler = TimedRotatingFileHandler(
            log_filename, when='D', interval=1, backupCount=30, encoding='utf-8'
        )
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
        
        root_logger.info("LOG_ENV=development detectado. Logs também serão salvos em arquivo.")

    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logging.info("Logger configurado com sucesso.")