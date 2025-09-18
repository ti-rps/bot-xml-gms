# src/core/orchestrator.py
import logging
from src.automation.browser_handler import BrowserHandler
from src.utils import data_handler

logger = logging.getLogger(__name__)

class Orchestrator:
    def run(self):
        logger.info("🚀 --- INICIANDO AUTOMAÇÃO BOT-XML-GMS --- 🚀")
        
        stores_to_process = data_handler.read_stores_from_csv()
        if not stores_to_process:
            logger.warning("Nenhuma loja para processar. Encerrando.")
            return

        browser_handler = BrowserHandler(headless=True) 
        
        try:
            driver = browser_handler.start_browser()

            # --- ETAPA DE LOGIN ---

            # --- LOOP PRINCIPAL ---
            for store in stores_to_process:
                store_name = store.get('nome_loja', 'N/A')
                logger.info(f"--- Processando loja: {store_name} ---")
                
                try:
                    # Aqui falta implementar ainda a lógica específica para cada loja
                    logger.info(f"✅ Loja {store_name} processada com sucesso.")

                except Exception as e:
                    logger.error(f"❌ Erro ao processar a loja {store_name}: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.critical(f"Ocorreu um erro fatal na orquestração: {e}", exc_info=True)
        finally:
            browser_handler.close_browser()
            logger.info("🏁 --- AUTOMAÇÃO FINALIZADA --- 🏁")