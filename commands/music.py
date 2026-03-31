import re
import os
import yt_dlp
import requests
from bs4 import BeautifulSoup
from ytmusicapi import YTMusic

def command(bot):
    @bot.message_handler(commands=['music'])
    def music_command(message):
        # bot.send_message(message.chat.id, "Отправьте ссылку на Spotify для скачивания песни.")
        bot.register_next_step_handler(message, handle_spotify_link)

    def handle_spotify_link(message):
        spotify_url = message.text.strip()
        
        song, artist, error = get_song_info_from_spotify(spotify_url)
        if error:
            bot.send_message(message.chat.id, f"Ошибка: {error}")
            return

        bot.send_message(message.chat.id, f"Песня: {song}\nИсполнитель: {artist}")

        # Поиск на YouTube и скачивание mp3
        search_query = f"{song} {artist}"
        while artist == "Spotify":
            song, artist, error = get_song_info_from_spotify(spotify_url) 
        youtube_url = search_song_YTM(search_query)
        if not youtube_url:
            bot.send_message(message.chat.id, "Не удалось найти трек на YouTube.")
            return

        bot.send_message(message.chat.id, "Скачиваю аудио с YouTube...")
        error = download_song_as_mp3(youtube_url, search_query=search_query)
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


def get_youtube_extractor_args(player_client=None):
    selected_client = (player_client or os.getenv('YTDLP_PO_CLIENT', 'android')).strip() or 'android'
    extractor_args = {'youtube': {'player_client': [selected_client]}}
    po_token = os.getenv('YTDLP_PO_TOKEN', '').strip()
    po_client = selected_client
    if po_token:
        extractor_args['youtube']['po_token'] = [f'{po_client}.gvs+{po_token}']
    return extractor_args


def str_to_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def is_sign_in_required_error(error):
    if not error:
        return False
    text = str(error).lower()
    return 'sign in to confirm you\'re not a bot' in text or 'use --cookies' in text


def download_song_as_mp3(youtube_url, search_query=None, output_path="."):
    """
    Скачивает аудио с YouTube-ссылки и сохраняет как mp3.
    Требуется установленный yt-dlp и ffmpeg.
    """
    normalized_url = youtube_url.replace("music.youtube.com", "www.youtube.com")

    use_browser_cookies = str_to_bool(os.getenv('YTDLP_USE_BROWSER_COOKIES', '0'))
    browser_cookies_env = os.getenv('YTDLP_BROWSER_COOKIES', 'chrome,firefox,edge')
    browser_cookies = [b.strip() for b in browser_cookies_env.split(',') if b.strip()]
    cookies_file = os.getenv('YTDLP_COOKIES_FILE', '').strip()
    require_po_token = str_to_bool(os.getenv('YTDLP_REQUIRE_PO_TOKEN', '0'))
    po_token = os.getenv('YTDLP_PO_TOKEN', '').strip()

    if require_po_token and not po_token:
        return (
            'Для сервера требуется PO token. '
            'Задайте переменную окружения YTDLP_PO_TOKEN '
            'и при необходимости YTDLP_PO_CLIENT=web или android.'
        )

    if cookies_file and not os.path.isfile(cookies_file):
        return f'Файл cookies не найден: {cookies_file}'

    base_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'noplaylist': True,
        'no_warnings': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'retries': 2,
        'extractor_retries': 2,
        'js_runtimes': ['node'],
    }

    # Сначала пробуем без авторизации: это быстрее и часто достаточно.
    no_auth_clients = ['android', 'mweb', 'tv', 'web']
    no_auth_formats = ['18/best', 'bestaudio/best', 'best']

    auth_configured = bool(cookies_file or (use_browser_cookies and browser_cookies))
    saw_sign_in_required = False
    last_error = None

    for client in no_auth_clients:
        for fmt in no_auth_formats:
            try:
                ydl_opts = {
                    **base_opts,
                    'format': fmt,
                    'extractor_args': get_youtube_extractor_args(client),
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([normalized_url])
                return None
            except Exception as e:
                if is_sign_in_required_error(e):
                    saw_sign_in_required = True
                last_error = e

    # Только при явной необходимости пробуем с cookies и только web-клиент.
    if saw_sign_in_required and auth_configured:
        auth_attempts = []
        if cookies_file:
            auth_attempts.append({'cookiefile': cookies_file})
        if use_browser_cookies:
            for browser in browser_cookies:
                auth_attempts.append({'cookiesfrombrowser': (browser,)})

        for auth_attempt in auth_attempts:
            for fmt in no_auth_formats:
                try:
                    ydl_opts = {
                        **base_opts,
                        **auth_attempt,
                        'format': fmt,
                        'extractor_args': get_youtube_extractor_args('web'),
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([normalized_url])
                    return None
                except Exception as e:
                    last_error = e

    if saw_sign_in_required and not auth_configured:
        return (
            'YouTube требует авторизацию. Укажите cookies через '
            'YTDLP_COOKIES_FILE=/path/to/cookies.txt или включите '
            'YTDLP_USE_BROWSER_COOKIES=1 (и опционально YTDLP_BROWSER_COOKIES=chrome,firefox,edge).'
        )

    # Fallback: search by title+artist and download first playable result.
    if search_query:
        try:
            search_client = 'web' if cookies_file else 'android'
            search_opts = {
                'quiet': False,
                'noplaylist': True,
                'no_warnings': False,
                'extractor_args': get_youtube_extractor_args(search_client),
                'js_runtimes': ['node']
            }
            if cookies_file:
                search_opts['cookiefile'] = cookies_file
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{search_query} official audio", download=False)
            entries = info.get('entries') or []
            if entries and entries[0].get('webpage_url'):
                fallback_url = entries[0]['webpage_url']
                ydl_opts = {
                    **base_opts,
                    'format': 'best',
                    'extractor_args': get_youtube_extractor_args(search_client)
                }
                if cookies_file:
                    ydl_opts['cookiefile'] = cookies_file
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([fallback_url])
                return None
        except Exception as e:
            last_error = e

    print(f"Ошибка скачивания: {last_error}")
    return str(last_error)

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

            # Если videoId существует, формируем ссылку
            if video_id:
                song_url = f"https://music.youtube.com/watch?v={video_id}"
                return song_url
            else:
                return "Не удалось найти идентификатор видео для этой песни"
        else:
            return "Песня не найдена"
    except Exception as e:
        print(f"YTMusic поиск не удался: {e}")

    # Запасной метод: через yt-dlp и обычный YouTube
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "js_runtimes": ["node"]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{song_name}", download=False)['entries'][0]
            return info['webpage_url']
    except Exception as e2:
        return f"Не удалось найти песню через yt-dlp: {e2}"
