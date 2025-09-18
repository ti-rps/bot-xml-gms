import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from config import settings

logger = logging.getLogger(__name__)

class BasePage:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, settings.DEFAULT_TIMEOUT)

    def _find_element(self, selector: str) -> WebElement:
        by = By.XPATH if selector.startswith('/') or selector.startswith('(') else By.CSS_SELECTOR
        try:
            return self.driver.find_element(by, selector)
        except NoSuchElementException:
            logger.error(f"Elemento com seletor '{selector}' não encontrado na página.")
            raise

    def wait_for_element(self, selector: str) -> WebElement:
        by = By.XPATH if selector.startswith('/') or selector.startswith('(') else By.CSS_SELECTOR
        try:
            return self.wait.until(EC.presence_of_element_located((by, selector)))
        except TimeoutException:
            logger.error(f"Tempo de espera excedido para o elemento com seletor: '{selector}'")
            raise

    def click(self, selector: str):
        by = By.XPATH if selector.startswith('/') or selector.startswith('(') else By.CSS_SELECTOR
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

    def get_current_url(self) -> str:
        return self.driver.current_url