import os
import re
import shutil
import tempfile

import requests
import yt_dlp
from bs4 import BeautifulSoup

def command(bot):
    @bot.message_handler(commands=['music'])
    def music_command(message):
        bot.send_message(message.chat.id, "Отправьте ссылку на трек в Spotify.")
        bot.register_next_step_handler(message, handle_spotify_link)

    def handle_spotify_link(message):
        spotify_url = (message.text or "").strip()

        if not spotify_url:
            bot.send_message(message.chat.id, "Ссылка пуста. Пришлите ссылку на трек в Spotify.")
            return

        if not is_spotify_url(spotify_url):
            bot.send_message(message.chat.id, "Нужна ссылка на конкретный трек Spotify.")
            return

        song, artist, error = get_song_info_from_spotify(spotify_url)
        if error:
            bot.send_message(message.chat.id, f"Ошибка: {error}")
            return

        search_query = f"{song} {artist}".strip()
        bot.send_message(message.chat.id, f"Ищу трек: {search_query}")

        youtube_url, search_error = search_song_youtube(search_query)
        if search_error:
            bot.send_message(message.chat.id, f"Не удалось найти трек: {search_error}")
            return

        bot.send_message(message.chat.id, "Скачиваю аудио с YouTube...")
        file_path, temp_dir, download_error = download_song_as_mp3(youtube_url, search_query=search_query)
        if download_error:
            bot.send_message(message.chat.id, f"Ошибка скачивания: {download_error}")
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return

        try:
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            
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


def search_song_youtube(search_query):
    use_browser_cookies = str_to_bool(os.getenv('YTDLP_USE_BROWSER_COOKIES', '0'))
    browser_cookies_env = os.getenv('YTDLP_BROWSER_COOKIES', 'chrome,firefox,edge')
    browser_cookies = [b.strip() for b in browser_cookies_env.split(',') if b.strip()]
    cookies_file = os.getenv('YTDLP_COOKIES_FILE', '').strip()

    search_client = 'web' if cookies_file else os.getenv('YTDLP_SEARCH_CLIENT', 'android')
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extractor_args': get_youtube_extractor_args(search_client),
    }

    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file
    elif use_browser_cookies and browser_cookies:
        # Используем первый доступный браузер для поиска, если нужно авторизоваться.
        ydl_opts['cookiesfrombrowser'] = (browser_cookies[0],)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{search_query} official audio", download=False)
        entries = info.get('entries') or []
        for entry in entries:
            if entry.get('webpage_url'):
                return entry['webpage_url'], None
        return None, "YouTube не вернул результатов"
    except Exception as e:
        return None, str(e)


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


def download_song_as_mp3(youtube_url, search_query=None, output_path=None):
    """
    Скачивает аудио с YouTube-ссылки и сохраняет как mp3.
    Требуется установленный yt-dlp и ffmpeg.
    """
    normalized_url = youtube_url.replace("music.youtube.com", "www.youtube.com")
    target_dir = output_path or tempfile.mkdtemp(prefix="music_bot_")

    use_browser_cookies = str_to_bool(os.getenv('YTDLP_USE_BROWSER_COOKIES', '0'))
    browser_cookies_env = os.getenv('YTDLP_BROWSER_COOKIES', 'chrome,firefox,edge')
    browser_cookies = [b.strip() for b in browser_cookies_env.split(',') if b.strip()]
    cookies_file = os.getenv('YTDLP_COOKIES_FILE', '').strip()
    require_po_token = str_to_bool(os.getenv('YTDLP_REQUIRE_PO_TOKEN', '0'))
    po_token = os.getenv('YTDLP_PO_TOKEN', '').strip()

    if require_po_token and not po_token:
        return None, target_dir, (
            'Для сервера требуется PO token. '
            'Задайте переменную окружения YTDLP_PO_TOKEN '
            'и при необходимости YTDLP_PO_CLIENT=web или android.'
        )

    if cookies_file and not os.path.isfile(cookies_file):
        return None, target_dir, f'Файл cookies не найден: {cookies_file}'

    base_opts = {
        'outtmpl': os.path.join(target_dir, '%(title).80s.%(ext)s'),
        'restrictfilenames': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'noplaylist': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'retries': 2,
        'extractor_retries': 2,
        'cachedir': False,
    }

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
                mp3_path = find_latest_mp3(target_dir)
                if mp3_path:
                    return mp3_path, target_dir, None
                last_error = 'Файл mp3 не найден после скачивания'
            except Exception as e:
                if is_sign_in_required_error(e):
                    saw_sign_in_required = True
                last_error = e

    # На сервере YouTube чаще просит авторизацию: пробуем cookies/web-клиент только по необходимости.
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
                    mp3_path = find_latest_mp3(target_dir)
                    if mp3_path:
                        return mp3_path, target_dir, None
                    last_error = 'Файл mp3 не найден после скачивания'
                except Exception as e:
                    last_error = e

    if saw_sign_in_required and not auth_configured:
        return None, target_dir, (
            'YouTube требует авторизацию. Укажите cookies через '
            'YTDLP_COOKIES_FILE=/path/to/cookies.txt или включите '
            'YTDLP_USE_BROWSER_COOKIES=1 (и опционально YTDLP_BROWSER_COOKIES=chrome,firefox,edge).'
        )

    if search_query:
        try:
            search_client = 'web' if cookies_file else 'android'
            search_opts = {
                'quiet': True,
                'noplaylist': True,
                'no_warnings': True,
                'extractor_args': get_youtube_extractor_args(search_client),
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
                    'extractor_args': get_youtube_extractor_args(search_client),
                }
                if cookies_file:
                    ydl_opts['cookiefile'] = cookies_file
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([fallback_url])
                mp3_path = find_latest_mp3(target_dir)
                if mp3_path:
                    return mp3_path, target_dir, None
        except Exception as e:
            last_error = e

    return None, target_dir, str(last_error or 'Неизвестная ошибка')


def find_latest_mp3(folder_path):
    mp3_files = [
        os.path.join(folder_path, f) for f in os.listdir(folder_path)
        if f.lower().endswith('.mp3')
    ]
    if not mp3_files:
        return None
    return max(mp3_files, key=os.path.getmtime)
