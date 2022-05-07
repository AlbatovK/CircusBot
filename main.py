import json
import time
from threading import Thread
from typing import List

import pymorphy2
from pyrebase import pyrebase
from pyrebase.pyrebase import Firebase, PyreResponse
from requests import HTTPError
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

config_name, token = 'config.json', '5332578418:AAGXhhCRmXroyGoLpSPK1mEwgNQ909YYJdw'

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

    def __init__(self, lgn: str):
        self.login = lgn


class Device:

    def __init__(self, name: str, tp, users_id: List[str], active):
        self.name = name
        self.tp = tp
        self.users_id = users_id
        self.active = active


class Root:

    def __init__(self, name, actions):
        self.name = name
        self.actions = actions


class ObjectMapper:

    @staticmethod
    def parse_devices(response: PyreResponse) -> List[Device]:
        def parse_single(item: PyreResponse):
            return Device(item.val()['name'], item.val()['tp'], item.val()['users_id'], item.val()['active'])

        map_query = map(parse_single, response.each())
        return list(map_query)

    @staticmethod
    def parse_users(response: PyreResponse) -> List[User]:
        def parse_single(item: PyreResponse):
            return User(item.val()['login'])

        map_query = map(parse_single, response.each())
        return list(map_query)

    @staticmethod
    def parse_roots(response: PyreResponse) -> List[Root]:
        def parse_single(item: PyreResponse):
            return Root(item.val()['name'], item.val()['actions'])

        map_query = map(parse_single, response.each())
        return list(map_query)


class UserDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def get_all(self):
        users = self.db.child("users").get()
        return ObjectMapper.parse_users(users) if users.each() is not None else []

    def insert(self, usr: User):
        user_dict = usr.__dict__
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

    def get_by_user(self, usr: User):
        return [d for d in self.get_all() if usr.login in d.users_id]

    def insert(self, device: Device):
        device_dict = device.__dict__
        self.db.child("devices").child(device.name).set(device_dict)


class RootDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def insert(self, root: Root):
        root_dict = root.__dict__
        self.db.child("device_root").child(root.name).set(root_dict)

    def get_all(self) -> List[Root]:
        roots = self.db.child("device_root").get()
        return ObjectMapper.parse_roots(roots) if roots.each() is not None else []

    def get_by_name(self, name: str):
        return [x for x in self.get_all() if x.name == name]


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
rts_dao = RootDao(firebase)
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
            query.edit_message_text(
                "Вы выбрали " + j.name + '. Прибор ' + ('бездействует.' if not j.active else 'активен.'),
                reply_markup=keyboard)
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
    global registering, entering, inserting
    registering = False
    entering = False
    inserting = False

    if user is None:
        update.message.reply_text("Вы не вошли в систему.")
        return

    all_devs = dev_dao.get_by_user(user)
    lst = [InlineKeyboardButton(text=j.name, callback_data=i) for i, j in enumerate(all_devs)]
    keys = [lst[i:i + 2] for i in range(0, len(lst) + 1, 2)]
    inline_keyboard = InlineKeyboardMarkup(keys)
    update.message.reply_text("Доступные вам устройства." if len(all_devs) > 0 else 'У вас нет устройств.',
                              reply_markup=inline_keyboard)


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


spec_words = {
    "ВНИМАНИЕ! Вы использовали слова 'база' или 'кринж' в диалоге с ботом! " +
    "Вы разочаровать партию! Партия забрать у вас кошка-жена!": ['база', 'кринж']
}

morph = pymorphy2.MorphAnalyzer()


def return_normal_form(word):
    return morph.parse(word)[0].normal_form


def handle_message(update: Update, context):
    global registering, entering, inserting, user

    if registering is False and entering is False and inserting is False:

        if user is None:
            update.message.reply_text("Вы не вошли в систему.")
            return

        text = update.message.text.split()
        for word in text:

            for key, list_special_word in spec_words.items():
                if word.lower() in list_special_word:
                    update.message.reply_text(key)
                    return

            for d in dev_dao.get_by_user(user):
                if return_normal_form(word) in rts_dao.get_by_name(d.tp.lower())[0].actions:
                    def async_write():
                        update.message.reply_text(d.name + ' выполняет вашу просьбу.')
                        time.sleep(5)
                        update.message.reply_text("Всё готово.")

                    Thread(target=async_write).run()
                    return

        update.message.reply_text('Ваша команда не может быть выполнена с вашими устройствами.')
        return

    if inserting is True:
        tp, name = update.message.text.split()[0], update.message.text.split()[1]

        if tp.lower() not in map(lambda x: x.name, rts_dao.get_all()):
            update.message.reply_text("Данный вид техники не поддерживается.")
            return

        dev_dao.insert(Device(name, tp, [user.login], False))
        inserting = False

        def async_write():
            update.message.reply_text("Соединяю вас и " + name)
            time.sleep(2)
            update.message.reply_text("Привет. Готов служить вам.")

        Thread(target=async_write).run()
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
        usr_dao.insert(User(email))
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
    update.message.reply_text("Введите тип и название прибора.")


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
