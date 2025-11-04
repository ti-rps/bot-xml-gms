# src/core/bot_runner.py
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Callable
from src.automation.browser_handler import BrowserHandler
from src.utils import data_handler
from src.utils.logger_config import set_task_id
from config import settings as config_settings
from src.automation.page_objects.login_page import LoginPage
from src.automation.page_objects.home_page import HomePage
from src.automation.page_objects.export_page import ExportPage
from src.utils import file_handler
from src.utils.exceptions import AutomationException, NoInvoicesFoundException

logger = logging.getLogger(__name__)

class BotRunner:
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
        
        self.job_id = job_id
        self.log_callback = log_callback
        
        if not self.gms_user:
            self.gms_user = os.getenv('GMS_USER') or config_settings.gms_username
        if not self.gms_password:
            self.gms_password = os.getenv('GMS_PASSWORD') or config_settings.gms_password
            
        self.gms_login_url = params.get('gms_login_url')
        self.browser_handler = None
        self.selectors = None
        
        self.status = "idle"
        self.progress = 0
        self.current_message = ""
        
        if not self.gms_user or not self.gms_password:
            raise ValueError("Credenciais GMS_USER e GMS_PASSWORD não foram encontradas nem nos parâmetros da API nem nas variáveis de ambiente.")
        
        if not self.gms_login_url:
            raise ValueError("Parâmetro obrigatório 'gms_login_url' não fornecido.")
        
        if not config_settings.SELECTORS_FILE.exists():
            raise FileNotFoundError(f"Arquivo de seletores não encontrado: {config_settings.SELECTORS_FILE}")
        
        if not self.stores_to_process:
            raise ValueError("Parâmetro obrigatório 'stores' não fornecido ou vazio.")
        
        logger.info(f"🤖 BotRunner inicializado com sucesso - Job ID: {job_id}")
        
    def _update_status(self, message: str, progress: int = None):
        self.current_message = message
        if progress is not None:
            self.progress = progress
        
        logger.info(message)
        
        if self.log_callback and self.job_id:
            try:
                self.log_callback(self.job_id, "INFO", message)
            except Exception as e:
                logger.warning(f"Falha ao enviar log para o Maestro via callback: {e}")

    def setup(self):
        self._update_status("Preparando ambiente para a execução...", 5)
        
        if self.job_id:
            set_task_id(self.job_id)
        
        logger.debug(f"Setup iniciado para job_id: {self.job_id}")
        logger.debug(f"Lojas a processar: {self.stores_to_process}")
        
        if not self.stores_to_process:
            logger.warning("Nenhuma loja fornecida nos parâmetros para processar.")
            return False
        
        logger.debug(f"Carregando seletores de: {config_settings.SELECTORS_FILE}")
        self.selectors = data_handler.load_yaml_file(config_settings.SELECTORS_FILE)
        if not self.selectors:
            logger.error("Falha ao carregar seletores. A automação não pode continuar.")
            return False
        
        logger.debug(f"✅ Seletores carregados com sucesso. Total: {len(self.selectors)} seções")
        return True
    
    def run(self) -> Dict:
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
            logger.debug(f"Configuração de headless: {self.headless}")
            
            MAX_BROWSER_RETRIES = 3
            driver = None
            
            for attempt in range(1, MAX_BROWSER_RETRIES + 1):
                try:
                    logger.info(f"Tentativa {attempt}/{MAX_BROWSER_RETRIES} de inicializar o navegador...")
                    driver = self.browser_handler.start_browser()
                    
                    if not driver:
                        raise ConnectionError("Driver do navegador não foi inicializado.")
                    
                    logger.debug("✅ Driver do navegador iniciado com sucesso")
                    break
                    
                except Exception as browser_error:
                    logger.warning(f"⚠️ Falha na tentativa {attempt}/{MAX_BROWSER_RETRIES} de iniciar o navegador: {browser_error}")
                    
                    try:
                        if self.browser_handler and self.browser_handler.driver:
                            self.browser_handler.close_browser()
                    except:
                        pass
                    
                    if attempt < MAX_BROWSER_RETRIES:
                        import time
                        wait_time = attempt * 2
                        logger.info(f"Aguardando {wait_time}s antes de tentar novamente...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ Todas as {MAX_BROWSER_RETRIES} tentativas de iniciar o navegador falharam")
                        raise ConnectionError(f"Não foi possível inicializar o navegador após {MAX_BROWSER_RETRIES} tentativas")
            
            if not driver:
                raise ConnectionError("Driver do navegador não foi inicializado após todas as tentativas.")

            self._update_status("Iniciando processo de login...", 20)
            logger.debug(f"Tentando login na URL: {self.gms_login_url.split('/')[2]}")
            login_page = LoginPage(driver, self.selectors.get('login_page', {}))
            login_page.navigate_to_login_page(self.gms_login_url)
            
            home_page_selectors = self.selectors.get('home_page', {})
            verification_selector = home_page_selectors.get('sidebar_tax')
            if not verification_selector:
                raise ValueError("Seletor de verificação pós-login ('sidebar_tax') não encontrado em selectors.yaml")
            
            logger.debug(f"Executando login com usuário: {self.gms_user}")
            login_page.execute_login(self.gms_user, self.gms_password, verification_selector)
            logger.debug("✅ Login executado com sucesso")

            self._update_status("Login realizado com sucesso!", 30)

            self._update_status("Navegando na página inicial...", 40)
            home_page = HomePage(driver, self.selectors.get('home_page', {}))
            logger.debug(f"Navegando para página de exportação")
            home_page.navigate_sidebar_export()

            self._update_status("Iniciando processo de exportação...", 50)
            logger.debug(f"Parâmetros de exportação: doc_type={self.document_type}, emitter={self.emitter}, op={self.operation_type}")
            logger.debug(f"Período: {self.start_date} até {self.end_date}")
            logger.debug(f"Lojas: {self.stores_to_process}")
            export_page = ExportPage(driver, self.selectors.get('export_page', {}))
            export_page.export_data(self.document_type, self.emitter, self.operation_type, self.file_type, self.invoice_situation, self.start_date, self.end_date, self.stores_to_process)
            logger.debug("✅ Dados de exportação enviados para GMS")
            
            self._update_status("Aguardando a conclusão da exportação no sistema GMS...", 60)
            logger.debug("Aguardando conclusão da exportação...")
            export_page.wait_for_export_completion()
            logger.debug("✅ Exportação concluída no GMS")
            
            self._update_status("Realizando o download dos arquivos exportados...", 70)
            logger.debug("Iniciando download dos arquivos...")
            export_page.download_exports()
            logger.debug("✅ Download dos arquivos concluído")

            self._update_status("Processando arquivos baixados (descompactando e organizando)...", 80)
            logger.debug("Processando arquivos baixados...")
            summary = file_handler.process_downloaded_files(self.document_type, self.start_date, self.end_date)
            logger.debug(f"✅ Resumo do processamento: {summary}")
            self._update_status("Processamento de arquivos concluído.", 100)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.debug(f"Tempo total de execução: {duration:.2f}s")
            
            result.update({
                "status": "completed",
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "summary": summary
            })
            
            logger.info(f"✅ Automação concluída com sucesso em {duration:.2f}s")

        except NoInvoicesFoundException as e:
            logger.debug(f"NoInvoicesFoundException capturada: {type(e).__name__}")
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
            logger.debug(f"AutomationException capturada: {type(e).__name__}")
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
            logger.debug(f"Exception genérica capturada: {type(e).__name__}")
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
