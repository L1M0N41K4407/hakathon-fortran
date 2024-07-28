from config import host, user, password, db_name
import telebot
import sqlite3
from telebot import types

# Инициализация бота
TOKEN = '6818579998:AAFwZ4nIWfESwyKpZdPx-c2HfDW3rfZgEGs'
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
conn = sqlite3.connect('qr_codes.db', check_same_thread=False)

# Функция для проверки и добавления столбцов
def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

# Обновление структуры таблицы users
with conn:
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        tokens INTEGER DEFAULT 0,
                        vip_status TEXT DEFAULT 'Нет')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS qr_codes (
                        code TEXT PRIMARY KEY,
                        user_id INTEGER)''')
    add_column_if_not_exists(cursor, 'users', 'username', 'TEXT')
    add_column_if_not_exists(cursor, 'users', 'vip_status', 'TEXT DEFAULT \'Нет\'')

# Обработчик команд /start и /help
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    username = message.from_user.username
    user_id = message.from_user.id
    with conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))

    markup = types.ReplyKeyboardMarkup(row_width=1)
    personal_cabinet_button = types.KeyboardButton('Личный кабинет')
    markup.add(personal_cabinet_button)

    bot.send_message(message.chat.id, "Привет! Отправь мне фото QR-кода, чтобы получить токен.", reply_markup=markup)

# Обработчик сообщений с фото (QR-кодами)
@bot.message_handler(content_types=['photo'])
def handle_qr_code(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with open('qr_code.png', 'wb') as new_file:
        new_file.write(downloaded_file)

    qr_code_data = 'some_data'  # Здесь должна быть ваша логика для извлечения данных из QR-кода

    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM qr_codes WHERE code = ?", (qr_code_data,))
        data = cursor.fetchone()

        if data:
            bot.send_message(message.chat.id, "Этот QR-код уже был использован.")
        else:
            cursor.execute("INSERT INTO qr_codes (code, user_id) VALUES (?, ?)", (qr_code_data, user_id))
            cursor.execute("INSERT OR IGNORE INTO users (user_id, tokens) VALUES (?, ?)", (user_id, 0))
            cursor.execute("UPDATE users SET tokens = tokens + 1 WHERE user_id = ?", (user_id,))
            bot.send_message(message.chat.id, "QR-код успешно отсканирован. Вы получили 1 токен!")

# Обработчик кнопки "Личный кабинет"
@bot.message_handler(func=lambda message: message.text == 'Личный кабинет')
def personal_cabinet(message):
    user_id = message.from_user.id
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, tokens, vip_status FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()

        cursor.execute("SELECT code FROM qr_codes WHERE user_id = ?", (user_id,))
        scanned_qr_codes = cursor.fetchall()

        if user_data:
            username, tokens, vip_status = user_data
            qr_codes_list = ', '.join([code[0] for code in scanned_qr_codes])
            response = (f"Юзернейм: {username}\n"
                        f"Токены: {tokens}\n"
                        f"Бакалажки: {qr_codes_list}\n"
                        f"VIP-status: {vip_status}")
            bot.send_message(message.chat.id, response)
        else:
            bot.send_message(message.chat.id, "Пользователь не найден.")

# Запуск бота
bot.polling()