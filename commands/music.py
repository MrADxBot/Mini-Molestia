import re
import os
import yt_dlp
import requests
from bs4 import BeautifulSoup
from ytmusicapi import YTMusic

def command(bot):
    @bot.message_handler(commands=['music'])
    def music_command(message):
        bot.send_message(message.chat.id, "Отправьте название трека или ссылку на Spotify или Youtube.")
        bot.register_next_step_handler(message, check_input)

    def check_input(message):
        text = message.text
        if is_spotify_url(text):
            youtube_url = handle_spotify_link(message)
        elif is_youtube_url(text):
            youtube_url = text
        else:
            youtube_url = search_song_YTM(text)

        # Проверяем, что получили валидную ссылку
        if not youtube_url or not str(youtube_url).startswith("http"):
            bot.send_message(message.chat.id, f"Не удалось получить ссылку на YouTube: {youtube_url}")
            return

        bot.send_message(message.chat.id, f"Ссылка на аудио с YouTube: {youtube_url}")
        bot.send_message(message.chat.id, "Начинаю скачивание, это может занять некоторое время...")
        error = download_song_as_mp3(youtube_url)
        if error:
            bot.send_message(message.chat.id, f"Ошибка скачивания: {error}")
            return

        # Отправка mp3 пользователю
        files = [f for f in os.listdir('.') if f.endswith('.mp3')]
        if files:
            file_path = files[-1]
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f)
            os.remove(file_path)
        else:
            print("Файл не найден после скачивания.")
            
    def handle_spotify_link(message):
        spotify_url = message.text.strip()
        
        song, artist, error = get_song_info_from_spotify(spotify_url)
        if error:
            bot.send_message(message.chat.id, f"Ошибка: {error}")
            return None

        bot.send_message(message.chat.id, f"Песня: {song}\nИсполнитель: {artist}")

        # Поиск на YouTube
        search_query = f"{song} {artist}"
        youtube_url = search_song_YTM(search_query)
        if not youtube_url:
            bot.send_message(message.chat.id, "Не удалось найти трек на YouTube.")
            return None
        return youtube_url
            
def get_song_info_from_spotify(spotify_url):
    """
    Получает название трека и исполнителя по ссылке Spotify без авторизации.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(spotify_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None, None, "Ошибка доступа к Spotify"
        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        if not title_tag:
            return None, None, "Не удалось найти название трека"
        title = title_tag.text.replace(" | Spotify", "").strip()
        title = re.sub(r"\s*song and lyrics\s*", "", title, flags=re.IGNORECASE)

        # Проверка формата "Song by Artist" или "Song -by Artist"
        match = re.match(r"(.+?)\s*(?:by|\-by)\s*(.+)", title, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip(), None

        # Разделители
        for sep in [" – ", " — ", "-", "—", "–"]:
            if sep in title:
                left, right = map(str.strip, title.split(sep, 1))
                if len(left) > len(right):
                    return left, right, None
                else:
                    return right, left, None

        return None, None, f"Не удалось распарсить название и исполнителя: {title}"
    except Exception as e:
        return None, None, f"Ошибка парсинга: {e}"


def is_spotify_url(text):
    return "open.spotify.com/track" in text

def is_youtube_url(text):
    return "youtube.com/watch" in text or "youtu.be/" in text

def download_song_as_mp3(youtube_url, output_path="."):
    """
    Скачивает аудио с YouTube-ссылки и сохраняет как mp3.
    Требуется установленный yt-dlp и ffmpeg.
    """
    # Попробуем несколько попыток и увеличим таймаут соединения
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'noplaylist': True,
        'no_warnings': True,
        # Увеличиваем таймаут сокета (сек)
        'socket_timeout': 60,
    }

    last_err = None
    for attempt in range(3):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            return None
        except Exception as e:
            last_err = e
    # Если не получилось после попыток, возвращаем ошибку строкой
    return f"Ошибка скачивания: {last_err}"

def search_song_YTM(song_name):
    try:
        # Инициализация API YouTube Music
        ytmusic = YTMusic()

        # Выполнение поиска по названию песни
        search_results = ytmusic.search(song_name, filter="songs")

        # Проверяем, есть ли результаты поиска
        if search_results:
            # Берем первый результат из списка
            first_result = search_results[0]

            # Получаем идентификатор видео
            video_id = first_result.get("videoId", "")

            # Если videoId существует, формируем обычную youtube.com ссылку
            if video_id:
                song_url = f"https://www.youtube.com/watch?v={video_id}"
                return song_url
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"YTMusic поиск не удался: {e}")

    # Запасной метод: через yt-dlp и обычный YouTube
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{song_name}", download=False)['entries'][0]
            return info.get('webpage_url')
    except Exception as e2:
        return None
