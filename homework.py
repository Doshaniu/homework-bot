"""Бот для проверки статуса домашнего задания."""
import logging
import os
import time

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
STATUS_LIST = ['approved', 'reviewing', 'rejected']


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('main.log'),
        logging.StreamHandler()
    ]
)


def check_tokens():
    """Проверка правильности и доступности токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing = []
    for name, value in tokens.items():
        if value:
            logging.info(f'Токен {name} - OK')
        else:
            logging.critical(f'Токен {name} - ОТСУТСТВУЕТ!')
            missing.append(name)
    if missing:
        raise exceptions.MissingTokenError(
            f'Отсутвуют токены {", ".join(missing)}'
        )


def send_message(bot, message):
    """Отправка сообщения в телеграм при смене статуса."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено {message}')
    except Exception as e:
        logging.error(f'Ошибка при отправке сообщения: {e}')


def get_api_answer(timestamp):
    """Проверка эндпоинта на доступности API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=timestamp
        )
    except requests.exceptions.RequestException as e:
        error_msg = f'Эндпоинт недоступен:{e}'
        logging.error(error_msg)
        raise ConnectionError(error_msg)

    if response.status_code != 200:
        error_msg = f'Ошибка: API вернул статус {response.status_code}'
        logging.error(error_msg)
        raise Exception(error_msg)

    return response.json()


def check_response(response):
    """Проверка ответа на соответствие."""
    if not isinstance(response, dict):
        error_msg = ('Ответ Api не является словарём')
        logging.error(error_msg)
        raise TypeError(error_msg)

    if 'homeworks' not in response:
        error_msg = 'В ответе отсутствует ключ "homeworks"'
        logging.error(error_msg)
        raise KeyError(error_msg)

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        error_msg = 'homeworks не является списком'
        logging.error(error_msg)
        raise TypeError(error_msg)

    if len(homeworks) == 0:
        logging.debug('Новых работ нет')
        return None

    last_homework = homeworks[0]
    return last_homework


def parse_status(homework):
    """Проверка статуса домашней работы."""
    try:
        status = homework.get('status')
        homework_name = homework.get('homework_name')

        if homework_name is None:
            error_msg = 'Отсутствует ключ "homework_name"'
            logging.error(error_msg)
            raise AssertionError(error_msg)

        if status not in STATUS_LIST:
            error_msg = 'Отсутствует статус проверки задания'
            logging.error(error_msg)
            raise ValueError(error_msg)

        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as e:
        logging.error(f'Ошибка {e}')
        raise


def main():
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error_msg = None
    check_tokens()

    while True:
        try:
            response = get_api_answer({'from_date': timestamp})
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.debug('Новых статусов нет')

            last_error_msg = None

        except Exception as e:
            error_msg = f'Сбой в работе программы: {e}'
            logging.critical(error_msg)

            if error_msg != last_error_msg:
                try:
                    send_message(bot, error_msg)
                    logging.info(
                        'Пользователю было отправлено сообщение с ошибкой'
                        f'{error_msg}'
                    )
                except Exception as send_err:
                    logging.error(
                        f'Не удалось отправить сообщение об ошибке{send_err}'
                    )
                last_error_msg = error_msg
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
