import logging
import sys
import argparse
import json
import signal
from src.core.bot_runner import BotRunner
from src.utils.logger_config import setup_logger

def load_execution_parameters(params_file_path):
    try:
        with open(params_file_path, 'r', encoding='utf-8') as f:
            params = json.load(f)
        logging.info(f"Parâmetros de execução carregados com sucesso de {params_file_path}")
        return params
    except Exception as e:
        logging.critical(f"Não foi possível ler o arquivo de parâmetros: {e}", exc_info=True)
        return None

def handle_termination(sig, frame):
    logging.warning("🔴 PROCESSO DE AUTOMAÇÃO INTERROMPIDO EXTERNAMENTE (CANCELADO). ENCERRANDO... 🔴")
    sys.exit(1)

def main():
    setup_logger()

    signal.signal(signal.SIGTERM, handle_termination)

    parser = argparse.ArgumentParser()
    parser.add_argument('--params-file', required=True, help='Caminho para o arquivo JSON de parâmetros.')
    args = parser.parse_args()

    execution_params = load_execution_parameters(args.params_file)
    if not execution_params:
        sys.exit(1)

    summary = None
    try:
        bot_runner = BotRunner(params=execution_params)
        summary = bot_runner.run()
    except Exception as e:
        logging.critical(f"Erro inesperado na execução principal: {e}", exc_info=True)
        sys.exit(1)
    
    if summary:
        print("\n---SUMMARY_START---")
        print(json.dumps(summary, indent=4, ensure_ascii=False))
        print("---SUMMARY_END---")

if __name__ == "__main__":
    main()
