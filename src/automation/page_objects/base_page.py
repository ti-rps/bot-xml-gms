# page_objects/base_page.py
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import Select
from src.utils.exceptions import ElementNotFoundError
from selenium.webdriver.common.by import By
from config import settings
import contextlib

logger = logging.getLogger(__name__)

class BasePage:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT)

    def _get_by(self, selector: str):
        return By.XPATH if selector.startswith('/') or selector.startswith('(') else By.CSS_SELECTOR

    def _find_element(self, selector: str) -> WebElement:
        by = self._get_by(selector)
        try:
            return self.driver.find_element(by, selector)
        except NoSuchElementException:
            logger.error(f"Elemento com seletor '{selector}' não encontrado na página.")
            raise

    def wait_for_element(self, selector: str) -> WebElement:
        by = self._get_by(selector)
        try:
            return self.wait.until(EC.presence_of_element_located((by, selector)))
        except TimeoutException:
            logger.error(f"Tempo de espera excedido para o elemento com seletor: '{selector}'")
            raise

    def click(self, selector: str):
        by = self._get_by(selector)
        try:
            element = self.wait.until(EC.element_to_be_clickable((by, selector)))
            element.click()
            logger.info(f"Clicado no elemento com seletor: '{selector}'")
        except TimeoutException:
            logger.error(f"Elemento com seletor '{selector}' não se tornou clicável a tempo.")
            raise

    def send_keys(self, selector: str, text: str):
        try:
            element = self.wait_for_element(selector)
            element.clear()
            element.send_keys(text)
            logger.info(f"Texto enviado para o elemento com seletor: '{selector}'")
        except Exception as e:
            logger.error(f"Falha ao enviar texto para o elemento '{selector}': {e}")
            raise

    def select_option_by_value(self, selector: str, value: str):
        logger.info(f"Tentando selecionar a opção com valor '{value}' no seletor '{selector}'")
        try:
            select_element = self.wait_for_element(selector)
            select = Select(select_element)
            select.select_by_value(value)
            logger.info(f"Opção com valor '{value}' selecionada com sucesso no seletor '{selector}'")
        except NoSuchElementException:
            logger.error(f"Não foi encontrada uma opção com o valor '{value}' no elemento '{selector}'.")
            raise
        except Exception as e:
            logger.error(f"Falha ao selecionar a opção com valor '{value}' no elemento '{selector}': {e}")
            raise

    @contextlib.contextmanager
    def switch_to_iframe(self, selector):
        logger.info(f"Tentando entrar no iframe com seletor: '{selector}'")
        try:
            iframe = self.wait_for_element(selector)
            if not iframe:
                raise ElementNotFoundError(f"Iframe com seletor '{selector}' não foi encontrado na página.")
                
            self.driver.switch_to.frame(iframe)
            yield
        
        except ElementNotFoundError:
            raise
        except Exception as e:
            raise ElementNotFoundError(f"Erro inesperado ao tentar entrar no iframe '{selector}': {e}")
        finally:
            logger.info("Voltando para o contexto principal")
            self.driver.switch_to.default_content()


    def switch_to_parent_iframe(self):
        self.driver.switch_to.parent_frame()
        logger.info("Voltando para o iframe pai")

    def switch_to_default(self):
        self.driver.switch_to.default_content()
        logger.info("Voltando para o contexto principal")

    def get_current_url(self) -> str:
        return self.driver.current_url