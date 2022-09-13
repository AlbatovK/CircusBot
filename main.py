from pyrebase import pyrebase
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

from domain.FileUtils import get_config
from model.dao.TaskDao import TaskDao
from model.dao.UserDao import UserDao
from model.data.User import User

config_name, token = 'config.json', '5332578418:AAGXhhCRmXroyGoLpSPK1mEwgNQ909YYJdw'
start_keys = [['/info', '/answer'], ['/balance']]
usr_state_mp = {}

firebase_config = get_config()
firebase = pyrebase.initialize_app(firebase_config)
task_dao = TaskDao(firebase)
usr_dao = UserDao(firebase)

second_time_txt = "Добро пожаловать! Если забыл правила, можешь освежить память, нажав /info."
first_time_txt = "Ты здесь в первый раз, да? Если что-то непонятно, нажми /info. Удачи!"

info = '''
Вас приветствует бот помощник клоунов 11Б🤡
С его помощью вы можете взаимодействовать с нашей одноименной валютой Б-коинами🤑, а именно: зарабатывать Б-коины за ответы на вопросы✏,
проверять личный баланс💰
Совсем скоро мы опубликуем список призов, которые возможно получить, обменивая валюту, так что следите за новостями!🦊

Stonks📈

1. подсказка: если хотите узнать количество человек в 11Б, то спросите у ученика с красным носом, он с радостью вам ответит!🤓

2.подсказка: для второго задания следует писать все 10 слов с маленькой буквы через пробел без точек и цифр!😧
'''


def start(update, context):
    print(context)
    reply_markup = ReplyKeyboardMarkup(start_keys)
    update.message.reply_text("Бот запущен. Выберите команду.", reply_markup=reply_markup)


def information(update: Update, context):
    print(context)
    update.message.reply_text(info)


def tasks_chooser(update: Update, context: CallbackContext):
    print(context)

    usr = [x for x in usr_dao.get_all() if x.user_id == update.callback_query.from_user.id][0]
    query = update.callback_query
    task = [t for t in task_dao.get_all() if int(query.data) == t.task_id][0]
    usr_state_mp[usr.user_id] = task

    query.answer()
    query.edit_message_text(f"Вопрос - {task.description}" + "\n" + "Напишите ваш ответ")


def handle_plain(update: Update, context):
    print(context)

    users = [x for x in usr_dao.get_all() if x.user_id == update.message.from_user.id]
    if not users:
        update.message.reply_text("Нажми /info или /answer чтобы войти в курс дела!")
        return

    usr = users[0]
    task = usr_state_mp.get(usr.user_id, None)
    if task is None:
        update.message.reply_text("Выберите вопрос, на котороый хотите ответить, нажав /info!")
        return

    if update.message.text.lower() == task.answer.lower():
        update.message.reply_text("Отлично! Вы правильно ответили на вопрос! Ваш баланс увеличился!")
        task_dao.increment_task_answered(task)
        usr.score += 10
        usr_dao.do_task(usr, task)

        usr_state_mp[usr.user_id] = None
        return

    usr_state_mp[usr.user_id] = None
    update.message.reply_text("Неправильный ответ... Попробуй ещё раз!")
    print(task.answer)


def answer(update: Update, context):
    print(context)
    users = usr_dao.get_all()
    usr: User

    if update.message.from_user.id not in [x.user_id for x in users]:
        tg_usr = update.message.from_user
        db_usr = User(tg_usr.id, 0, tg_usr.name, tg_usr.full_name)
        usr_dao.insert(db_usr)
        welcome_txt = first_time_txt
        usr = db_usr
    else:
        welcome_txt = second_time_txt
        usr = [x for x in users if x.user_id == update.message.from_user.id][0]

    done_tasks_ids = [x.task_id for x in usr_dao.get_done_tasks(usr)]
    tasks = [t for t in task_dao.get_all() if t.task_id not in done_tasks_ids]

    lst = [InlineKeyboardButton(text=j.description, callback_data=j.task_id) for i, j in enumerate(tasks)]
    keys = [lst[i:i + 1] for i in range(0, len(lst))]
    inline_keyboard = InlineKeyboardMarkup(keys)

    text = welcome_txt + "\n" * 2 + "Вот список доступных вопросов." if len(tasks) > 0 else 'Вы выполнили все задания.'
    update.message.reply_text(text, reply_markup=inline_keyboard)


def balance(update: Update, context):
    print(context)
    users = [x for x in usr_dao.get_all() if x.user_id == update.message.from_user.id]
    if not users:
        update.message.reply_text("Вас нет в списке участников игры. Нажмите /answer, чтобы поучаствовать.")
    else:
        usr = users[0]
        text = f"{usr.name}, id = {usr.user_id}, баланс = {usr.score}"
        update.message.reply_text(text)


def main():
    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("answer", answer))
    dp.add_handler(CommandHandler("info", information))
    dp.add_handler(CommandHandler("balance", balance))

    message_filter = Filters.text & ~ Filters.command
    dp.add_handler(MessageHandler(message_filter, handle_plain))
    dp.add_handler(CallbackQueryHandler(tasks_chooser))
    updater.start_polling()


if __name__ == '__main__':
    main()
