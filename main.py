# main.py
import logging
import sys
import argparse
import json
from src.core.orchestrator import Orchestrator
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

def main():
    setup_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('--params-file', required=True, help='Caminho para o arquivo JSON de parâmetros.')
    args = parser.parse_args()

    execution_params = load_execution_parameters(args.params_file)
    if not execution_params:
        sys.exit(1)

    try:
        orchestrator = Orchestrator(params=execution_params)
        orchestrator.run()
    except Exception as e:
        logging.critical(f"Erro inesperado na execução principal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()