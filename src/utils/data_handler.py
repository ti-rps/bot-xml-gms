# src/utils/data_handler.py
import json
import logging
from typing import List, Dict
from config import settings

logger = logging.getLogger(__name__)

def read_stores_from_json() -> List[Dict[str, str]]:
    try:
        with open(settings.STORES_DATA_FILE, mode='r', encoding='utf-8') as jsonfile:
            stores = json.load(jsonfile)
        logger.info(f"{len(stores)} lojas carregadas do arquivo {settings.STORES_DATA_FILE}")
        return stores
    except FileNotFoundError:
        logger.error(f"Arquivo de lojas não encontrado em: {settings.STORES_DATA_FILE}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Erro de sintaxe no arquivo JSON: {settings.STORES_DATA_FILE}")
        return []
    except Exception as e:
        logger.error(f"Erro ao ler o arquivo de lojas: {e}")
        return []