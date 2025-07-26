import os
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from user_repository import UserRepository, init_db

# чтение токена бота из файла и его объявление
with open("../tg_bot_token.txt", "r") as file:
    token = file.readline().strip()
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())

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
        repo = UserRepository()
        tasks = await repo.get_user_tasks(chat_id=str(message.chat.id) )
        if not tasks:
            await message.reply("У вас пока нет сохранённых задач.", reply_markup=types.ReplyKeyboardRemove())
        else:
            response = "Вот ваши задачи:\n\n"
            for idx, task in enumerate(tasks, start=1):
                response += f"{idx}. {task}\n"
            await message.reply(response)
    except Exception as e:
        print(e)
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
        repo = UserRepository()
        task_number = int(message.text.strip())
        success, result = await repo.delete_user_task(str(message.chat.id), task_number)

        if not success:
            await message.reply(result, reply_markup=cancel_markup)
        else:
            await message.reply(f"Задача '{result}' удалена", reply_markup=types.ReplyKeyboardRemove())
            await state.finish()

    except ValueError:
        await message.reply("Пожалуйста, введите число", reply_markup=cancel_markup)


# Обработчик ввода задачи
@dp.message_handler(state=TaskStates.WAITING_FOR_TASK)
async def handle_task(message: types.Message, state: FSMContext):
    if message.text == "Отменить":
        await message.reply("Добавление задачи отменено", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return
    try:
        repo = UserRepository()
        success, result = await repo.add_user_task(str(message.chat.id), message.text)
    except Exception as e:
        await bot.send_message(message.chat.id, "Ошибка сохранения задачи.", reply_markup=types.ReplyKeyboardRemove())
    finally:
        if not success:
            await bot.send_message(message.chat.id, result, reply_markup=cancel_markup)
            return
        else:
            await bot.send_message(message.chat.id, result, reply_markup=types.ReplyKeyboardRemove())
            await state.finish()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)
