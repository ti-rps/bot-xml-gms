import logging
import time
from selenium.webdriver.remote.webdriver import WebDriver
from .base_page import BasePage
from config import settings

logger = logging.getLogger(__name__)

class LoginPage(BasePage):
    def __init__(self, driver: WebDriver, selectors: dict):
        super().__init__(driver)
        self.selectors = selectors
        self.login_url = settings.LOGIN_URL

    def navigate_to_login_page(self):
        logger.info(f"Navegando para a página de login: {self.login_url}")
        self.driver.get(self.login_url)

    def execute_login(self, username, password):
        try:
            logger.info("Preenchendo credenciais de login.")
            self.send_keys(self.selectors['username_input'], username)
            self.send_keys(self.selectors['password_input'], password)
            time.sleep(1)
            self.click(self.selectors['login_button'])
        except KeyError as e:
            logger.error(f"Seletor não encontrado no dicionário para a página de login: {e}")
            raise
        except Exception as e:
            logger.error(f"Ocorreu um erro durante a execução do login: {e}")
            raise