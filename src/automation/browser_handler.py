import logging
from pathlib import Path
from datetime import datetime
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
        
        download_dir = str(settings.PENDING_DIR)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu") 
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_argument('--log-level=3')

        try:
            configured_driver_path = settings.chrome_driver_path

            if configured_driver_path and Path(configured_driver_path).exists():
                logger.info(f"Usando ChromeDriver configurado em: {configured_driver_path}")
                service = ChromeService(executable_path=configured_driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            elif Path("/usr/local/bin/chromedriver").exists():
                logger.info("Usando ChromeDriver padrão do container: /usr/local/bin/chromedriver")
                service = ChromeService(executable_path="/usr/local/bin/chromedriver")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                logger.info("ChromeDriver não encontrado em caminho fixo. Usando Selenium Manager automático.")
                self.driver = webdriver.Chrome(options=chrome_options)

            # Configurar download via CDP (essencial para headless e mais confiável em geral)
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": download_dir
            })
            logger.info(f"Download configurado via CDP para: {download_dir}")

            logger.info("Navegador iniciado com sucesso.")
            return self.driver
        
        except Exception as e:
            logger.error(f"Não foi possível iniciar o Chrome Driver: {e}", exc_info=True)
            return None

    def take_screenshot(self, name: str = "debug") -> str:
        """Captura screenshot para diagnóstico. Retorna o caminho do arquivo."""
        if not self.driver:
            logger.warning("Driver não disponível para capturar screenshot.")
            return None
        try:
            screenshots_dir = settings.BASE_DIR / "logs" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = screenshots_dir / f"{name}_{timestamp}.png"
            self.driver.save_screenshot(str(filepath))
            logger.info(f"📸 Screenshot salva: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Falha ao capturar screenshot: {e}")
            return None

    def close_browser(self):
        if self.driver:
            logger.info("Fechando o navegador.")
            self.driver.quit()
            self.driver = None