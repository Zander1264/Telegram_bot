import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# чтение токена бота из файла и его объявление
with open("../tg_bot_token.txt", "r") as file:
    token = file.readline().strip()
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())


# менеджер для асинхронных сессий
class DatabaseSession:
    def __init__(self, db_path):
        self.db_path = db_path

    async def __aenter__(self):
        self.conn = await aiosqlite.connect(self.db_path)
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()


# инициализация бд
async def init_db():
    async with DatabaseSession("study.db") as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        chat_id TEXT NOT NULL,
                        task TEXT NOT NULL)''')
        await db.commit()

HELP = """
/help - спиоок доступных комманд
/addTask - Добавить задачу для выполнения
/showTasks - Показать список запланированных задач
/delTask - удаления одной задачи пользователя"""


# Состояния диалога
class TaskStates(StatesGroup):
    WAITING_FOR_TASK = State()
    WAITING_FOR_DELETE_NUMBER = State()


# Кнопка отменить
cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Отменить"))


# команда /help
@dp.message_handler(commands=["help"])
async def help(message: types.Message):
    await message.reply(HELP)


# Команда добавить задачу
@dp.message_handler(commands=["addTask"])
async def add_task(message: types.Message):
    await message.reply("Напиши текст задачи, которую хочешь сохранить", reply_markup=cancel_markup)
    await TaskStates.WAITING_FOR_TASK.set()


# Команда показания задач
@dp.message_handler(commands=["showTasks"])
async def show_user_tasks(message: types.Message):
    try:
        tasks = await get_tasks(str(message.chat.id))
        if not tasks:
            await message.reply("У вас пока нет сохранённых задач.", reply_markup=types.ReplyKeyboardRemove())
        else:
            response = "Вот ваши задачи:\n\n"
            for idx, task in enumerate(tasks, start=1):
                response += f"{idx}. {task}\n"
            await message.reply(response)
    except Exception as e:
        await message.reply("Ошибка при загрузке задач", reply_markup=types.ReplyKeyboardRemove())


# команда удаления задачи
@dp.message_handler(commands=["delTask"])
async def del_user_task(message: types.Message):
    try:
        await message.reply("Напиши номер задачи, которую хочешь удалить", reply_markup=cancel_markup)
        await TaskStates.WAITING_FOR_DELETE_NUMBER.set()
    except Exception as e:
        await message.reply("Ошибка при удалении задачи", reply_markup=types.ReplyKeyboardRemove())

# обработчик удаления задачи
@dp.message_handler(state=TaskStates.WAITING_FOR_DELETE_NUMBER)
async def handle_delete(message: types.Message, state: FSMContext):
    if message.text == "Отменить":
        await message.reply("Удаление задачи отменено", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return
    try:
        task_number = int(message.text.strip()) - 1
        chat_id = str(message.chat.id)
        async with DatabaseSession("study.db") as db:
            async with db.execute(
                    "SELECT id, task FROM users WHERE chat_id = ?",
                    (str(chat_id),)
            ) as cursor:
                tasks = await cursor.fetchall()

            if task_number < 0 or task_number >= len(tasks):
                await message.reply("Неверный номер задачи", reply_markup=types.ReplyKeyboardRemove())
                await state.finish()
                return

            task_id = tasks[task_number][0]
            task_text = tasks[task_number][1]

            await db.execute("DELETE FROM users WHERE id = ? AND chat_id = ?", (task_id, chat_id))
            await db.commit()

        await message.reply(f"Задача '{task_text}' удалена", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
    except ValueError:
        await message.reply("Пожалуйста, введите число", reply_markup=cancel_markup)


# получение задач
async def get_tasks(chat_id):
    try:
        async with DatabaseSession("study.db") as db:
            async with db.execute(
                    "SELECT task FROM users WHERE chat_id = ?",
                    (str(chat_id),)
            ) as cursor:
                tasks = await cursor.fetchall()
                return [task[0] for task in tasks]
    except Exception as e:
        await bot.send_message(chat_id, "Ошибка вывода задач.", reply_markup=types.ReplyKeyboardRemove())
        return []


# сохранение задачи
async def save_task(chat_id, task_text):
    try:
        async with DatabaseSession("study.db") as db:
            await db.execute("INSERT INTO users (chat_id, task) VALUES (?, ?)",
                            (chat_id, task_text))
            await db.commit()
    except Exception as e:
        await bot.send_message(chat_id, "Ошибка сохранения задачи.", reply_markup=types.ReplyKeyboardRemove())


# Обработчик ввода задачи
@dp.message_handler(state=TaskStates.WAITING_FOR_TASK)
async def handle_task(message: types.Message, state: FSMContext):
    if message.text == "Отменить":
        await message.reply("Добавление задачи отменено", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return

    # Сохранение задачи в фоне
    asyncio.create_task(save_task(str(message.chat.id), message.text))
    await message.reply("Задача сохранена!", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)


