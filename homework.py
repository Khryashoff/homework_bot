import os
import sys
import json
import time
import logging
import requests
import telegram
import exceptions


from typing import Union
from dotenv import load_dotenv
from http import HTTPStatus


load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN_YP')
TELEGRAM_TOKEN = os.getenv('TOKEN_BOT')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens() -> bool:
    """
    Функция проверяет доступность переменных окружения.

    Result:
        True - если все переменные окружения доступны.
        False - если какая-то из переменных окружения недоступна.
    """
    token_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in token_list:
        if token is None:
            logging.critical(exceptions.ENVIRONMENT_VARIABLE_IS_MISSING)
            return False
    return True


def get_api_answer(timestamp: int) -> Union[dict, Exception]:
    """
    Функция производит запрос к эндпоинту API-сервиса.

    Attributes:
        timestamp: int - текущее время в секундах.
    Result:
        dict - JSON-ответ API-сервиса в виде словаря.
    """
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Ошибка при запросе к эндпоинту API-сервиса. '
                f'Код статуса: {response.status_code}.'
            )
            raise exceptions.EndpointError(response.status_code)

    except json.decoder.JSONDecodeError as error:
        logging.error(f'Ошибка при декодировании JSON: {error}.')
        return error

    except requests.exceptions.ConnectionError as error:
        logging.error(f'Ошибка соединения: {error}.')
        return error

    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}.')
        raise SystemError(f'Запрошенный эндпоинт не доступен: {error}.')

    else:
        return response.json()


def check_response(response: dict) -> dict:
    """
    Функция проверяет соответствие ответа API ожидаемому значению.

    Attributes:
        response: dict - JSON-ответ API в виде словаря.
    Result:
        dict - информация о первой домашней работе из списка в виде словаря.
    """
    if 'code' in response:
        logging.error(f'Ошибка доступа к API. Код: {response["code"]}.')
        raise exceptions.AccessError(
            f'При обращении к сервису, произошла ошибка доступа. '
            f'Код: {response["code"]}.'
        )

    if not isinstance(response, dict):
        logging.error(
            'Некорректный формат ответа API. '
            'Объект "response" должен быть словарём.'
        )
        raise TypeError(
            'Некорректный формат ответа API. '
            'Данные приходят не в виде словаря.'
        )

    if 'homeworks' not in response:
        logging.error(
            'Некорректный формат ответа API. Отсутствует ключ "homeworks".'
        )
        raise KeyError(
            'Структура данных не соответствует ожиданиям. '
            'Отсутствует ключ "homeworks".'
        )

    if not isinstance(response['homeworks'], list):
        logging.error(
            'Некорректный формат ответа API. '
            'Ключ "homeworks" должен быть списком.'
        )
        raise TypeError(
            'Некорректный формат ответа API. Данные приходят не в виде списка.'
        )

    if response['homeworks']:
        return response['homeworks'][0]

    else:
        logging.error(exceptions.HOMEWORS_LIST_IS_EMPTY)
        raise IndexError(exceptions.HOMEWORS_LIST_IS_EMPTY)


def parse_status(homework: dict) -> str:
    """
    Функция извлекает из ответа API статус проверки домашней работы.

    Attributes:
        homework: dict - словарь с информацией о домашней работе.
    Result:
        message: str - сообщение с информацией о статусе проверки работы.
    """
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError(
            'Ключ "homework_name" отсутствует в словаре "homework".'
        )

    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        logging.error(exceptions.UNKNOWN_STATUS)
        raise exceptions.StatusCodeError(
            f'Некорректный статус домашней работы: {homework_status}'
        )

    verdict = HOMEWORK_VERDICTS[homework_status]
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def send_message(bot: telegram.Bot, message: str) -> None:
    """
    Функция отправляет сообщение о статусе домашней работы пользователю.

    Attributes:
        bot: объект бота из библиотеки python-telegram-bot.
        message: str - сообщение с информацией о статусе проверки работы.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение "{message}" отправленно пользователю.')
    except telegram.error.TelegramError as error:
        logging.error(f'{exceptions.FAILED_SEND_MESSAGE}. Ошибка: {error}')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status_check = ''

    if not check_tokens():
        logging.critical(
            'Ошибка. Отсутствует одна или несколько переменных окружения.'
        )
        sys.exit()

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response['current_date']
            homework = check_response(response)
            message = parse_status(homework)
            status_check_now = homework['status']
            if status_check_now != status_check:
                send_message(bot, message)
            status_check = status_check_now
            logging.debug(exceptions.MESSAGE_SENT_SUCCESSFULLY.format(message))
            logging.info(homework)

        except IndexError:
            message = 'Статус домашней работы не изменился'
            send_message(bot, message)
            logging.debug(exceptions.MESSAGE_SENT_SUCCESSFULLY.format(message))
            logging.info(message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.debug(exceptions.MESSAGE_SENT_SUCCESSFULLY.format(message))

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':

    logging.basicConfig(
        format=(
            '%(asctime)s-%(levelname)s-%(funcName)s-%(lineno)d-%(message)s'
        ),
        filename='main.log',
        filemode='w',
        level=logging.DEBUG,
        encoding='utf-8',
    )

    main()
