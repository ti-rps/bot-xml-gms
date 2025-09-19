#page_objects/home_page.py
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from .base_page import BasePage
from config import settings

logger = logging.getLogger(__name__)

class HomePage(BasePage):
  def __init__(self, driver: WebDriver, selectors: dict):
    super().__init__(driver)
    self.selectors = selectors

  def navigate_sidebar_export(self):
    try:
      logger.info("Navegando para a seção de exportação via sidebar.")
      self.click(self.selectors['sidebar_tax'])
      self.click(self.selectors['sidebar_tax_integration'])
      self.click(self.selectors['sidebar_tax_integration_export'])
    except KeyError as e:
        logger.error(f"Seletor não encontrado no dicionário para a página de login: {e}")
        raise
    except Exception as e:
        logger.error(f"Ocorreu um erro durante a execução do login: {e}")
        raise