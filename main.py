import os
import time
from threading import Thread

from pydub import AudioSegment
from pyrebase import pyrebase
from requests import HTTPError
from speech_recognition import Recognizer, AudioFile
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, File
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

from domain.FileUtils import get_config
from domain.StringUtils import return_normal_form, error_to_hint, parse_error_response
from model.dao.DeviceDao import DeviceDao
from model.dao.RootDao import RootDao
from model.dao.UserDao import UserDao
from model.data.Device import Device
from model.data.User import User

config_name, token = 'config.json', '5332578418:AAGXhhCRmXroyGoLpSPK1mEwgNQ909YYJdw'

start_keys = [
    ['/register', '/login'],
    ['/command', '/add']
]

device_keys = [
    ['/start', '/stop']
]

device_action_keys = [
    [InlineKeyboardButton(text="Запуск", callback_data="enable")],
    [InlineKeyboardButton(text="Стоп", callback_data="stop")],
]


def establish_firebase():
    firebase_config = get_config()
    return pyrebase.initialize_app(firebase_config)


firebase = establish_firebase()

dev_dao = DeviceDao(firebase)
usr_dao = UserDao(firebase)
rts_dao = RootDao(firebase)

user = None
chosen_device = None

registering = False
entering = False
inserting = False

voice_id = 0


def start(update, context):
    reply_markup = ReplyKeyboardMarkup(start_keys)
    update.message.reply_text("Бот запущен. Выберите команду.", reply_markup=reply_markup)


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
    registering, inserting, entering = False, False, False

    if user is None:
        update.message.reply_text("Вы не вошли в систему.")
        return

    all_devs = dev_dao.get_by_user(user)
    lst = [InlineKeyboardButton(text=j.name, callback_data=i) for i, j in enumerate(all_devs)]
    keys = [lst[i:i + 2] for i in range(0, len(lst) + 1, 2)]
    inline_keyboard = InlineKeyboardMarkup(keys)
    update.message.reply_text("Доступные вам устройства." if len(all_devs) > 0 else 'У вас нет устройств.',
                              reply_markup=inline_keyboard)


def login(update: Update, context):
    global entering, registering, inserting
    entering, registering, inserting = True, False, False
    update.message.reply_text("Вход. Введите логин и пароль через пробел.")


def register(update: Update, context):
    global registering, entering, inserting
    registering, entering, inserting = True, False, False
    update.message.reply_text("Создание аккаунта. Введите логин и пароль через пробел.")


def handle_voice(update: Update, context: CallbackContext):
    global voice_id
    voice_id += 1
    file: File = context.bot.get_file(update.message.voice.file_id)

    f_name = f"{voice_id}.ogg"
    update.message.reply_text("Подождите...")
    file.download(f_name)
    time.sleep(20)

    try:
        AudioSegment.converter = os.getcwd() + "\\ffmpeg.exe"
        AudioSegment.from_ogg(f_name).export(f"{voice_id}.wav", format='wav')
        analyzer = SpeechOggAudioFileToText()
        update.message.reply_text(analyzer.text)
    except Exception as e:
        update.message.reply_text("Произошла непредвиденная ошибка. Попробуйте позже.")
        print(e)


class SpeechOggAudioFileToText:
    def __init__(self):
        self.recognizer = Recognizer()

    @property
    def text(self):
        global voice_id
        file = f'{voice_id}.wav'

        with AudioFile(file) as source:
            audio = self.recognizer.record(source)

        text = self.recognizer.recognize_google(audio, language='RU')
        return text


def handle_message(update: Update, context):
    global registering, entering, inserting, user

    if registering is False and entering is False and inserting is False:

        if user is None:
            update.message.reply_text("Вы не вошли в систему.")
            return

        text = update.message.text.split()
        for word in text:
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
    global inserting, entering, registering

    if user is None:
        update.message.reply_text("Вы не вошли в систему.")
        return

    inserting, entering, registering = True, False, False
    update.message.reply_text("Введите тип и название прибора.")


def main():
    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("command", command))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("login", login))
    dp.add_handler(CommandHandler("add", add_device))

    dp.add_handler(MessageHandler(Filters.voice, handle_voice))
    dp.add_handler(MessageHandler(Filters.text & ~ Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(device_chooser))

    updater.start_polling()


if __name__ == '__main__':
    main()
