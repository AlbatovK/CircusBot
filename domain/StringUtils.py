import json

import pymorphy2
from requests import HTTPError

hint_dict = {
    "INVALID_EMAIL": "Некорректный логин",
    "INVALID_PASSWORD": "Некорректный пароль",
    "MISSING_PASSWORD": "Необходимо ввести пароль",
    "EMAIL_NOT_FOUND": "Учётной записи с таким логином не существует",
    "WEAK_PASSWORD": "Пароль должен быть как минимум 6 символов",
    "EMAIL_EXISTS": "Учётная запись с таким логином уже существует",
    "INVALID_CONNECTION": "Проблемы с сетью. Проверьте подключение",
}

morph = pymorphy2.MorphAnalyzer()


def return_normal_form(word):
    return morph.parse(word)[0].normal_form


def parse_error_response(e: HTTPError):
    return str(e.errno).split()[0], json.loads(e.strerror)["error"]["message"].split()[0]


def error_to_hint(err_str: str) -> str:
    return hint_dict.get(err_str, "Неизвестная ошибка")
