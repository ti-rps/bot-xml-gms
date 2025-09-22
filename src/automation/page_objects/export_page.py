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
              
              iframe_popup = self.wait_for_element(self.selectors['popup_frame'])
              self.driver.switch_to.frame(iframe_popup)
              logger.info("Entrou no iframe do popup.")

              self.select_option_by_value(self.selectors['document_type_dropdown'], document_type)
              self.send_keys(self.selectors['start_date_input'], start_date)
              self.send_keys(self.selectors['end_date_input'], end_date)
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
                          self.click(option_selector)
                          logger.info(f"Loja '{store_code}' selecionada com sucesso.")
                          
                      except Exception as e:
                          logger.error(f"Não foi possível selecionar a loja '{store_code}': {e}")
                          raise

              logger.info("Interação no popup concluída.")
              self.switch_to_parent_iframe()
          logger.info("Processo de exportação dentro do iframe concluído.")

      except KeyError as e:
          logger.error(f"Seletor não encontrado no dicionário de exportação: {e}")
          raise
      except Exception as e:
          logger.error(f"Ocorreu um erro durante a exportação: {e}")
          raise