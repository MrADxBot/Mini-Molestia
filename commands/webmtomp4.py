import os
import subprocess

def command(bot):
    @bot.channel_post_handler(func=lambda message: message.document.mime_type == 'video/webm', content_types=['document']) 
    def transform(message):
        try:
            file_info = bot.get_file(message.document.file_id)
            file = message.document.file_name
            with open(file, 'wb') as f:
                f.write(bot.download_file(file_info.file_path))
            output_file = file.rsplit('.', 1)[0] + '.mp4'
            webt_to_mp4(file, output_file)

            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            with open(output_file, 'rb') as f:
                bot.send_document(chat_id=message.chat.id, document=f)

            os.remove(file)
            os.remove(output_file)

        except Exception as e:
            bot.send_message(chat_id=message.chat.id, text=f"Ошибка при конвертации: {e}")

def webt_to_mp4(input_file, output_file):
    command = [
            'ffmpeg',
            '-i', input_file,
            '-c:v', 'libx264',  # Video codec
            '-preset', 'medium', # Encoding preset (e.g., ultrafast, medium, slow)
            '-crf', '23',       # Constant Rate Factor for quality (lower is higher quality)
            '-c:a', 'aac',      # Audio codec
            '-b:a', '128k',     # Audio bitrate
            output_file
        ]
    subprocess.run(command, check=True) 
    
