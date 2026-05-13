# src/utils/exceptions.py

class AutomationException(Exception):
    """Classe base para exceções customizadas da automação."""
    pass

class LoginError(AutomationException):
    """Lançada quando ocorre um erro durante o processo de login."""
    pass

class NavigationError(AutomationException):
    """Lançada quando ocorre um erro ao navegar entre páginas ou elementos."""
    pass

class DataExportError(AutomationException):
    """Lançada quando a exportação de dados falha por um motivo esperado."""
    pass

class ElementNotFoundError(AutomationException):
    """Lançada quando um elemento crucial não é encontrado na página."""
    pass

class ConfigurationError(AutomationException):
    """Lançada quando há erro ao carregar configurações (selectors, env, etc)."""
    pass

class NoInvoicesFoundException(AutomationException):
    """Exceção levantada quando nenhuma nota fiscal é encontrada para os filtros de exportação."""
    pass

class JobCanceledException(Exception):
    """Levantada quando o maestro sinaliza cancelamento do job em execução.

    Não herda de AutomationException porque cancelamento não é erro de automação —
    é sinal de controle e o BotRunner trata com handler dedicado (não fica como
    'failed' no resto do pipeline).
    """

    def __init__(self, stage: str):
        self.stage = stage
        super().__init__(f"Job cancelado pelo usuário durante a etapa: {stage}")