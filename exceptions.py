"""Собственные исключения."""


class MissingTokenError(Exception):
    """Ошибка отсутствия обязательных токенов."""


class MessageError(Exception):
    """Ошибка отправки сообщения."""


class EmptyAPIResponseError(Exception):
    """Ошибка ответа API."""


class HomeworkParseError(Exception):
    """Ошибка парсинга домашней страницы."""


class InvalidAPIResponseError(Exception):
    """Неферный формат ответа API."""


class APIConnectionError(Exception):
    """Ошибка соединения с API."""
