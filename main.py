import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from contextlib import contextmanager

# чтение токена бота из файла и его объявление
with open("../tg_bot_token.txt", "r") as file:
    token = file.readline().strip()
bot = Bot(token=token)
dp = Dispatcher(bot)


# инициализация бд
def init_db():
    conn = sqlite3.connect('study.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        chat_id TEXT NOT NULL,
                        task TEXT NOT NULL)''')
    conn.commit()
    conn.close()


HELP = """
/help - спиоок доступных комманд
/addTask - Добавить задачу для выполнения
/showTasks - Показать список запланированных задач"""


# Состояния диалога
class TaskStates(StatesGroup):
    WAITING_FOR_TASK = State()


def get_db_connection():
    return sqlite3.connect('study.db', check_same_thread=False)

@contextmanager
def db_session():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

# Кнопка отменить
cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Отменить"))


# Команда показания задач
@dp.message_handler(commands=["showTasks"])
async def show_tasks(message: types.Message):
    chat_id = str(message.chat.id)
    try:
        # Подключение к БД
        conn = sqlite3.connect('study.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        # Получаем задачи пользователя
        cursor.execute("SELECT task FROM users WHERE chat_id = ?", (chat_id,))
        tasks = cursor.fetchall()

        if not tasks:
            await message.reply("У вас нет запланированных задач.")
        else:
            response = "Вот все ваши запланированные задачи: \n\n"
            for idx, task in enumerate(tasks, start=1):
                response += f"{idx}. {task[0]}\n"
            await message.reply(response)

    except Exception as e:
        await message.reply(f"Ошибка при зарузке задач: {str(e)}")
    finally:
        conn.close()


# команда /help
@dp.message_handler(commands=["help"])
async def help(message: types.Message):
    await message.reply(HELP)


# Команда добавить задачу
@dp.message_handler(commands=["addTask"])
async def add_task(message: types.Message):
    await message.reply("Напиши текст задачи, которую хочешь сохранить", reply_markup=cancel_markup)
    await TaskStates.WAITING_FOR_TASK.set()


# Обработчик ввода задачи
@dp.message_handler(state=TaskStates.WAITING_FOR_TASK)
async def save_task(message: types.Message, state: FSMContext):
    if message.text == "Отменить":
        await message.reply("Добавление задачи отменено", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return

    try:
        conn = sqlite3.connect('study.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute('''
            INSERT INTO users (chat_id, task)
            VALUES (?, ?)
        ''', (str(message.chat.id), message.text))
        conn.commit()
        await message.reply(f"Задача сохранена!", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        await message.reply(f"Ошибка сохранения: {str(e)}", reply_markup=types.ReplyKeyboardRemove())
    finally:
        conn.close()
        await state.finish()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    init_db()
    from aiogram.contrib.fsm_storage.memory import MemoryStorage
    dp.storage = MemoryStorage()
    executor.start_polling(dp, skip_updates=True)
