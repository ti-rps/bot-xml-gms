# src/core/orchestrator.py
import logging
from src.automation.browser_handler import BrowserHandler
from src.utils import data_handler
from config import settings
from src.automation.page_objects.login_page import LoginPage

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser_handler = None
        self.stores_to_process = []
    def setup(self):
        logger.info("Preparando ambiente para a execução...")
        self.stores_to_process = data_handler.read_json_file(settings.STORES_DATA_FILE)
        if not self.stores_to_process:
            logger.warning("Nenhuma loja encontrada para processar.")
            return False
        
        self.selectors = data_handler.load_yaml_file(settings.SELECTORS_FILE)
        if not self.selectors:
            logger.error("Falha ao carregar seletores. A automação não pode continuar.")
            return False
        
        return True
    
    def run(self):
        """
        Executa o fluxo principal da automação.
        """
        logger.info("🚀 --- INICIANDO AUTOMAÇÃO BOT-XML-GMS --- 🚀")
        
        if not self.setup():
            logger.info("🏁 --- AUTOMAÇÃO FINALIZADA DEVIDO A FALHA NO SETUP --- 🏁")
            return

        self.browser_handler = BrowserHandler(headless=self.headless)
        
        try:
            driver = self.browser_handler.start_browser()
            if not driver:
                raise ConnectionError("Driver do navegador não foi inicializado.")

            # --- ETAPA DE LOGIN ---
            logger.info("Iniciando processo de login...")
            login_page_selectors = self.selectors.get('login_page', {})
            
            login_page = LoginPage(driver, login_page_selectors)
            login_page.navigate_to_login_page()
            login_page.execute_login(settings.GMS_USER, settings.GMS_PASSWORD)
            
            logger.info("Login realizado com sucesso!")

            # --- ETAPAS FUTURAS ---
            
        except Exception as e:
            logger.critical(f"Ocorreu um erro fatal na orquestração: {e}", exc_info=True)
        finally:
            if self.browser_handler:
                self.browser_handler.close_browser()
            logger.info("🏁 --- AUTOMAÇÃO FINALIZADA --- 🏁")