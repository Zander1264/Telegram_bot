import telebot
import os
import sqlite3

with open("../tg_bot_token.txt", "r") as file:
    token = file.readline()
bot = telebot.TeleBot(token)

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
/add-task - Добавить задачу для выполнения"""

# Состояния диалога
class TaskStates:
    WAITING_FOR_TASK = 1

# Хранилище состояний (можно использовать глобальную переменную для простоты)
user_states = {}



# #фильтр обработки сообщений(декоратор)
# @bot.message_handler(content_types=["text"])
# def echo(message):
#     bot.send_message(message.chat.id, message.text)

@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, HELP)

@bot.message_handler(commands=["add-task"])
def add_task(message):
    # Сохраняем состояние ожидания ввода задачи
    user_states[message.from_user.id] = TaskStates.WAITING_FOR_TASK
    
    # Создаем клавиатуру с кнопкой отмены
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Отменить"))
    
    bot.send_message(
        message.chat.id,
        "Напишите текст задачи",
        reply_markup=markup
    )

# Обработчик ввода задачи
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == TaskStates.WAITING_FOR_TASK)
def save_task(message):
    if message.text == "Отменить":
        bot.reply_to(message, "Добавление задачи отменено")
        del user_states[message.from_user.id]
        return
        
    try:
        conn = sqlite3.connect('study.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (chat_id, task)
            VALUES (?, ?)
        ''', (str(message.chat.id), message.text))
        conn.commit()
        
        bot.reply_to(message, f"Задача сохранена! ID чата: {message.chat.id}")
        del user_states[message.from_user.id]
    except Exception as e:
        bot.reply_to(message, f"Ошибка сохранения: {str(e)}")
    finally:
        conn.close()



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    init_db()
    #постоянно обращается к серверам телеграм
    bot.polling(none_stop=True)

