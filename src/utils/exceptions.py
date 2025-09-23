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