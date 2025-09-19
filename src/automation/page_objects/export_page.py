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

  def export_data(self):
    try:
      with self.switch_to_iframe(self.selectors['legado_frame']):
        self.click(self.selectors['include_button'])
        # with self.switch_to_iframe(self.selectors['popup_frame']):
        #  logger.info("Dentro do popup de exportação.")
      logger.info("Interação no popup concluída, de volta ao iframe principal.")

    except KeyError as e:
      logger.error(f"Seletor não encontrado no dicionário de exportação: {e}")
      raise
    except Exception as e:
      logger.error(f"Ocorreu um erro durante a exportação: {e}")
      raise
    finally:
      self.switch_to_default()