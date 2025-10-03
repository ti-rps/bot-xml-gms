# tasks.py
import logging
import json
from celery import Celery
from src.core.bot_runner import BotRunner
from src.utils.logger_config import setup_logger, set_task_id

celery_app = Celery(
    'tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

setup_logger()
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='run_automation_task')
def run_automation_task(self, params: dict):
    set_task_id(self.request.id)

    summary = None
    try:
        logger.info(f"Iniciando automação...")
        bot_runner = BotRunner(params=params, task=self)
        summary = bot_runner.run()
        logger.info(f"Automação concluída.")
        
        if summary:
            logger.info(f"Resultado final da tarefa {self.request.id}: \n{json.dumps(summary, indent=2, ensure_ascii=False)}")

        return {
            "status": "concluído",
            "summary": summary
        }

    except Exception as exc:
        logger.critical(f"A automação falhou para a tarefa {self.request.id}: {exc}", exc_info=True)
        raise exc