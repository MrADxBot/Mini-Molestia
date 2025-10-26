<<<<<<< HEAD
import telebot
from telebot import types
from dotenv import load_dotenv
import os
import requests
from music import command as command_music

# Создание бота и указание токена
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
bot = telebot.TeleBot(TELEGRAM_TOKEN)

command_music(bot)

@bot.message_handler(commands=['ping'])
def check_ping(message):
    try:
        bot.send_message(message.chat.id, "Бот работает!")
        requests.post(DISCORD_WEBHOOK, data={'content': 'Тест'})
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.channel_post_handler(content_types=['photo'])
def handle_channel_photo(message):
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_data = bot.download_file(file_info.file_path)

        temp_filename = "temp.jpg"
        with open(temp_filename, 'wb') as f:
            f.write(file_data)

        with open(temp_filename, 'rb') as f:
            files = {'file': f}
            requests.post(DISCORD_WEBHOOK, files=files)

        print(f"Фото переслано в Discord ({message.chat.title})")

        os.remove(temp_filename)
    except Exception as e:
        print(f"Ошибка при пересылке: {e}")

print("Бот запущен.")
bot.infinity_polling()
=======
import telebot
from telebot import types
from dotenv import load_dotenv
import os
import requests

# Создание бота и указание токена
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['ping'])
def check_ping(message):
    try:
        bot.send_message(message.chat.id, "Бот работает!")
        requests.post(DISCORD_WEBHOOK, data={'content': 'Тест'})
        bot.send_message(message.chat.id, "Тест")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.channel_post_handler(content_types=['photo'])
def handle_channel_photo(message):
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_data = bot.download_file(file_info.file_path)

        temp_filename = "temp.jpg"
        with open(temp_filename, 'wb') as f:
            f.write(file_data)

        with open(temp_filename, 'rb') as f:
            files = {'file': f}
            requests.post(DISCORD_WEBHOOK, files=files)

        print(f"Фото переслано в Discord ({message.chat.title})")

        os.remove(temp_filename)
    except Exception as e:
        print(f"Ошибка при пересылке: {e}")

print("Бот запущен.")
bot.infinity_polling()
>>>>>>> ede92455bc36fb69e8556018db4d7e06ecc28a5e
