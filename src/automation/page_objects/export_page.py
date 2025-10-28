#page_objects/export_page.py
import time
import logging
from selenium.webdriver.remote.webdriver import WebDriver
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

                        if "Concluído" in status_col:
                            logger.info("✅ Exportação concluída com sucesso!")
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
                
        raise TimeoutError(f"A exportação não foi concluída no tempo limite de {minutes} minutos.")
    
    def download_exports(self):
        logger.info("Iniciando o download dos arquivos exportados...")
        try:
            with self.switch_to_iframe(self.selectors['legado_frame']):
                first_row_selector = f"({self.selectors['table_rows']})[3]"
                self.wait_for_element(first_row_selector)
                self.click(first_row_selector)
                download_button_selector = self.selectors['download_button']
                self.wait_for_element(download_button_selector)
                self.click(download_button_selector)
                logger.info("Clique no botão de download realizado.")
                    
        except Exception as e:
            logger.error(f"Ocorreu um erro durante o processo de download: {e}")
            raise
        logger.info("Processo de download iniciado. Verifique a pasta de downloads do navegador.")
    
