import json
import time
from typing import List

from pyrebase import pyrebase
from pyrebase.pyrebase import Firebase, PyreResponse
from telegram import InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

config_name, token = 'config.json', '5303647214:AAFfM1nxeSQw7z259f0Ka_KAUIm_mVpJyCo'

data_set = {
    'Coffee': 'coffee',
    'Microwave': 'microwave',
}

reply_keyboard = [
    ['/register', '/a'],
    ['/b', '/c']
]

key_objs = [InlineKeyboardButton(text=key, callback_data=val) for key, val in data_set.items()]
keys = [key_objs[i:i + 2] for i in range(0, len(key_objs) + 1, 2)]

markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
keyboard = InlineKeyboardMarkup(keys)


def get_config() -> str:
    with open(config_name, 'r') as config_file:
        return parse_from_file(config_file)


def parse_from_file(read_file) -> str:
    return json.load(read_file)


def establish_firebase():
    firebase_config = get_config()
    return pyrebase.initialize_app(firebase_config)


class User:

    def __init__(self, login: str):
        self.login = login


class Device:

    def __init__(self, name: str, users_id: List[str], active):
        self.name = name
        self.users_id = users_id
        self.active = active


class ObjectMapper:

    @staticmethod
    def parse_devices(response: PyreResponse) -> List[Device]:
        def parse_single(item: PyreResponse):
            return Device(item.val()['name'], item.val()['users_id'], item.val()['active'])

        map_query = map(parse_single, response.each())
        return list(map_query)

    @staticmethod
    def parse_users(response: PyreResponse) -> List[User]:
        def parse_single(item: PyreResponse):
            return User(item.val()['login'])

        map_query = map(parse_single, response.each())
        return list(map_query)


class UserDao:

    def __init__(self, firebase: Firebase):
        self.db = firebase.database()

    def get_all(self):
        users = self.db.child("users").get()
        return ObjectMapper.parse_users(users) if users.each() is not None else []

    def insert(self, user: User):
        user_dict = user.__dict__
        self.db.child("users").push(user_dict)


class DeviceDao:

    def __init__(self, firebase: Firebase):
        self.db = firebase.database()

    def get_all(self):
        devices = self.db.child("devices").get()
        return ObjectMapper.parse_devices(devices) if devices.each() is not None else []

    def get_by_user(self, user: User):
        return [d for d in self.get_all() if user.login in d.users_id]

    def insert(self, device: Device):
        device_dict = device.__dict__
        self.db.child("devices").push(device_dict)


def start(update, context):
    update.message.reply_text("Выберите устройство.")


def help(update, context):
    update.message.reply_text("Я бот справочник.")


def address(update, context):
    update.message.reply_text("Адрес: г. Москва, ул. Льва Толстого, 16", reply_markup=markup)


def phone(update, context):
    update.message.reply_text("Выберите устройство.", reply_markup=keyboard)


def site(update, context):
    update.message.reply_text(
        "Сайт: https://github.com/CondInPunz/SunLust", reply_markup=markup)


def work_time(update, context):
    update.message.reply_text("Начинаю стирать.")
    time.sleep(3)
    update.message.reply_text("Кофе готов!")


def echo(update, context):
    update.message.reply_text(update.message.text)


def main():
    firebase = establish_firebase()
    dev_dao = DeviceDao(firebase)
    usr_dao = UserDao(firebase)

    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~ Filters.command, echo))
    dp.add_handler(CommandHandler("register", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("address", address))
    dp.add_handler(CommandHandler("phone", phone))
    dp.add_handler(CommandHandler("site", site))
    dp.add_handler(CommandHandler("work_time", work_time))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
