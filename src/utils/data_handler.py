# src/utils/data_handler.py
import json
import yaml
import logging
from typing import List, Dict, Any
from config import settings
from src.utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

def read_json_file(file_path: str) -> List[Dict[str, Any]]:
    logger.info(f"Lendo arquivo JSON de: {file_path}")
    try:
        with open(file_path, mode='r', encoding='utf-8') as jsonfile:
            return json.load(jsonfile)
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado em: {file_path}")
    except json.JSONDecodeError:
        logger.error(f"Erro de sintaxe (formato inválido) no arquivo JSON: {file_path}")
    except Exception as e:
        logger.error(f"Erro inesperado ao ler o arquivo '{file_path}': {e}")
    return []

def load_yaml_file(file_path: str) -> Dict:
    logger.info(f"Carregando arquivo YAML de: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            if data is None:
                raise ValueError("Arquivo YAML está vazio ou inválido")
            return data
    except FileNotFoundError as e:
        logger.error(f"Arquivo YAML não encontrado em: {file_path}")
        raise ConfigurationError(f"Arquivo YAML não encontrado: {file_path}") from e
    except yaml.YAMLError as e:
        logger.error(f"Erro ao fazer o parse do arquivo YAML '{file_path}': {e}")
        raise ConfigurationError(f"Erro ao fazer parse do YAML: {e}") from e
    except ValueError as e:
        logger.error(f"Arquivo YAML inválido '{file_path}': {e}")
        raise ConfigurationError(f"Arquivo YAML inválido: {e}") from e
    except Exception as e:
        logger.error(f"Erro inesperado ao ler o arquivo '{file_path}': {e}")
        raise ConfigurationError(f"Erro ao ler arquivo '{file_path}': {e}") from e