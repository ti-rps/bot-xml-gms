import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from config import settings

logger = logging.getLogger(__name__)

class BrowserHandler:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver: webdriver.Chrome = None

    def start_browser(self) -> webdriver.Chrome:
        logger.info(f"Iniciando o navegador em modo {'headless' if self.headless else 'com interface'}.")
        
        chrome_options = ChromeOptions()
        
        prefs = {"download.default_directory": str(settings.PENDING_DIR)}
        chrome_options.add_experimental_option("prefs", prefs)

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu") 
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_argument('--log-level=3')

        try:
            service = ChromeService(executable_path="/usr/local/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Navegador iniciado com sucesso.")
            return self.driver
        
        except Exception as e:
            logger.error(f"Não foi possível iniciar o Chrome Driver: {e}", exc_info=True)
            return None

    def close_browser(self):
        if self.driver:
            logger.info("Fechando o navegador.")
            self.driver.quit()
            self.driver = None