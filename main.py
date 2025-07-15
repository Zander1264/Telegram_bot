import telebot
import os

with open("../tg_bot_token.txt", "r") as file:
    token = file.readline()
bot = telebot.TeleBot(token)

@bot.message_handler(content_types=["text"])
def echo(message):
    bot.send_message(message.chat.id, message.text)








# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    bot.polling(none_stop=True)

