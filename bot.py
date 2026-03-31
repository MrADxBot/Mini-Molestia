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

CHANNEL_CONTENT_TYPES = [
    'text',
    'audio',
    'document',
    'photo',
    'sticker',
    'video',
    'video_note',
    'voice',
    'animation',
    'contact',
    'location',
    'venue',
    'poll',
]

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


def get_message_author(message):
    if getattr(message, 'author_signature', None):
        return message.author_signature

    if getattr(message, 'from_user', None):
        full_name = " ".join(
            part for part in [message.from_user.first_name, message.from_user.last_name] if part
        ).strip()
        if message.from_user.username:
            return f"{full_name} (@{message.from_user.username})" if full_name else f"@{message.from_user.username}"
        if full_name:
            return full_name

    return "Сосагио"


def get_webhook_username(message):
    author = get_message_author(message).strip()
    if not author:
        return "Сосагио"
    return author[:80]


def build_discord_content(message):
    return message.text or message.caption or ""


def send_to_discord(content="", file_payload=None, webhook_username=None):
    data = {'content': content}
    if webhook_username:
        data['username'] = webhook_username

    if file_payload:
        requests.post(DISCORD_WEBHOOK, data=data, files={'file': file_payload})
    else:
        requests.post(DISCORD_WEBHOOK, data=data)


def forward_file_to_discord(file_id, filename, mime_type, text, webhook_username):
    file_info = bot.get_file(file_id)
    file_data = bot.download_file(file_info.file_path)
    send_to_discord(content=text, file_payload=(filename, file_data, mime_type), webhook_username=webhook_username)


@bot.channel_post_handler(content_types=CHANNEL_CONTENT_TYPES)
def handle_channel_post(message):
    try:
        text = build_discord_content(message)
        webhook_username = get_webhook_username(message)

        if message.content_type == 'text':
            send_to_discord(content=text, webhook_username=webhook_username)
            print(f"Сообщение переслано в Discord ({message.chat.title})")
            return

        if message.content_type == 'photo':
            forward_file_to_discord(
                file_id=message.photo[-1].file_id,
                filename=f"photo_{message.message_id}.jpg",
                mime_type='image/jpeg',
                text=text,
                webhook_username=webhook_username,
            )
            print(f"Фото переслано в Discord ({message.chat.title})")
            return

        if message.content_type == 'document':
            # Не дублируем обработку webm: этим занимается отдельная команда.
            # if message.document and message.document.mime_type == 'video/webm':
            #     return

            filename = message.document.file_name or f"file_{message.message_id}"
            mime_type = message.document.mime_type or 'application/octet-stream'
            forward_file_to_discord(
                file_id=message.document.file_id,
                filename=filename,
                mime_type=mime_type,
                text=text,
                webhook_username=webhook_username,
            )
            print(f"Файл переслан в Discord ({message.chat.title})")
            return

        if message.content_type == 'video':
            mime_type = message.video.mime_type or 'video/mp4'
            forward_file_to_discord(
                file_id=message.video.file_id,
                filename=f"video_{message.message_id}.mp4",
                mime_type=mime_type,
                text=text,
                webhook_username=webhook_username,
            )
            print(f"Видео переслано в Discord ({message.chat.title})")
            return

        if message.content_type == 'animation':
            filename = message.animation.file_name or f"animation_{message.message_id}.gif"
            mime_type = message.animation.mime_type or 'image/gif'
            forward_file_to_discord(
                file_id=message.animation.file_id,
                filename=filename,
                mime_type=mime_type,
                text=text,
                webhook_username=webhook_username,
            )
            print(f"GIF/анимация переслана в Discord ({message.chat.title})")
            return

        if message.content_type == 'audio':
            filename = message.audio.file_name or f"audio_{message.message_id}.mp3"
            mime_type = message.audio.mime_type or 'audio/mpeg'
            forward_file_to_discord(
                file_id=message.audio.file_id,
                filename=filename,
                mime_type=mime_type,
                text=text,
                webhook_username=webhook_username,
            )
            print(f"Аудио переслано в Discord ({message.chat.title})")
            return

        if message.content_type == 'voice':
            forward_file_to_discord(
                file_id=message.voice.file_id,
                filename=f"voice_{message.message_id}.ogg",
                mime_type='audio/ogg',
                text=text,
                webhook_username=webhook_username,
            )
            print(f"Голосовое переслано в Discord ({message.chat.title})")
            return

        if message.content_type == 'video_note':
            forward_file_to_discord(
                file_id=message.video_note.file_id,
                filename=f"video_note_{message.message_id}.mp4",
                mime_type='video/mp4',
                text=text,
                webhook_username=webhook_username,
            )
            print(f"Видео-кружок переслан в Discord ({message.chat.title})")
            return

        if message.content_type == 'sticker':
            filename = f"sticker_{message.message_id}.webp"
            mime_type = 'image/webp'
            if getattr(message.sticker, 'is_animated', False):
                filename = f"sticker_{message.message_id}.tgs"
                mime_type = 'application/x-tgsticker'
            if getattr(message.sticker, 'is_video', False):
                filename = f"sticker_{message.message_id}.webm"
                mime_type = 'video/webm'
            forward_file_to_discord(
                file_id=message.sticker.file_id,
                filename=filename,
                mime_type=mime_type,
                text=text,
                webhook_username=webhook_username,
            )
            print(f"Стикер переслан в Discord ({message.chat.title})")
            return

        # Для сервисных/редких типов отправляем текстовый fallback.
        fallback = text or f"[Telegram {message.content_type}]"
        send_to_discord(content=fallback, webhook_username=webhook_username)
        print(f"Служебный тип {message.content_type} переслан как текст ({message.chat.title})")
    except Exception as e:
        print(f"Ошибка при пересылке: {e}")

print("Бот запущен.")
bot.infinity_polling()
