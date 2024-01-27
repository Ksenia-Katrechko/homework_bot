class APIException(Exception):
    """Базовый класс для обработки API."""


class APITelegramException(APIException):
    """Класс для ошибок, требующих передачи в Телеграм."""


class APIOtherException(APIException):
    """Класс для остальных ошибок, которые не требуют передачи в Телеграм."""
