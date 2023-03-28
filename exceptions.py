"""
Здесь хранятся используемые исключения.
The exceptions used are stored here.
"""


ENVIRONMENT_VARIABLE_IS_MISSING = 'Переменная окружения отсутствует.'
MESSAGE_SENT_SUCCESSFULLY = 'Сообщение "{message}" успешно отправлено.'
HOMEWORS_LIST_IS_EMPTY = 'Список домашних работ пуст.'
UNKNOWN_STATUS = 'Неизвестный статус домашней работы.'
FAILED_SEND_MESSAGE = 'Не удалось отправить сообщение пользователю.'


class StatusCodeError(Exception):
    """Ошибка. Недокументированный статус домашней работы."""


class AccessError(Exception):
    """Ошибка. При обращении к сервису, произошла ошибка доступа."""


class EndpointError(Exception):
    """Ошибка. Некорректный эндпоинт запроса к API-сервису."""
