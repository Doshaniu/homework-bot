"""Бот для проверки статуса домашнего задания."""
import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка правильности и доступности токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing = []
    for name, value in tokens.items():
        if not value:
            missing.append(name)
    return missing


def send_message(bot, message):
    """Отправка сообщения в телеграм при смене статуса."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено %s', message)
    except Exception as e:
        logger.error('Ошибка при отправке сообщения: %s', e)
        raise exceptions.MessageError(f'Ошибка при отправке сообщения: {e}')


def get_api_answer(timestamp):
    """Проверка эндпоинта на доступности API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=timestamp
        )
    except requests.exceptions.RequestException as e:
        raise exceptions.APIConnectionError(f'Эндпоинт недоступен:{e}')

    if response.status_code != HTTPStatus.OK:
        raise exceptions.EmptyApiResponseError(
            f'Ошибка: API вернул статус {response.status_code}'
        )

    return response.json()


def check_response(response):
    """Проверка ответа на соответствие."""
    if not isinstance(response, dict):
        error_msg = ('Ответ Api не является словарём')
        logger.error(error_msg)
        raise TypeError(error_msg)

    if 'homeworks' not in response:
        error_msg = 'В ответе отсутствует ключ "homeworks"'
        logger.error(error_msg)
        raise exceptions.InvalidAPIResponseError(error_msg)

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        error_msg = 'homeworks не является списком'
        logger.error(error_msg)
        raise TypeError(error_msg)

    if len(homeworks) == 0:
        logger.debug('Новых работ нет')
        return None

    last_homework = homeworks[0]
    return last_homework


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if 'homework_name' not in homework:
        error_msg = 'Отсутствует ключ "homework_name"'
        logger.error(error_msg)
        raise exceptions.HomeworkParseError(error_msg)

    if 'status' not in homework:
        error_msg = 'Отсутствует статус проверки задания'
        logger.error(error_msg)
        raise exceptions.HomeworkParseError(error_msg)

    status = homework.get('status')
    homework_name = homework.get('homework_name')

    if status not in HOMEWORK_VERDICTS:
        logger.error('Неизвестный статус %s', status)
        raise exceptions.HomeworkParseError(f'Неизвестный статус {status}')

    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    missing = check_tokens()
    if missing:
        error_msg = f'Отсутствуют токены: {",".join(missing)}'
        logger.critical(error_msg)
        raise exceptions.MissingTokenError(error_msg)
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error_msg = None

    while True:
        try:
            response = get_api_answer({'from_date': timestamp})
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug('Новых статусов нет')

            last_error_msg = None

        except Exception as e:
            error_msg = f'Сбой в работе программы: {e}'
            logger.critical('Сбой в работе программы: %s', e)

            if error_msg != last_error_msg:
                try:
                    send_message(bot, error_msg)
                    logger.info(
                        'Пользователю было отправлено сообщение с ошибкой %s',
                        error_msg
                    )
                except exceptions.MessageError as send_err:
                    logger.error(
                        'Не удалось отправить сообщение об ошибке %s', send_err
                    )
                last_error_msg = error_msg
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
