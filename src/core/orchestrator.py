# src/core/orchestrator.py
import logging
from src.automation.browser_handler import BrowserHandler
from src.utils import data_handler
from config import settings
from src.automation.page_objects.login_page import LoginPage
from src.automation.page_objects.home_page import HomePage
from src.automation.page_objects.export_page import ExportPage

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, params: dict):
        self.headless = params.get('headless', True)
        self.stores_to_process = params.get('lojas', [])
        self.data_inicial = params.get('data_inicial')
        self.data_final = params.get('data_final')
        # Mais parâmetros podem ser adicionados conforme necessário
        self.browser_handler = None
        self.selectors = None
    
    def setup(self):
        logger.info("Preparando ambiente para a execução...")
        
        if not self.stores_to_process:
            logger.warning("Nenhuma loja fornecida nos parâmetros para processar.")
            return False
        
        self.selectors = data_handler.load_yaml_file(settings.SELECTORS_FILE)
        if not self.selectors:
            logger.error("Falha ao carregar seletores. A automação não pode continuar.")
            return False
        
        return True
    
    def run(self):
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

            logger.info("Navegando na página inicial...")
            home_page_selectors = self.selectors.get('home_page', {})

            home_page = HomePage(driver, home_page_selectors)
            home_page.navigate_sidebar_export()

            logger.info("Iniciando processo de exportação...")
            export_page_selectors = self.selectors.get('export_page', {})   

            export_page = ExportPage(driver, export_page_selectors)
            export_page.export_data()
            
        except Exception as e:
            logger.critical(f"Ocorreu um erro fatal na orquestração: {e}", exc_info=True)
            raise
        finally:
            if self.browser_handler:
                self.browser_handler.close_browser()
            logger.info("🏁 --- AUTOMAÇÃO FINALIZADA --- 🏁")