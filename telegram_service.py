# telegram_service.py - Сервис для работы с Telegram

import telebot
from telebot import types
import os
from dotenv import load_dotenv
import threading
import time

# Загрузка переменных окружения
load_dotenv()

# Инициализация Telegram бота
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""))

# Словари для локализации
MESSAGES = {
    "ru": {
        "welcome": "Привет! Я бот для торговли токенами Solana.\n\nДоступные команды:\n/start - Показать это сообщение\n/balance - Проверить баланс кошелька\n/stats - Показать статистику торговли",
        "trade_success": lambda params: f"Токен куплен: {params['token_name']}, Количество: {params['amount']}, Цена: {params['price']} SOL",
        "trade_profit": lambda params: f"Токен продан: {params['token_name']}, Прибыль: {params['profit']}%",
        "balance": lambda params: f"Баланс вашего кошелька: {params['balance']} SOL",
        "stats": lambda params: f"Статистика торговли:\nВсего сделок: {params['total_trades']}\nУспешных: {params['successful_trades']}\nПрибыль: {params['total_profit']} SOL",
        "not_registered": "Ваш аккаунт не связан с ботом. Обратитесь к администратору."
    },
    "uz": {
        "welcome": "Salom! Men Solana tokenlarini savdo qilish uchun botman.\n\nMavjud buyruqlar:\n/start - Ushbu xabarni ko'rsatish\n/balance - Hamyon balansini tekshirish\n/stats - Savdo statistikasini ko'rsatish",
        "trade_success": lambda params: f"Token sotib olindi: {params['token_name']}, Miqdor: {params['amount']}, Narxi: {params['price']} SOL",
        "trade_profit": lambda params: f"Token sotildi: {params['token_name']}, Foyda: {params['profit']}%",
        "balance": lambda params: f"Hamyon balansingiz: {params['balance']} SOL",
        "stats": lambda params: f"Savdo statistikasi:\nJami bitimlar: {params['total_trades']}\nMuvaffaqiyatli: {params['successful_trades']}\nFoyda: {params['total_profit']} SOL",
        "not_registered": "Hisobingiz bot bilan bog'lanmagan. Administrator bilan bog'laning."
    }
}

# Функция для получения сообщения на нужном языке
def get_message(message_key, language="ru", params=None):
    if params is None:
        params = {}
    
    # Получаем словарь сообщений для указанного языка или для русского по умолчанию
    messages = MESSAGES.get(language, MESSAGES["ru"])
    
    # Получаем сообщение по ключу
    message = messages.get(message_key)
    
    # Если сообщение - функция (для параметризованных сообщений), вызываем ее с параметрами
    if callable(message):
        return message(params)
    
    # Иначе возвращаем текст сообщения или сам ключ, если сообщение не найдено
    return message if message else message_key

# Функция для отправки сообщения через Telegram
def send_message(chat_id, message_key, language="ru", params=None):
    message_text = get_message(message_key, language, params)
    bot.send_message(chat_id, message_text)

# Функция для создания клавиатуры на нужном языке
def get_keyboard(language="ru"):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if language == "uz":
        markup.add(types.KeyboardButton("Balans"), types.KeyboardButton("Statistika"))
    else:  # Русский по умолчанию
        markup.add(types.KeyboardButton("Баланс"), types.KeyboardButton("Статистика"))
    
    return markup

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    # Здесь должна быть логика для проверки пользователя в базе данных
    # и определения его языка
    # Для примера используем русский язык
    
    chat_id = message.chat.id
    language = "ru"  # В реальности брать из базы данных
    
    # Отправляем приветственное сообщение
    send_message(chat_id, "welcome", language)
    
    # Показываем клавиатуру
    bot.send_message(chat_id, "Выберите действие:", reply_markup=get_keyboard(language))

# Обработчик команды /balance
@bot.message_handler(commands=['balance'])
def handle_balance(message):
    chat_id = message.chat.id
    
    # Получаем информацию о пользователе из базы данных
    # В реальном боте это будет запрос к MongoDB
    user = {
        "language": "ru",  # В реальности брать из базы данных
        "wallet_address": "SampleWalletAddress123"  # В реальности брать из базы данных
    }
    
    # Получаем баланс кошелька (в реальности это будет запрос к Solana)
    balance = 1.234  # Sample balance in SOL
    
    # Отправляем сообщение с балансом
    send_message(chat_id, "balance", user["language"], {"balance": balance})

# Обработчик команды /stats
@bot.message_handler(commands=['stats'])
def handle_stats(message):
    chat_id = message.chat.id
    
    # Получаем информацию о пользователе из базы данных
    # В реальном боте это будет запрос к MongoDB
    user = {
        "language": "ru",  # В реальности брать из базы данных
    }
    
    # Получаем статистику торговли (в реальности это будет запрос к MongoDB)
    stats = {
        "total_trades": 10,
        "successful_trades": 8,
        "total_profit": 0.5
    }
    
    # Отправляем сообщение со статистикой
    send_message(chat_id, "stats", user["language"], stats)

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.lower()
    
    # Получаем информацию о пользователе из базы данных
    # В реальном боте это будет запрос к MongoDB
    user = {
        "language": "ru",  # В реальности брать из базы данных
    }
    
    # Обрабатываем русскоязычные команды
    if text == "баланс" or text == "balans":
        handle_balance(message)
    elif text == "статистика" or text == "statistika":
        handle_stats(message)
    else:
        # Просто отправляем приветственное сообщение
        send_message(chat_id, "welcome", user["language"])

# Функция для запуска бота в отдельном потоке
def start_bot():
    bot.polling(none_stop=True)

# Функция для отправки уведомления о покупке токена
def notify_token_purchase(chat_id, token_name, amount, price, language="ru"):
    params = {
        "token_name": token_name,
        "amount": amount,
        "price": price
    }
    send_message(chat_id, "trade_success", language, params)

# Функция для отправки уведомления о продаже токена
def notify_token_sale(chat_id, token_name, profit, language="ru"):
    params = {
        "token_name": token_name,
        "profit": profit
    }
    send_message(chat_id, "trade_profit", language, params)

# Экспортируем функции для использования в других модулях
__all__ = [
    'start_bot',
    'notify_token_purchase',
    'notify_token_sale',
    'send_message',
    'get_message'
]

# Если файл запускается напрямую, запускаем бота
if __name__ == "__main__":
    start_bot()