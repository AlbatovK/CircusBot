import json
from typing import List

from pyrebase import pyrebase
from pyrebase.pyrebase import Firebase, PyreResponse
from requests import HTTPError
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

config_name, token = 'config.json', '5303647214:AAFfM1nxeSQw7z259f0Ka_KAUIm_mVpJyCo'

start_keys = [
    ['/register', '/login'],
    ['/command', '/add']
]

device_keys = [
    ['/start', '/stop']
]

data_set = {
    'Кофемашина': 'coffee',
    'Микроволновка': 'microwave',
    'Стиральная Машинка': 'washing'
}

device_action_keys = [
    [InlineKeyboardButton(text="Запуск", callback_data="enable")],
    [InlineKeyboardButton(text="Стоп", callback_data="stop")],
]


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

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def get_all(self):
        users = self.db.child("users").get()
        return ObjectMapper.parse_users(users) if users.each() is not None else []

    def insert(self, user: User):
        user_dict = user.__dict__
        self.db.child("users").push(user_dict)


class DeviceDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def update_device_status(self, device: Device, active: bool):
        update_dict = {"active": True if active else False}
        self.db.child("devices").child(device.name).update(update_dict)

    def get_all(self):
        devices = self.db.child("devices").get()
        return ObjectMapper.parse_devices(devices) if devices.each() is not None else []

    def get_by_user(self, user: User):
        return [d for d in self.get_all() if user.login in d.users_id]

    def insert(self, device: Device):
        device_dict = device.__dict__
        self.db.child("devices").child(device.name).set(device_dict)


def get_config() -> str:
    with open(config_name, 'r') as config_file:
        return parse_from_file(config_file)


def parse_from_file(read_file) -> str:
    return json.load(read_file)


def establish_firebase():
    firebase_config = get_config()
    return pyrebase.initialize_app(firebase_config)


firebase = establish_firebase()
dev_dao = DeviceDao(firebase)
usr_dao = UserDao(firebase)
user = None


def start(update, context):
    reply_markup = ReplyKeyboardMarkup(start_keys)
    update.message.reply_text("Бот запущен. Выберите команду.", reply_markup=reply_markup)


chosen_device = None


def device_chooser(update: Update, context: CallbackContext):
    global chosen_device, user

    query = update.callback_query
    choice = query.data
    query.answer()

    if user is None:
        return

    keyboard = InlineKeyboardMarkup(device_action_keys)
    all_dev = dev_dao.get_by_user(user)

    for i, j in enumerate(all_dev):
        if choice == str(i):
            query.edit_message_text("Вы выбрали " + j.name, reply_markup=keyboard)
            chosen_device = j
            return

    if chosen_device is None:
        return

    if choice == 'enable':
        if chosen_device.active is False:
            dev_dao.update_device_status(chosen_device, True)
            chosen_device.active = True
            query.edit_message_text(chosen_device.name + " запущен", reply_markup=keyboard)
        else:
            query.edit_message_text(chosen_device.name + " уже запущен на данный момент.", reply_markup=keyboard)
    elif choice == 'stop':
        if chosen_device.active is True:
            dev_dao.update_device_status(chosen_device, False)
            chosen_device.active = False
            query.edit_message_text(chosen_device.name + " остановлен.", reply_markup=keyboard)
        else:
            query.edit_message_text(chosen_device.name + " уже остановлен на данный момент.", reply_markup=keyboard)


def command(update: Update, context):
    if user is None:
        update.message.reply_text("Вы не вошли в систему.")
        return

    all_devs = dev_dao.get_by_user(user)
    lst = [InlineKeyboardButton(text=j.name, callback_data=i) for i, j in enumerate(all_devs)]
    keys = [lst[i:i + 2] for i in range(0, len(lst) + 1, 2)]
    inline_keyboard = InlineKeyboardMarkup(keys)
    update.message.reply_text("Выберите устройство.", reply_markup=inline_keyboard)


hint_dict = {
    "INVALID_EMAIL": "Некорректный логин",
    "INVALID_PASSWORD": "Некорректный пароль",
    "MISSING_PASSWORD": "Необходимо ввести пароль",
    "EMAIL_NOT_FOUND": "Учётной записи с таким логином не существует",
    "WEAK_PASSWORD": "Пароль должен быть как минимум 6 символов",
    "EMAIL_EXISTS": "Учётная запись с таким логином уже существует",
    "INVALID_CONNECTION": "Проблемы с сетью. Проверьте подключение",
}

registering = False
entering = False
inserting = False


def login(update: Update, context):
    global entering, registering, inserting
    entering = True
    registering = False
    inserting = False

    update.message.reply_text("Вход. Введите логин и пароль через пробел.")


def register(update: Update, context):
    global registering, entering, inserting
    registering = True
    entering = False
    inserting = False

    update.message.reply_text("Создание аккаунта. Введите логин и пароль через пробел.")


def error_to_hint(err_str: str) -> str:
    return hint_dict.get(err_str, "Неизвестная ошибка")


def parse_error_response(e: HTTPError):
    return str(e.errno).split()[0], json.loads(e.strerror)["error"]["message"].split()[0]


def handle_message(update: Update, context):
    global registering, entering, user, inserting

    if registering is False and entering is False and inserting is False:
        update.message.reply_text("Не используется ни одна команда. Выберите из списка.")
        return

    if inserting is True:
        name = update.message.text
        dev_dao.insert(Device(name, [user.login], False))
        inserting = False
        update.message.reply_text("Прибор " + name + " зарегистрирован.")
        return

    if entering is True:
        email, usr_login = update.message.text.split()[0], update.message.text.split()[1]
        auth = firebase.auth()

        try:
            fb_usr = auth.sign_in_with_email_and_password(email + "@gmail.com", usr_login)
            fb_usr = auth.refresh(fb_usr['refreshToken'])
            print(fb_usr)
            entering = False
        except HTTPError as e:
            code, msg = parse_error_response(e)
            update.message.reply_text(error_to_hint(msg) + ". Попробуйте ввести данные ещё раз.")
            return

        user = User(email)
        update.message.reply_text("Пользователь " + user.login + " успешно вошёл.")
        return

    email, usr_login = update.message.text.split()[0], update.message.text.split()[1]
    auth = firebase.auth()
    try:
        fb_usr = auth.create_user_with_email_and_password(email + "@gmail.com", usr_login)
        fb_usr = auth.refresh(fb_usr['refreshToken'])
        print(fb_usr)
    except HTTPError as e:
        code, msg = parse_error_response(e)
        update.message.reply_text(error_to_hint(msg) + ". Попробуйте ввести данные ещё раз.")
        return

    user = User(email)
    update.message.reply_text("Пользователь " + user.login + " успешно зарегистрирован.")
    registering = False


def add_device(update: Update, context):
    global inserting

    if user is None:
        update.message.reply_text("Вы не вошли в систему.")
        return

    inserting = True
    update.message.reply_text("Введите название прибора.")


def main():
    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("command", command))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("login", login))
    dp.add_handler(CommandHandler("add", add_device))

    dp.add_handler(MessageHandler(Filters.text & ~ Filters.command, handle_message))

    updater.dispatcher.add_handler(CallbackQueryHandler(device_chooser))

    updater.start_polling()


if __name__ == '__main__':
    main()
