import io
import librosa
import soundfile as sf
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import config

bot = Bot(token=config.TGTOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect('stats.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS stats
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER,
                   date DATE)''')
conn.commit()

@dp.message_handler(content_types=types.ContentType.VOICE)
async def process_voice_message(message: types.Message):
    voice_file = io.BytesIO()
    await message.voice.download(destination=voice_file)
    y, sr = librosa.load(voice_file, sr=16000)
    voice_file.close()
    voice_file = io.BytesIO()
    sf.write(voice_file, y, sr, format='WAV', subtype='PCM_16')
    voice_file.seek(0)
    text = recognize_speech(voice_file)
    await message.reply(text)
    record_stat(message.from_user.id)

def recognize_speech(file):
    import speech_recognition as sr
    r = sr.Recognizer()
    with sr.AudioFile(file) as source:
        audio = r.record(source)
        try:
            text = r.recognize_google(audio, language='ru-RU')
            return text
        except sr.UnknownValueError:
            return "Не удалось распознать речь"
        except sr.RequestError as e:
            return f"Произошла ошибка при обращении к серверу распознавания речи: {e}"

def record_stat(user_id):
    cursor.execute("INSERT INTO stats (user_id, date) VALUES (?, DATE('now'))", (user_id,))
    conn.commit()

@dp.message_handler(commands=['stats'])
async def show_stats(message: types.Message):
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM stats")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM stats WHERE date = DATE('now')")
    today_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stats")
    total_requests = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stats WHERE date = DATE('now')")
    today_requests = cursor.fetchone()[0]
    text = f"Статистика использования бота:\n" \
           f"Всего пользователей: {total_users}\n" \
           f"Пользователей сегодня: {today_users}\n" \
           f"Всего запросов: {total_requests}\n" \
           f"Запросов сегодня: {today_requests}"
    await message.reply(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
