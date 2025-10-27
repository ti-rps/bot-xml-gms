# src/core/bot_runner.py
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Callable
from src.automation.browser_handler import BrowserHandler
from src.utils import data_handler
from config import settings
from src.automation.page_objects.login_page import LoginPage
from src.automation.page_objects.home_page import HomePage
from src.automation.page_objects.export_page import ExportPage
from src.utils import file_handler
from src.utils.exceptions import AutomationException, NoInvoicesFoundException

logger = logging.getLogger(__name__)

class BotRunner:
    # ATUALIZAÇÃO: Modificado __init__ para aceitar job_id e log_callback
    def __init__(self, params: dict, job_id: str = None, log_callback: Callable = None):
        self.headless = params.get('headless', True)
        self.stores_to_process = params.get('stores', [])
        self.document_type = params.get('document_type')
        self.emitter = params.get('emitter')
        self.operation_type = params.get('operation_type')
        self.file_type = params.get('file_type')
        self.invoice_situation = params.get('invoice_situation')
        self.start_date = params.get('start_date')
        self.end_date = params.get('end_date')
        self.gms_user = params.get('gms_user')
        self.gms_password = params.get('gms_password')
        
        # ATUALIZAÇÃO: Armazenar job_id e callback
        self.job_id = job_id
        self.log_callback = log_callback
        
        if not self.gms_user:
            self.gms_user = os.getenv('GMS_USER') or settings.gms_username
        if not self.gms_password:
            self.gms_password = os.getenv('GMS_PASSWORD') or settings.gms_password
            
        self.gms_login_url = params.get('gms_login_url')
        self.browser_handler = None
        self.selectors = None
        
        self.status = "idle"
        self.progress = 0
        self.current_message = ""
        
        if not self.gms_user or not self.gms_password:
            raise ValueError("Credenciais GMS_USER e GMS_PASSWORD não foram encontradas nem nos parâmetros da API nem nas variáveis de ambiente.")
        
    def _update_status(self, message: str, progress: int = None):
        """Atualiza status interno E envia log para o Maestro via callback"""
        self.current_message = message
        if progress is not None:
            self.progress = progress
        
        # Log local
        logger.info(message)
        
        # ATUALIZAÇÃO: Enviar log para o Maestro se o callback foi fornecido
        if self.log_callback and self.job_id:
            try:
                self.log_callback(self.job_id, "INFO", message)
            except Exception as e:
                # Não quebrar a automação se o log falhar
                logger.warning(f"Falha ao enviar log para o Maestro via callback: {e}")

    def setup(self):
        self._update_status("Preparando ambiente para a execução...", 5)
        
        if not self.stores_to_process:
            logger.warning("Nenhuma loja fornecida nos parâmetros para processar.")
            return False
        
        self.selectors = data_handler.load_yaml_file(settings.SELECTORS_FILE)
        if not self.selectors:
            logger.error("Falha ao carregar seletores. A automação não pode continuar.")
            return False
        
        return True
    
    def run(self) -> Dict:
        """
        Executa o fluxo completo de automação
        
        Returns:
            Dicionário com resultado da execução
        """
        logger.info("🚀 --- INICIANDO AUTOMAÇÃO BOT-XML-GMS --- 🚀")
        start_time = datetime.now()
        
        result = {
            "status": "pending",
            "started_at": start_time.isoformat(),
            "completed_at": None,
            "duration_seconds": None,
            "summary": None,
            "error": None
        }
        
        if not self.setup():
            logger.info("🏁 --- AUTOMAÇÃO FINALIZADA DEVIDO A FALHA NO SETUP --- 🏁")
            result.update({
                "status": "failed",
                "error": "Falha no setup da automação",
                "completed_at": datetime.now().isoformat()
            })
            return result

        self.browser_handler = BrowserHandler(headless=self.headless)
        summary = None
        
        try:
            self._update_status("Iniciando o navegador...", 10)
            driver = self.browser_handler.start_browser()
            if not driver:
                raise ConnectionError("Driver do navegador não foi inicializado.")

            self._update_status("Iniciando processo de login...", 20)
            login_page = LoginPage(driver, self.selectors.get('login_page', {}))
            login_page.navigate_to_login_page(self.gms_login_url)
            
            home_page_selectors = self.selectors.get('home_page', {})
            verification_selector = home_page_selectors.get('sidebar_tax')
            if not verification_selector:
                raise ValueError("Seletor de verificação pós-login ('sidebar_tax') não encontrado em selectors.yaml")
                
            login_page.execute_login(self.gms_user, self.gms_password, verification_selector)

            self._update_status("Login realizado com sucesso!", 30)

            self._update_status("Navegando na página inicial...", 40)
            home_page = HomePage(driver, self.selectors.get('home_page', {}))
            home_page.navigate_sidebar_export()

            self._update_status("Iniciando processo de exportação...", 50)
            export_page = ExportPage(driver, self.selectors.get('export_page', {}))
            export_page.export_data(self.document_type, self.emitter, self.operation_type, self.file_type, self.invoice_situation, self.start_date, self.end_date, self.stores_to_process)
            
            self._update_status("Aguardando a conclusão da exportação no sistema GMS...", 60)
            export_page.wait_for_export_completion()
            
            self._update_status("Realizando o download dos arquivos exportados...", 70)
            export_page.download_exports()

            self._update_status("Processando arquivos baixados (descompactando e organizando)...", 80)
            summary = file_handler.process_downloaded_files(self.document_type, self.start_date, self.end_date)
            self._update_status("Processamento de arquivos concluído.", 100)
            
            # Sucesso
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result.update({
                "status": "completed",
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "summary": summary
            })
            
            logger.info(f"✅ Automação concluída com sucesso em {duration:.2f}s")

        except NoInvoicesFoundException as e:
            logger.warning(f"Processo encerrado conforme esperado: {e}")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result.update({
                "status": "completed_no_invoices",
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "summary": {"status": "concluido_sem_notas", "message": str(e)}
            })

        except AutomationException as e:
            logger.error(f"ERRO DE PROCESSO: {e}", exc_info=True)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result.update({
                "status": "failed",
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e)
            })
            
        except Exception as e:
            logger.critical("ERRO INESPERADO: Ocorreu uma falha crítica na orquestração.", exc_info=True)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result.update({
                "status": "failed",
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e)
            })
            
        finally:
            if self.browser_handler:
                self.browser_handler.close_browser()
            logger.info("🏁 --- AUTOMAÇÃO FINALIZADA --- 🏁")
        
        return result
