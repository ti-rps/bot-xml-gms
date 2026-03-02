#page_objects/export_page.py
import time
import logging
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_page import BasePage
from config import settings
from src.utils.exceptions import NoInvoicesFoundException

logger = logging.getLogger(__name__)

class ExportPage(BasePage):
    def __init__(self, driver: WebDriver, selectors: dict):
        super().__init__(driver)
        self.selectors = selectors

    def export_data(self, document_type: str, emitter: str, operation_type: str, file_type: str, invoice_situation: str, start_date: str, end_date: str, stores_to_process: list):
        try:
            with self.switch_to_iframe(self.selectors['legado_frame']):
                self.click(self.selectors['include_button'])
              
                with self.switch_to_iframe(self.selectors['popup_frame']):
                    logger.info("Entrou no iframe do popup.")

                    self.select_option_by_value(self.selectors['document_type_dropdown'], document_type)

                    self.click(self.selectors['start_date_input'])
                    self.add_text_to_field(self.selectors['start_date_input'], start_date)
                    self.click(self.selectors['end_date_input'])
                    self.press_key(self.selectors['end_date_input'], 'HOME')
                    self.add_text_to_field(self.selectors['end_date_input'], end_date)

                    self.select_option_by_value(self.selectors['emitter_dropdown'], emitter)
                    if operation_type != 'TODAS':
                        self.select_option_by_value(self.selectors['operation_type_dropdown'], operation_type)
                    self.select_option_by_value(self.selectors['file_type_dropdown'], file_type)
                    self.select_option_by_value(self.selectors['invoice_situation_dropdown'], invoice_situation)

                    if stores_to_process:
                        logger.info(f"Selecionando as lojas via input: {stores_to_process}")
                        
                        for store_code in stores_to_process:
                            try:
                                self.send_keys(self.selectors['stores_input'], str(store_code))
                                option_selector = f"//li[@role='option' and contains(., '{store_code}')]"
                                self.wait_for_element(option_selector)
                                time.sleep(0.5)
                                self.click(option_selector)
                                logger.info(f"Loja '{store_code}' selecionada com sucesso.")
                                
                            except Exception as e:
                                logger.error(f"Não foi possível selecionar a loja '{store_code}': {e}")
                                raise

                    self.wait_for_element(self.selectors['export_button'])
                    self.click( self.selectors['popup_header'])
                    self.click(self.selectors['export_button'])
                    logger.info("Clique no botão de exportar realizado.")
                    time.sleep(1)
                    if self.is_element_present(self.selectors['alert_msg'], timeout=settings.DEFAULT_TIMEOUT // 10):
                        alert_element = self._find_element(self.selectors['alert_msg'])
                        if "Não existem notas a serem exportadas para esse filtro." in alert_element.text:
                            logger.warning("Nenhuma nota encontrada para os filtros especificados. Encerrando o processo de exportação.")
                            raise NoInvoicesFoundException("Não existem notas a serem exportadas para o filtro selecionado.")

                    logger.info("Interação no popup concluída.")
                    
            logger.info("Processo de exportação dentro do iframe concluído.")

        except KeyError as e:
            logger.error(f"Seletor não encontrado no dicionário de exportação: {e}")
            raise
        except Exception as e:
            logger.error(f"Ocorreu um erro durante a exportação: {e}")
            raise

    def wait_for_export_completion(self):
        logger.info("Iniciando monitoramento da tabela de exportação (verificando apenas a primeira linha)...")
        minutes = 180
        timeout = time.time() + 60 * minutes
        
        while time.time() < timeout:
            try:
                with self.switch_to_iframe(self.selectors['legado_frame']):
                    logger.info("Analisando a primeira linha da tabela de exportação...")
                    
                    first_row_selector = f"({self.selectors['table_rows']})[3]"
                    
                    if not self.is_element_present(first_row_selector):
                        logger.info("Nenhuma linha encontrada na tabela ainda. Aguardando...")
                    else:
                        first_row_element = self.wait_for_element(first_row_selector)
                        columns = self.find_child_elements(first_row_element, "td")
                        status_col = columns[18].text
                        logger.info(f"Status atual da exportação: '{status_col}'")

                        if "Concluído" in status_col:
                            logger.info("✅ Exportação concluída com sucesso!")
                            
                            # Capturar screenshot do estado "Concluído" para diagnóstico
                            try:
                                self.driver.switch_to.default_content()
                                screenshots_dir = settings.BASE_DIR / "logs" / "screenshots"
                                screenshots_dir.mkdir(parents=True, exist_ok=True)
                                screenshot_path = screenshots_dir / f"export_concluded_{int(time.time())}.png"
                                self.driver.save_screenshot(str(screenshot_path))
                                logger.info(f"📸 Screenshot do status concluído: {screenshot_path}")
                            except Exception:
                                pass
                            
                            return
                        if "Em processamento" in status_col:
                            logger.info("⏳ A exportação está em processamento. Continuando a monitorar...")
                        if "Pendente" in status_col:
                            logger.info("⏳ A exportação está pendente. Continuando a monitorar...")
                        if "com Erro" in status_col:
                            logger.error("❌ A exportação falhou, status 'Com erro' encontrado na tabela.")
                            raise Exception("A exportação retornou o status 'Com erro'.")

            except Exception as e:
                logger.error(f"Ocorreu um erro inesperado durante o monitoramento: {e}")
                raise

            logger.info("Aguardando 30 segundos antes de verificar a tabela novamente...")
            time.sleep(30)
            self.driver.refresh()
            with self.switch_to_iframe(self.selectors['legado_frame']):
                self.wait_for_element(self.selectors['search_button'])
                self.click(self.selectors['search_button'])
                time.sleep(3)  # Aguardar a tabela ser recarregada após o clique em pesquisar
                
        raise TimeoutError(f"A exportação não foi concluída no tempo limite de {minutes} minutos.")
    
    def download_exports(self):
        logger.info("Iniciando o download dos arquivos exportados...")
        pending_dir = settings.PENDING_DIR

        # Limpar arquivos antigos do diretório pending antes de iniciar o download
        existing_files_before = set(pending_dir.glob('*'))
        logger.info(f"Arquivos existentes em pending antes do download: {[f.name for f in existing_files_before]}")

        try:
            with self.switch_to_iframe(self.selectors['legado_frame']):
                first_row_selector = f"({self.selectors['table_rows']})[3]"
                self.wait_for_element(first_row_selector)
                
                # Clicar na linha para selecioná-la
                logger.info("Clicando na primeira linha da tabela para selecioná-la...")
                self.click(first_row_selector)
                time.sleep(1)

                # Verificar se a linha foi selecionada (class 'selected' ou similar)
                first_row_element = self._find_element(first_row_selector)
                row_classes = first_row_element.get_attribute("class") or ""
                logger.info(f"Classes da linha após clique: '{row_classes}'")

                # Tentar também clicar no checkbox/input da linha se existir
                try:
                    checkbox_selector = f"({self.selectors['table_rows']})[3]//input[@type='checkbox']"
                    if self.is_element_present(checkbox_selector, timeout=2):
                        self.click(checkbox_selector)
                        logger.info("Checkbox da linha clicado.")
                        time.sleep(0.5)
                except Exception:
                    logger.debug("Nenhum checkbox encontrado na linha (pode não ser necessário).")

                download_button_selector = self.selectors['download_button']
                self.wait_for_element(download_button_selector)
                
                # Log do estado do botão de download antes de clicar
                download_btn = self._find_element(download_button_selector)
                btn_enabled = download_btn.is_enabled()
                btn_displayed = download_btn.is_displayed()
                logger.info(f"Botão de download - Enabled: {btn_enabled}, Displayed: {btn_displayed}")

                if not btn_enabled:
                    logger.warning("⚠️ O botão de download está desabilitado! A linha pode não estar selecionada corretamente.")
                
                # Tentar click normal primeiro
                self.click(download_button_selector)
                logger.info("Clique no botão de download realizado.")

                # Aguardar um momento para ver se algum diálogo/alerta aparece
                time.sleep(2)

                # Verificar se há algum alert do browser
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    logger.info(f"Alert detectado após click no download: '{alert_text}'")
                    alert.accept()
                    logger.info("Alert aceito.")
                except Exception:
                    logger.debug("Nenhum alert do browser detectado após click no download.")

        except Exception as e:
            logger.error(f"Ocorreu um erro durante o processo de download: {e}")
            # Capturar screenshot para diagnóstico
            try:
                self.driver.switch_to.default_content()
                screenshots_dir = settings.BASE_DIR / "logs" / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = screenshots_dir / f"download_error_{int(time.time())}.png"
                self.driver.save_screenshot(str(screenshot_path))
                logger.info(f"📸 Screenshot de erro salva: {screenshot_path}")
            except Exception as ss_err:
                logger.debug(f"Falha ao salvar screenshot de erro: {ss_err}")
            raise

        # AGUARDAR O DOWNLOAD SER CONCLUÍDO (fora do iframe)
        logger.info("Aguardando o download do arquivo ser concluído no diretório pending...")
        self._wait_for_download_complete(pending_dir, existing_files_before)
        logger.info("✅ Download dos arquivos concluído com sucesso.")

    def _wait_for_download_complete(self, pending_dir: Path, files_before: set, timeout_seconds: int = None):
        """Aguarda o download do arquivo ser concluído no diretório pending."""
        if timeout_seconds is None:
            timeout_seconds = settings.download_timeout

        logger.info(f"Monitorando diretório de downloads por até {timeout_seconds} segundos...")
        start_time = time.time()
        download_detected = False

        while time.time() - start_time < timeout_seconds:
            current_files = set(pending_dir.glob('*'))
            new_files = current_files - files_before

            # Verificar downloads em andamento (Chrome usa .crdownload, Firefox usa .part)
            downloading_files = [f for f in new_files if f.suffix in ('.crdownload', '.part', '.tmp')]
            completed_zips = [f for f in new_files if f.suffix == '.zip']

            if downloading_files:
                if not download_detected:
                    logger.info(f"📥 Download detectado! Arquivo(s) em progresso: {[f.name for f in downloading_files]}")
                    download_detected = True
                else:
                    sizes = {f.name: f.stat().st_size for f in downloading_files if f.exists()}
                    logger.debug(f"Download em progresso... Tamanhos: {sizes}")

            if completed_zips:
                # Verificar se o arquivo está estável (tamanho não muda)
                zip_file = completed_zips[0]
                size_1 = zip_file.stat().st_size
                time.sleep(3)
                
                if not zip_file.exists():
                    logger.debug("Arquivo ZIP desapareceu (pode ter sido renomeado). Continuando monitoramento...")
                    continue

                size_2 = zip_file.stat().st_size

                if size_1 == size_2 and size_2 > 0:
                    logger.info(f"✅ Download concluído: {zip_file.name} ({size_2:,} bytes)")
                    return
                else:
                    logger.info(f"Arquivo ZIP ainda sendo escrito... ({size_1} -> {size_2} bytes)")

            elapsed = int(time.time() - start_time)
            if elapsed > 0 and elapsed % 30 == 0:
                logger.info(f"⏳ Aguardando download... ({elapsed}s decorridos)")

            time.sleep(3)

        # Timeout - capturar estado final para diagnóstico
        final_files = list(pending_dir.glob('*'))
        logger.error(f"❌ Timeout no download! Arquivos em pending após {timeout_seconds}s: {[f.name for f in final_files]}")
        
        # Capturar screenshot final
        try:
            self.driver.switch_to.default_content()
            screenshots_dir = settings.BASE_DIR / "logs" / "screenshots" 
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = screenshots_dir / f"download_timeout_{int(time.time())}.png"
            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"📸 Screenshot de timeout salva: {screenshot_path}")
        except Exception:
            pass

        raise TimeoutError(f"O download não foi concluído no tempo limite de {timeout_seconds} segundos.")
    
