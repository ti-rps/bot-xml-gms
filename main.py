# main.py
import logging
from src.core.orchestrator import Orchestrator
from src.utils.logger_config import setup_logger

def main():
    setup_logger()
    try:
        orchestrator = Orchestrator()
        orchestrator.run()
    except Exception as e:
        logging.critical(f"Erro inesperado na execução principal: {e}", exc_info=True)

if __name__ == "__main__":
    main()