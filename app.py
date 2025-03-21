# app.py - Основной файл сервера

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pymongo
from pymongo import MongoClient
import bcrypt
import base58
from solana.keypair import Keypair
import telebot
import threading
import time
import json
import os
from dotenv import load_dotenv
import requests
import uuid
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app)  # Включаем CORS для API
PORT = int(os.environ.get("PORT", 5000))

# Подключение к MongoDB
client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017/"))
db = client["solana_bot_db"]
users_collection = db["users"]
transactions_collection = db["transactions"]
tokens_collection = db["tokens"]

# Инициализация Telegram бота
telegram_bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""))

# Конфигурация бота
class Config:
    MIGRATION_THRESHOLD = 98  # Процент миграции для покупки
    TARGET_PROFIT = 10  # Целевая прибыль в процентах
    PURCHASE_AMOUNT_SOL = 0.05  # Количество SOL для покупки
    MAX_HOLDING_TIME = 3600  # Максимальное время удержания токена в секундах (1 час)
    CHECK_INTERVAL = 5  # Интервал проверки токенов в секундах

# Функция для создания кошелька Solana
def create_solana_wallet():
    keypair = Keypair()
    return {
        "address": str(keypair.public_key),
        "private_key": base58.b58encode(keypair.secret_key).decode('ascii')
    }

# Функции для мультиязычности
def get_message(message_key, language="ru", params=None):
    if params is None:
        params = {}
    
    messages = {
        "ru": {
            "welcome": "Привет! Я бот.",
            "trade_success": f"Токен куплен: {params.get('token_name', '')}, Количество: {params.get('amount', '')}, Цена: {params.get('price', '')} SOL",
            "trade_profit": f"Токен продан: {params.get('token_name', '')}, Прибыль: {params.get('profit', '')}%"
        },
        "uz": {
            "welcome": "Salom! Men botman.",
            "trade_success": f"Token sotib olindi: {params.get('token_name', '')}, Miqdor: {params.get('amount', '')}, Narxi: {params.get('price', '')} SOL",
            "trade_profit": f"Token sotildi: {params.get('token_name', '')}, Foyda: {params.get('profit', '')}%"
        }
    }
    
    return messages.get(language, messages["ru"]).get(message_key, message_key)

# Функция для отправки сообщений в Telegram
def send_telegram_message(chat_id, message_key, language="ru", params=None):
    message_text = get_message(message_key, language, params)
    telegram_bot.send_message(chat_id, message_text)

# Middleware для проверки авторизации
def auth_required(f):
    def decorated(*args, **kwargs):
        data = request.get_json()
        if not data or "username" not in data or "password" not in data:
            return jsonify({"success": False, "message": "Необходимо предоставить имя пользователя и пароль"}), 401
        
        username = data["username"]
        password = data["password"]
        
        user = users_collection.find_one({"username": username})
        if not user:
            return jsonify({"success": False, "message": "Пользователь не найден"}), 401
        
        if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            return f(*args, **kwargs, user=user)
        else:
            return jsonify({"success": False, "message": "Неверный пароль"}), 401
    
    return decorated

# Middleware для проверки прав администратора
def admin_required(f):
    def decorated(*args, **kwargs):
        user = kwargs.get("user")
        if not user or user["role"] != "admin":
            return jsonify({"success": False, "message": "Требуются права администратора"}), 403
        return f(*args, **kwargs)
    
    return decorated

# Маршруты API

# Главная страница
@app.route('/')
def home():
    return "Бот работает! Добро пожаловать на наш сайт!"

# Авторизация пользователя
@app.route('/api/auth/login', methods=['POST'])
@auth_required
def login(user):
    return jsonify({
        "success": True,
        "message": "Авторизация успешна",
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "role": user["role"],
            "language": user.get("language", "ru")
        }
    })

# Создание нового пользователя (только администратор)
@app.route('/api/users/create', methods=['POST'])
@auth_required
@admin_required
def create_user(user):
    data = request.get_json()
    
    if not data or "newUsername" not in data or "newPassword" not in data:
        return jsonify({"success": False, "message": "Необходимо предоставить имя пользователя и пароль"}), 400
    
    new_username = data["newUsername"]
    new_password = data["newPassword"]
    telegram_chat_id = data.get("telegramChatId")
    language = data.get("language", "ru")
    
    # Проверяем, существует ли пользователь
    existing_user = users_collection.find_one({"username": new_username})
    if existing_user:
        return jsonify({"success": False, "message": "Пользователь с таким именем уже существует"}), 400
    
    # Создаем хеш пароля
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    # Создаем кошелек
    wallet = create_solana_wallet()
    
    # Создаем нового пользователя
    new_user = {
        "username": new_username,
        "password": hashed_password,
        "role": "user",
        "wallet_address": wallet["address"],
        "wallet_private_key": wallet["private_key"],
        "telegram_chat_id": telegram_chat_id,
        "language": language,
        "active": True,
        "created_at": datetime.now()
    }
    
    result = users_collection.insert_one(new_user)
    
    return jsonify({
        "success": True,
        "message": "Пользователь успешно создан",
        "user": {
            "id": str(result.inserted_id),
            "username": new_username,
            "wallet_address": wallet["address"]
        }
    })

# Получение списка всех пользователей (только администратор)
@app.route('/api/users', methods=['GET'])
@auth_required
@admin_required
def get_users(user):
    users = list(users_collection.find({}, {
        "username": 1, 
        "role": 1, 
        "wallet_address": 1, 
        "active": 1, 
        "created_at": 1, 
        "telegram_chat_id": 1, 
        "language": 1
    }))
    
    # Преобразуем ObjectId в строки для JSON
    for user in users:
        user["_id"] = str(user["_id"])
    
    return jsonify({"success": True, "users": users})

# Функция для проверки миграции токена на pump.fun
def check_token_migration(token_address):
    try:
        # URL API pump.fun (заменить на реальный URL)
        api_url = f"https://api.pump.fun/tokens/{token_address}"
        
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            if data and "migrationPercentage" in data:
                return {
                    "success": True,
                    "migration_percentage": data["migrationPercentage"],
                    "above_threshold": data["migrationPercentage"] >= Config.MIGRATION_THRESHOLD
                }
        
        return {
            "success": False,
            "migration_percentage": 0,
            "above_threshold": False
        }
    except Exception as e:
        print(f"Ошибка при проверке миграции токена {token_address}: {str(e)}")
        return {
            "success": False,
            "migration_percentage": 0,
            "above_threshold": False,
            "error": str(e)
        }

# Функция для проверки миграции токена на Raydium
def check_raydium_token_migration(token_address):
    try:
        # URL API Raydium (заменить на реальный URL)
        api_url = f"https://api.raydium.io/tokens/{token_address}"
        
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            if data and "migrationPercentage" in data:
                return {
                    "success": True,
                    "migration_percentage": data["migrationPercentage"],
                    "above_threshold": data["migrationPercentage"] >= Config.MIGRATION_THRESHOLD
                }
        
        return {
            "success": False,
            "migration_percentage": 0,
            "above_threshold": False
        }
    except Exception as e:
        print(f"Ошибка при проверке миграции токена Raydium {token_address}: {str(e)}")
        return {
            "success": False,
            "migration_percentage": 0,
            "above_threshold": False,
            "error": str(e)
        }

# Функция для получения новых токенов с pump.fun
def get_new_pumpfun_tokens():
    try:
        # URL API для получения новых токенов (заменить на реальный URL)
        api_url = "https://api.pump.fun/tokens/new"
        
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list):
                return {
                    "success": True,
                    "tokens": data
                }
        
        return {
            "success": False,
            "tokens": []
        }
    except Exception as e:
        print(f"Ошибка при получении новых токенов с pump.fun: {str(e)}")
        return {
            "success": False,
            "tokens": [],
            "error": str(e)
        }

# Функция для получения новых токенов с Raydium
def get_new_raydium_tokens():
    try:
        # URL API для получения новых токенов (заменить на реальный URL)
        api_url = "https://api.raydium.io/tokens/new"
        
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list):
                return {
                    "success": True,
                    "tokens": data
                }
        
        return {
            "success": False,
            "tokens": []
        }
    except Exception as e:
        print(f"Ошибка при получении новых токенов с Raydium: {str(e)}")
        return {
            "success": False,
            "tokens": [],
            "error": str(e)
        }

# Функция для покупки токена
def buy_token(wallet, token_address, amount_in_sol):
    try:
        # Здесь должен быть код для взаимодействия с Solana блокчейном и DEX
        # для фактической покупки токена
        
        # Для демонстрации вернем симуляцию успешной покупки
        token_info = tokens_collection.find_one({"address": token_address})
        token_name = token_info["name"] if token_info else "Unknown Token"
        token_symbol = token_info["symbol"] if token_info else "???"
        
        # Симуляция цены токена (в реальности получить из DEX)
        token_price = 0.0001  # SOL за токен
        token_amount = amount_in_sol / token_price
        
        return {
            "success": True,
            "token_address": token_address,
            "token_name": token_name,
            "token_symbol": token_symbol,
            "amount_in_sol": amount_in_sol,
            "token_amount": token_amount,
            "token_price": token_price
        }
    except Exception as e:
        print(f"Ошибка при покупке токена {token_address}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Функция для продажи токена
def sell_token(wallet, token_address, token_amount, target_profit_percentage):
    try:
        # Здесь должен быть код для взаимодействия с Solana блокчейном и DEX
        # для фактической продажи токена
        
        # Для демонстрации вернем симуляцию успешной продажи
        token_info = tokens_collection.find_one({"address": token_address})
        token_name = token_info["name"] if token_info else "Unknown Token"
        
        # Симуляция текущей цены токена с учетом прибыли
        purchase_transaction = transactions_collection.find_one({
            "token_address": token_address,
            "status": "bought",
            "wallet_address": wallet["address"]
        })
        
        purchase_price = purchase_transaction["purchase_price"] if purchase_transaction else 0.0001
        current_price = purchase_price * (1 + target_profit_percentage / 100)
        sol_received = token_amount * current_price
        
        return {
            "success": True,
            "token_address": token_address,
            "token_name": token_name,
            "token_amount": token_amount,
            "sol_received": sol_received,
            "profit_percentage": target_profit_percentage
        }
    except Exception as e:
        print(f"Ошибка при продаже токена {token_address}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Функция для мониторинга токенов
def monitor_tokens():
    print("Запуск мониторинга токенов...")
    
    # Словарь для отслеживания токенов
    tracked_tokens = {}
    
    # Время последней проверки новых токенов
    last_new_tokens_check = 0
    
    while True:
        try:
            current_time = time.time()
            
            # Проверяем новые токены каждые 10 секунд
            if current_time - last_new_tokens_check > 10:
                # Получаем новые токены с pump.fun
                pump_tokens = get_new_pumpfun_tokens()
                if pump_tokens["success"]:
                    for token in pump_tokens["tokens"]:
                        if token["address"] not in tracked_tokens:
                            # Добавляем токен в БД
                            tokens_collection.update_one(
                                {"address": token["address"]},
                                {"$set": {
                                    "name": token["name"],
                                    "symbol": token["symbol"],
                                    "platform": "pump.fun",
                                    "last_migration_percentage": 0,
                                    "time_added": datetime.now(),
                                    "status": "tracking"
                                }},
                                upsert=True
                            )
                            
                            # Добавляем в отслеживаемые
                            tracked_tokens[token["address"]] = {
                                "name": token["name"],
                                "symbol": token["symbol"],
                                "platform": "pump.fun",
                                "last_migration_percentage": 0,
                                "time_added": datetime.now(),
                                "status": "tracking"
                            }
                            
                            print(f"Новый токен добавлен для отслеживания: {token['name']} ({token['symbol']})")
                
                # Получаем новые токены с Raydium
                raydium_tokens = get_new_raydium_tokens()
                if raydium_tokens["success"]:
                    for token in raydium_tokens["tokens"]:
                        if token["address"] not in tracked_tokens:
                            # Добавляем токен в БД
                            tokens_collection.update_one(
                                {"address": token["address"]},
                                {"$set": {
                                    "name": token["name"],
                                    "symbol": token["symbol"],
                                    "platform": "raydium",
                                    "last_migration_percentage": 0,
                                    "time_added": datetime.now(),
                                    "status": "tracking"
                                }},
                                upsert=True
                            )
                            
                            # Добавляем в отслеживаемые
                            tracked_tokens[token["address"]] = {
                                "name": token["name"],
                                "symbol": token["symbol"],
                                "platform": "raydium",
                                "last_migration_percentage": 0,
                                "time_added": datetime.now(),
                                "status": "tracking"
                            }
                            
                            print(f"Новый токен добавлен для отслеживания: {token['name']} ({token['symbol']})")
                
                last_new_tokens_check = current_time
            
            # Проверяем миграцию для каждого отслеживаемого токена
            for token_address, token_info in list(tracked_tokens.items()):
                # Пропускаем токены, которые не в статусе отслеживания
                if token_info["status"] != "tracking":
                    continue
                
                # Проверяем миграцию в зависимости от платформы
                migration_result = None
                if token_info["platform"] == "pump.fun":
                    migration_result = check_token_migration(token_address)
                elif token_info["platform"] == "raydium":
                    migration_result = check_raydium_token_migration(token_address)
                
                if migration_result and migration_result["success"]:
                    # Обновляем процент миграции
                    token_info["last_migration_percentage"] = migration_result["migration_percentage"]
                    
                    # Обновляем в БД
                    tokens_collection.update_one(
                        {"address": token_address},
                        {"$set": {"last_migration_percentage": migration_result["migration_percentage"]}}
                    )
                    
                    print(f"Токен {token_info['name']} ({token_info['symbol']}): миграция {migration_result['migration_percentage']}%")
                    
                    # Если миграция достигла порога, покупаем токен для всех активных пользователей
                    if migration_result["above_threshold"]:
                        token_info["status"] = "buying"
                        
                        # Обновляем статус в БД
                        tokens_collection.update_one(
                            {"address": token_address},
                            {"$set": {"status": "buying"}}
                        )
                        
                        # Получаем всех активных пользователей
                        active_users = list(users_collection.find({"active": True}))
                        
                        for user in active_users:
                            wallet = {
                                "address": user["wallet_address"],
                                "private_key": user["wallet_private_key"]
                            }
                            
                            # Покупаем токен
                            purchase_result = buy_token(wallet, token_address, Config.PURCHASE_AMOUNT_SOL)
                            
                            if purchase_result["success"]:
                                # Создаем запись о транзакции
                                transaction = {
                                    "user_id": user["_id"],
                                    "token_address": token_address,
                                    "token_name": purchase_result["token_name"],
                                    "token_symbol": purchase_result["token_symbol"],
                                    "purchase_price": purchase_result["token_price"],
                                    "purchase_amount": purchase_result["token_amount"],
                                    "purchase_sol": purchase_result["amount_in_sol"],
                                    "status": "bought",
                                    "created_at": datetime.now(),
                                    "updated_at": datetime.now()
                                }
                                
                                transactions_collection.insert_one(transaction)
                                
                                # Отправляем сообщение в Telegram
                                if "telegram_chat_id" in user and user["telegram_chat_id"]:
                                    send_telegram_message(
                                        user["telegram_chat_id"],
                                        "trade_success",
                                        user.get("language", "ru"),
                                        {
                                            "token_name": purchase_result["token_name"],
                                            "amount": round(purchase_result["token_amount"], 2),
                                            "price": purchase_result["amount_in_sol"]
                                        }
                                    )
                                
                                # Запланируем продажу токена через некоторое время
                                # В реальности это должно быть более сложным механизмом с проверкой цены
                                # Для примера продаем через 60 секунд
                                threading.Timer(60, sell_token_for_user, args=[user, token_address, purchase_result["token_amount"], Config.TARGET_PROFIT]).start()
            
            # Спим перед следующей проверкой
            time.sleep(Config.CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Ошибка в цикле мониторинга: {str(e)}")
            time.sleep(Config.CHECK_INTERVAL)

# Функция для продажи токена пользователю
def sell_token_for_user(user, token_address, token_amount, target_profit):
    try:
        wallet = {
            "address": user["wallet_address"],
            "private_key": user["wallet_private_key"]
        }
        
        # Продаем токен
        sell_result = sell_token(wallet, token_address, token_amount, target_profit)
        
        if sell_result["success"]:
            # Находим транзакцию покупки
            purchase_transaction = transactions_collection.find_one({
                "user_id": user["_id"],
                "token_address": token_address,
                "status": "bought"
            })
            
            if purchase_transaction:
                # Обновляем транзакцию
                transactions_collection.update_one(
                    {"_id": purchase_transaction["_id"]},
                    {"$set": {
                        "sell_price": sell_result["sol_received"] / token_amount,
                        "sell_amount": token_amount,
                        "profit_percentage": sell_result["profit_percentage"],
                        "status": "sold",
                        "updated_at": datetime.now()
                    }}
                )
                
                # Отправляем сообщение в Telegram
                if "telegram_chat_id" in user and user["telegram_chat_id"]:
                    send_telegram_message(
                        user["telegram_chat_id"],
                        "trade_profit",
                        user.get("language", "ru"),
                        {
                            "token_name": sell_result["token_name"],
                            "profit": sell_result["profit_percentage"]
                        }
                    )
    except Exception as e:
        print(f"Ошибка при продаже токена: {str(e)}")

# Обработчик сообщений Telegram
@telegram_bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        chat_id = message.chat.id
        text = message.text
        
        # Поиск пользователя по chat_id
        user = users_collection.find_one({"telegram_chat_id": str(chat_id)})
        
        if user:
            # Определяем язык пользователя
            language = user.get("language", "ru")
            
            # Отправляем приветственное сообщение
            if text == '/start' or text.lower() in ['привет', 'salom']:
                send_telegram_message(chat_id, "welcome", language)
        else:
            # Если пользователь не найден, отправляем сообщение на русском
            telegram_bot.send_message(chat_id, "Ваш аккаунт не связан с ботом. Обратитесь к администратору.")
    except Exception as e:
        print(f"Ошибка при обработке сообщения Telegram: {str(e)}")

# Создание админа при первом запуске (если его нет)
def create_admin_if_not_exists():
    try:
        admin_exists = users_collection.find_one({"role": "admin"})
        
        if not admin_exists:
            admin_username = os.environ.get("ADMIN_USERNAME", "admin")
            admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
            
            # Создаем хеш пароля
            hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
            
            # Создаем кошелек
            wallet = create_solana_wallet()
            
            # Создаем админа
            admin_user = {
                "username": admin_username,
                "password": hashed_password,
                "role": "admin",
                "wallet_address": wallet["address"],
                "wallet_private_key": wallet["private_key"],
                "active": True,
                "created_at": datetime.now()
            }
            
            users_collection.insert_one(admin_user)
            print("Администратор успешно создан")
    except Exception as e:
        print(f"Ошибка при создании администратора: {str(e)}")

# Запуск сервера
if __name__ == "__main__":
    # Создаем админа, если его нет
    create_admin_if_not_exists()
    
    # Запускаем мониторинг токенов в отдельном потоке
    monitoring_thread = threading.Thread(target=monitor_tokens)
    monitoring_thread.daemon = True
    monitoring_thread.start()
    
    # Запускаем Telegram бота в отдельном потоке
    telegram_thread = threading.Thread(target=telegram_bot.polling, kwargs={"none_stop": True})
    telegram_thread.daemon = True
    telegram_thread.start()
    
    # Запускаем Flask сервер
    app.run(host='0.0.0.0', port=PORT, debug=False)