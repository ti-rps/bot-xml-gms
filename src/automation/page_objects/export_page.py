#page_objects/export_page.py
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from .base_page import BasePage
from config import settings

logger = logging.getLogger(__name__)

class ExportPage(BasePage):
  def __init__(self, driver: WebDriver, selectors: dict):
    super().__init__(driver)
    self.selectors = selectors

  def export_data(self, document_type: str, data_inicial: str, data_final: str):
      try:
          with self.switch_to_iframe(self.selectors['legado_frame']):
              self.click(self.selectors['include_button'])
              
              iframe_popup = self.wait_for_element(self.selectors['popup_frame'])
              self.driver.switch_to.frame(iframe_popup)
              logger.info("Entrou no iframe do popup.")

              self.select_option_by_value(self.selectors['document_type_dropdown'], document_type)
              self.send_keys(self.selectors['start_date_input'], data_inicial)
              self.send_keys(self.selectors['end_date_input'], data_final)
              logger.info("Interação no popup concluída.")

              self.switch_to_parent_iframe()
          logger.info("Processo de exportação dentro do iframe concluído.")

      except KeyError as e:
          logger.error(f"Seletor não encontrado no dicionário de exportação: {e}")
          raise
      except Exception as e:
          logger.error(f"Ocorreu um erro durante a exportação: {e}")
          raise