#page_objects/export_page.py
import time
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from .base_page import BasePage

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
                    self.click(self.selectors['export_button'])
                    logger.info("Interação no popup concluída.")
                    
            logger.info("Processo de exportação dentro do iframe concluído.")

        except KeyError as e:
            logger.error(f"Seletor não encontrado no dicionário de exportação: {e}")
            raise
        except Exception as e:
            logger.error(f"Ocorreu um erro durante a exportação: {e}")
            raise

    def wait_for_export_completion(self, document_type: str, operation_type: str, file_type: str, emitter: str, stores_to_process: list, start_date: str, end_date: str, user_identifier: str):

        logger.info("Iniciando monitoramento da tabela de exportação...")
        
        stores_str = ",".join(map(str, stores_to_process))
        
        timeout = time.time() + 60 * 15 
        
        while time.time() < timeout:
            try:
                with self.switch_to_iframe(self.selectors['legado_frame']):
                    logger.info("Analisando a tabela de exportação dentro do iframe 'legadoFrame'.")
                    
                    table_rows_selector = self.selectors['table_rows']
                    
                    if not self.is_element_present(table_rows_selector):
                        logger.info("Nenhuma linha encontrada na tabela ainda. Aguardando...")
                    else:
                        rows_elements = self._find_elements(table_rows_selector)
                        num_rows = len(rows_elements)
                        
                    if num_rows == 0:
                        logger.info("Elemento da tabela existe, mas não há linhas. Aguardando...")
                        continue
                    
                    found_row = False
                    for i in range(1, num_rows + 1):
                        row_selector = f"({table_rows_selector})[{i}]"
                        row_element = self.wait_for_element(row_selector)
                        columns = self.find_child_elements(row_element, "td")
                        
                        if len(columns) < 19: continue

                        doc_type_col = self.normalize_text(columns[2].text)
                        op_type_col = self.normalize_text(columns[3].text)
                        file_type_col = self.normalize_text(columns[4].text)
                        emitter_col = self.normalize_text(columns[5].text)
                        stores_col = self.normalize_text(columns[6].text)
                        start_date_col = self.normalize_text(columns[7].text)
                        end_date_col = self.normalize_text(columns[8].text)
                        user_col = self.normalize_text(columns[17].text)
                        status_col = self.normalize_text(columns[18].text)

                        if (doc_type_col == document_type and
                            op_type_col == operation_type and
                            file_type_col == file_type and
                            emitter_col == emitter and
                            stores_col == stores_str and
                            start_date_col == start_date and 
                            end_date_col == end_date and
                            user_col == user_identifier):
                            
                            logger.info(f"Linha da exportação encontrada na posição {i}! Status atual: '{status_col}'")
                            found_row = True
                            
                            if "CONCLUIDO" in status_col:
                                logger.info("✅ Exportação concluída com sucesso!")
                                return
                            
                            if "ERRO" in status_col:
                                logger.error("❌ A exportação falhou, status 'Com erro' encontrado na tabela.")
                                raise Exception("A exportação retornou o status 'Com erro'.")
                            
                            break
                    
                    if not found_row:
                        logger.info("Nossa linha de exportação ainda não apareceu ou não corresponde. Verificando novamente...")

            except Exception as e:
                logger.error(f"Ocorreu um erro inesperado durante o monitoramento: {e}")
                raise

            logger.info("Aguardando 30 segundos antes de verificar a tabela novamente...")
            time.sleep(30)
            self.driver.refresh()
            self.wait_for_element(self.selectors['search_button'])
            self.click(self.selectors['search_button'])
        raise TimeoutError("A exportação não foi concluída no tempo limite.")