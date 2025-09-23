# page_objects/base_page.py
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from src.utils.exceptions import ElementNotFoundError
from selenium.webdriver.common.by import By
from config import settings
import contextlib
import unicodedata

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
    
    def _find_elements(self, selector: str) -> list[WebElement]:
        """Encontra e retorna uma LISTA de WebElements que correspondem ao seletor."""
        by = self._get_by(selector)
        return self.driver.find_elements(by, selector)

    def find_child_element(self, parent_element: WebElement, child_selector: str) -> WebElement:
        by = self._get_by(child_selector)
        try:
            return parent_element.find_element(by, child_selector)
        except NoSuchElementException:
            logger.error(f"Elemento filho com seletor '{child_selector}' não encontrado dentro do elemento pai.")
            raise

    def find_child_elements(self, parent_element: WebElement, child_selector: str) -> list[WebElement]:
        by = self._get_by(child_selector)
        return parent_element.find_elements(by, child_selector)

    def wait_for_element(self, selector: str) -> WebElement:
        by = self._get_by(selector)
        try:
            return self.wait.until(EC.presence_of_element_located((by, selector)))
        except TimeoutException:
            logger.error(f"Tempo de espera excedido para o elemento com seletor: '{selector}'")
            raise
    
    def wait_for_element_to_disappear(self, selector: str):
        logger.info(f"Aguardando o elemento com seletor '{selector}' desaparecer.")
        try:
            by = self._get_by(selector)
            self.wait.until(EC.invisibility_of_element_located((by, selector)))
            logger.info(f"Elemento '{selector}' desapareceu com sucesso.")
        except TimeoutException:
            logger.warning(f"Tempo de espera excedido para o desaparecimento do elemento: '{selector}'. Ele pode já ter desaparecido.")

    def is_element_present(self, selector: str, timeout: int = 5) -> bool:
        logger.info(f"Verificando a presença do elemento: '{selector}'")
        try:
            short_wait = WebDriverWait(self.driver, timeout)
            by = self._get_by(selector)
            short_wait.until(EC.presence_of_element_located((by, selector)))
            logger.info(f"Elemento '{selector}' está presente.")
            return True
        except TimeoutException:
            logger.info(f"Elemento '{selector}' não foi encontrado no tempo de espera.")
            return False

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

    def add_text_to_field(self, selector: str, text: str):
        try:
            element = self.wait_for_element(selector)
            element.send_keys(text)
            logger.info(f"Texto '{text}' adicionado ao elemento com seletor: '{selector}'")
        except Exception as e:
            logger.error(f"Falha ao adicionar texto para o elemento '{selector}': {e}")
            raise
    
    def normalize_text(texto: str) -> str:
        if not isinstance(texto, str):
            return ""
            
        upper_text = texto.upper()
        normalized_text = unicodedata.normalize('NFKD', upper_text)
        final_text = normalized_text.encode('ASCII', 'ignore').decode('ASCII')
        
        return final_text

    def press_key(self, selector: str, key_name: str):
        key_map = {
            "ESCAPE": Keys.ESCAPE,
            "ENTER": Keys.ENTER,
            "TAB": Keys.TAB,
            "HOME": Keys.HOME,
        }
        
        key_to_press = key_map.get(key_name.upper())
        
        if not key_to_press:
            logger.error(f"A tecla '{key_name}' não é uma tecla especial conhecida no mapeamento.")
            raise ValueError(f"A tecla '{key_name}' não é uma tecla especial conhecida.")

        logger.info(f"Pressionando a tecla '{key_name}' no elemento com seletor: '{selector}'")
        try:
            element = self.wait_for_element(selector)
            element.send_keys(key_to_press)
            logger.info(f"Tecla '{key_name}' pressionada com sucesso no elemento '{selector}'.")
        except Exception as e:
            logger.error(f"Falha ao pressionar a tecla '{key_name}' no elemento '{selector}': {e}")
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

    def select_option_by_visible_text(self, selector: str, text: str):
        logger.info(f"Tentando selecionar a opção com o texto visível '{text}' no seletor '{selector}'")
        try:
            select_element = self.wait_for_element(selector)
            select = Select(select_element)
            select.select_by_visible_text(text)
            logger.info(f"Opção com o texto '{text}' selecionada com sucesso no seletor '{selector}'")
        except NoSuchElementException:
            logger.error(f"Não foi encontrada uma opção com o texto visível '{text}' no elemento '{selector}'.")
            raise
        except Exception as e:
            logger.error(f"Falha ao selecionar a opção com o texto '{text}' no elemento '{selector}': {e}")
            raise
    
    def select_multiple_options_by_value_js(self, selector: str, values: list):
        logger.info(f"Tentando selecionar múltiplas opções via JS para o seletor '{selector}' com valores: {values}")
        
        js_values_array = str(values)

        script = f"""
            var selectElement = document.querySelector('{selector}');
            if (!selectElement) {{
                return 'Elemento select não encontrado com o seletor: {selector}';
            }}
            var valuesToSelect = {js_values_array};
            var options = selectElement.options;

            for (var i = 0; i < options.length; i++) {{
                options[i].selected = false;
            }}

            for (var i = 0; i < options.length; i++) {{
                if (valuesToSelect.includes(options[i].value)) {{
                    options[i].selected = true;
                }}
            }}

            selectElement.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'Seleção concluída com sucesso.';
        """
        
        try:
            result = self.driver.execute_script(script)
            logger.info(f"Resultado da execução do script de multiselect: {result}")
        except Exception as e:
            logger.error(f"Falha ao executar o script para selecionar múltiplas opções: {e}")
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
            logger.info("Voltando para o iframe pai")
            self.driver.switch_to.parent_frame()


    def switch_to_parent_iframe(self):
        self.driver.switch_to.parent_frame()
        logger.info("Voltando para o iframe pai")

    def switch_to_default(self):
        self.driver.switch_to.default_content()
        logger.info("Voltando para o contexto principal")

    def get_current_url(self) -> str:
        return self.driver.current_url