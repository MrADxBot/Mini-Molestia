import telebot
from telebot import types
from dotenv import load_dotenv
import os
import requests
import json
from commands.music import command as command_music
from commands.webmtomp4 import command as command_convert

# Создание бота и указание токена
load_dotenv(".env") 
# load_dotenv(".env.test", override=True)  
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

def send_to_discord(content="", file_payload=None):
    data = {'content': content}
    if file_payload:
        requests.post(DISCORD_WEBHOOK, data=data, files={'file': file_payload})
    else:
        requests.post(DISCORD_WEBHOOK, data=data)


@bot.channel_post_handler(content_types=['text', 'photo', 'document', 'video'])
def handle_channel_post(message):
    try:
        text = message.text or message.caption or ""

        if message.content_type == 'text':
            send_to_discord(content=text)
            print(f"Сообщение переслано в Discord ({message.chat.title})")
            return

        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            file_data = bot.download_file(file_info.file_path)
            filename = f"photo_{message.message_id}.jpg"
            send_to_discord(content=text, file_payload=(filename, file_data, 'image/jpeg'))
            print(f"Фото переслано в Discord ({message.chat.title})")
            return

        if message.content_type == 'document':
            # Не дублируем обработку webm: этим занимается отдельная команда.
            if message.document and message.document.mime_type == 'video/webm':
                return

            file_info = bot.get_file(message.document.file_id)
            file_data = bot.download_file(file_info.file_path)
            filename = message.document.file_name or f"file_{message.message_id}"
            mime_type = message.document.mime_type or 'application/octet-stream'
            send_to_discord(content=text, file_payload=(filename, file_data, mime_type))
            print(f"Файл переслан в Discord ({message.chat.title})")
            return

        if message.content_type == 'video':
            file_info = bot.get_file(message.video.file_id)
            file_data = bot.download_file(file_info.file_path)
            filename = f"video_{message.message_id}.mp4"
            send_to_discord(content=text, file_payload=(filename, file_data, 'video/mp4'))
            print(f"Видео переслано в Discord ({message.chat.title})")
            return
    except Exception as e:
        print(f"Ошибка при пересылке: {e}")

print("Бот запущен.")
bot.infinity_polling()
