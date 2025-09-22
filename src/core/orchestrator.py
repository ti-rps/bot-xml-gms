# src/core/orchestrator.py
import logging
from src.automation.browser_handler import BrowserHandler
from src.utils import data_handler
from config import settings
from src.automation.page_objects.login_page import LoginPage
from src.automation.page_objects.home_page import HomePage
from src.automation.page_objects.export_page import ExportPage
from src.utils.exceptions import AutomationException

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, params: dict):
        self.headless = params.get('headless', True)
        self.stores_to_process = params.get('stores', [])
        self.document_type = params.get('document_type')
        self.emitter = params.get('emitter')
        self.operation_type = params.get('operation_type')
        self.file_type = params.get('file_type')
        self.invoice_situation = params.get('invoice_situation')
        self.start_date = params.get('start_date')
        self.end_date = params.get('end_date')
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
            export_page.export_data(self.document_type, self.emitter, self.operation_type, self.file_type, self.invoice_situation, self.start_date, self.end_date, self.stores_to_process)
            
        except AutomationException as e:
            error_message = f"ERRO DE PROCESSO: {e}"
            logger.error(error_message)
            raise
        except Exception as e:
            error_message = f"ERRO INESPERADO: Ocorreu uma falha crítica na orquestração."
            logger.critical(error_message, exc_info=True)
            raise
        finally:
            if self.browser_handler:
                self.browser_handler.close_browser()
            logger.info("🏁 --- AUTOMAÇÃO FINALIZADA --- 🏁")