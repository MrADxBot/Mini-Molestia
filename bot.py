import telebot
from telebot import types
from dotenv import load_dotenv
import os
import requests
from commands.music import command as command_music
from commands.webmtomp4 import command as command_convert

# Создание бота и указание токена
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
bot = telebot.TeleBot(TELEGRAM_TOKEN)

#Блок дополнительных команд
command_music(bot)
command_convert(bot)

#Блок основных команд
@bot.message_handler(commands=['ping'])
def check_ping(message):
    try:
        bot.send_message(message.chat.id, "Бот работает!")
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

        caption = message.caption or ""

        with open(temp_filename, 'rb') as f:
            files = {'file': f}
            data = {
                'content': caption
            }
            requests.post(DISCORD_WEBHOOK, files=files, data=data)

        print(f"Фото переслано в Discord ({message.chat.title})")

        os.remove(temp_filename)
    except Exception as e:
        print(f"Ошибка при пересылке: {e}")

print("Бот запущен.")
bot.infinity_polling()
