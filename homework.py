import locale
import os
import time
import telegram
import requests
import logging

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)


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


class APIException(Exception):
    """Класс для обработки API."""

    ...


def check_tokens(*keys):
    """Проверяем доступность переменных окружения."""
    tokens = []
    for key in keys:
        token = os.getenv(key)
        if token is None:
            logger.critical(f'Не передано значение для переменной окружения:'
                            f'{key}')
            exit(1)
        tokens.append(token)
    return tokens


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение "{message}" успешно отправлено в Телеграм')
    except telegram.TelegramError as e:
        logger.error(f'Ошибка при отправке сообщения: {e}')
        raise APIException('Ошибка при отправке сообщения в Телеграм.') from e


def get_api_answer(timestamp):
    """Делаем запрос к единственному эндпоинту API-сервиса."""
    params = {
        'from_date': timestamp,
        'to_date': int(time.time())
    }
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
        if response.status_code != 200:
            raise APIException(f'Ошибка при запросе к API:'
                               f'{response.status_code}')
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f'Ошибка при запросе к API: {e}')
        raise APIException('Ошибка при запросе к API.') from e


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if 'error' in response:
        raise APIException(f"Ошибка при получении данных API:"
                           f"{response['error']}")
    if not isinstance(response, dict):
        raise TypeError("Ответ API не представлен в виде словаря")
    if 'homeworks' not in response:
        raise APIException("В ответе API отсутствует ключ 'homeworks'")
    if not isinstance(response['homeworks'], list):
        raise TypeError("Данные о домашней работе не представлены в виде"
                        "списка")
    if not response['homeworks']:
        raise APIException("В ответе API отсутствуют данные о домашней работе")
    for homework in response['homeworks']:
        if 'status' not in homework:
            raise APIException("В ответе API отсутствует ключ 'status' для"
                               "домашней работы")
        status = homework['status']
        if status not in HOMEWORK_VERDICTS:
            raise APIException(f"Некорректный статус домашней работы:{status}")
    return True


def parse_status(homework):
    """Извлекаем статус домашней работы."""
    status = homework.get("status")
    homework_name = homework.get("homework_name")
    if not homework_name:
        raise ValueError("Отсутствует ключ 'homework_name' в ответе API")
    if status:
        if status in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS[status]
            return (
                f'Изменился статус проверки работы "{homework_name}".'
                f'{verdict}'
            )
        else:
            raise ValueError("Недокументированный статус домашней работы.")
    else:
        raise ValueError("Отсутствует ключ 'status' в ответе API.")


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Отсутствует обязательная переменная окружения. '
                        'Программа принудительно остановлена.')
        raise SystemExit
    logger.debug('Бот запущен')
    try:
        check_tokens()
    except ValueError as e:
        logger.error(f'Ошибка при проверке токенов: {e}')
        exit(0)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        response = get_api_answer(timestamp)
        if response:
            try:
                check_response(response)
                homeworks = response['homeworks']
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            except APIException as e:
                logger.error(f'Ошибка API: {e}')
        timestamp = response['current_date']
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
