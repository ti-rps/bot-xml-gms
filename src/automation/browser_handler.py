# src/automation/browser_handler.py
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from config import settings

logger = logging.getLogger(__name__)

class BrowserHandler:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    def start_browser(self):
        logger.info("Iniciando o navegador...")
        
        chrome_options = webdriver.ChromeOptions()
        
        prefs = {"download.default_directory": str(settings.PENDING_DIR)}
        chrome_options.add_experimental_option("prefs", prefs)
        
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")

        try:
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            return self.driver
        except Exception as e:
            logger.error(f"Não foi possível iniciar o Chrome Driver: {e}")
            raise

    def close_browser(self):
        if self.driver:
            logger.info("Fechando o navegador.")
            self.driver.quit()