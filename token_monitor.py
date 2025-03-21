# token_monitor.py - Сервис для мониторинга токенов

import time
import threading
from datetime import datetime
import os
from dotenv import load_dotenv

from models import User, Token, Transaction
import solana_service
import telegram_service

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
MIGRATION_THRESHOLD = int(os.environ.get("MIGRATION_THRESHOLD", 98))
TARGET_PROFIT = int(os.environ.get("TARGET_PROFIT", 10))
PURCHASE_AMOUNT_SOL = float(os.environ.get("PURCHASE_AMOUNT_SOL", 0.05))
MAX_HOLDING_TIME = int(os.environ.get("MAX_HOLDING_TIME", 3600))
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", 5))

# Глобальная переменная для хранения запущенного потока мониторинга
monitoring_thread = None
stop_monitoring = False

def buy_token_for_user(user, token_address, token_name, token_symbol, platform):
    """Функция для покупки токена пользователем"""
    try:
        # Получаем данные кошелька
        wallet_private_key = user["wallet_private_key"]
        
        # Покупаем токен (в реальности это будет вызов к solana_service.buy_token)
        purchase_result = solana_service.buy_token(wallet_private_key, token_address, PURCHASE_AMOUNT_SOL)
        
        if purchase_result["success"]:
            # Создаем запись о транзакции
            transaction_id = Transaction.create_purchase(
                user["_id"],
                token_address,
                token_name,
                token_symbol,
                purchase_result["token_price"],
                purchase_result["token_amount"],
                PURCHASE_AMOUNT_SOL
            )
            
            # Отправляем уведомление в Telegram
            if "telegram_chat_id" in user and user["telegram_chat_id"]:
                telegram_service.notify_token_purchase(
                    user["telegram_chat_id"],
                    token_name,
                    round(purchase_result["token_amount"], 2),
                    PURCHASE_AMOUNT_SOL,
                    user.get("language", "ru")
                )
            
            print(f"Токен {token_name} куплен для пользователя {user['username']}")
            
            # Запланируем продажу токена через некоторое время
            # В реальности нужна проверка цены в реальном времени
            threading.Timer(60, sell_token_for_user, args=[user, token_address, purchase_result["token_amount"], purchase_result["token_price"]]).start()
            
            return True
        
        return False
    
    except Exception as e:
        print(f"Ошибка при покупке токена {token_address} для пользователя {user['username']}: {str(e)}")
        return False

def sell_token_for_user(user, token_address, token_amount, purchase_price):
    """Функция для продажи токена пользователем"""
    try:
        # Получаем данные кошелька
        wallet_private_key = user["wallet_private_key"]
        
        # Получаем информацию о токене
        token_info = Token.find_by_address(token_address)
        token_name = token_info["name"] if token_info else "Unknown Token"
        
        # Продаем токен (в реальности это будет вызов к solana_service.sell_token)
        sell_result = solana_service.sell_token(wallet_private_key, token_address, token_amount, purchase_price)
        
        if sell_result["success"]:
            # Находим транзакцию покупки
            purchase_transaction = Transaction.find_purchase(user["_id"], token_address)
            
            if purchase_transaction:
                # Обновляем транзакцию
                Transaction.update_sale(
                    purchase_transaction["_id"],
                    sell_result["current_price"],
                    token_amount,
                    sell_result["profit_percentage"]
                )
                
                # Отправляем уведомление в Telegram
                if "telegram_chat_id" in user and user["telegram_chat_id"]:
                    telegram_service.notify_token_sale(
                        user["telegram_chat_id"],
                        token_name,
                        round(sell_result["profit_percentage"], 2),
                        user.get("language", "ru")
                    )
                
                print(f"Токен {token_name} продан для пользователя {user['username']} с прибылью {sell_result['profit_percentage']}%")
                
                return True
        
        return False
    
    except Exception as e:
        print(f"Ошибка при продаже токена {token_address} для пользователя {user['username']}: {str(e)}")
        return False

def monitor_tokens():
    """Основная функция для мониторинга токенов"""
    global stop_monitoring
    
    print("Запуск мониторинга токенов...")
    
    # Словарь для отслеживания токенов
    tracked_tokens = {}
    
    # Время последней проверки новых токенов
    last_new_tokens_check = 0
    
    while not stop_monitoring:
        try:
            current_time = time.time()
            
            # Проверяем новые токены каждые 10 секунд
            if current_time - last_new_tokens_check > 10:
                # Получаем новые токены с pump.fun
                pump_tokens = solana_service.get_new_pumpfun_tokens()
                if pump_tokens["success"]:
                    for token in pump_tokens["tokens"]:
                        if token["address"] not in tracked_tokens:
                            # Добавляем токен в БД или обновляем существующий
                            existing_token = Token.find_by_address(token["address"])
                            
                            if not existing_token:
                                Token.create(
                                    token["address"],
                                    token["name"],
                                    token["symbol"],
                                    "pump.fun",
                                    0,
                                    "tracking"
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
                raydium_tokens = solana_service.get_new_raydium_tokens()
                if raydium_tokens["success"]:
                    for token in raydium_tokens["tokens"]:
                        if token["address"] not in tracked_tokens:
                            # Добавляем токен в БД или обновляем существующий
                            existing_token = Token.find_by_address(token["address"])
                            
                            if not existing_token:
                                Token.create(
                                    token["address"],
                                    token["name"],
                                    token["symbol"],
                                    "raydium",
                                    0,
                                    "tracking"
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
                    migration_result = solana_service.check_token_migration(token_address)
                elif token_info["platform"] == "raydium":
                    migration_result = solana_service.check_raydium_token_migration(token_address)
                
                if migration_result and migration_result["success"]:
                    # Обновляем процент миграции
                    token_info["last_migration_percentage"] = migration_result["migration_percentage"]
                    
                    # Обновляем в БД
                    Token.update_migration_percentage(token_address, migration_result["migration_percentage"])
                    
                    print(f"Токен {token_info['name']} ({token_info['symbol']}): миграция {migration_result['migration_percentage']}%")
                    
                    # Если миграция достигла порога, покупаем токен для всех активных пользователей
                    if migration_result["migration_percentage"] >= MIGRATION_THRESHOLD:
                        token_info["status"] = "buying"
                        
                        # Обновляем статус в БД
                        Token.update_status(token_address, "buying")
                        
                        # Получаем всех активных пользователей
                        active_users = User.get_all_active()
                        
                        for user in active_users:
                            # Покупаем токен для пользователя
                            buy_token_for_user(
                                user,
                                token_address,
                                token_info["name"],
                                token_info["symbol"],
                                token_info["platform"]
                            )
                        
                        # Меняем статус токена на "bought"
                        token_info["status"] = "bought"
                        Token.update_status(token_address, "bought")
            
            # Спим перед следующей проверкой
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Ошибка в цикле мониторинга: {str(e)}")
            time.sleep(CHECK_INTERVAL)

def start_monitoring():
    """Запуск мониторинга токенов в отдельном потоке"""
    global monitoring_thread, stop_monitoring
    
    if monitoring_thread is None or not monitoring_thread.is_alive():
        stop_monitoring = False
        monitoring_thread = threading.Thread(target=monitor_tokens)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        return True
    
    return False

def stop_monitoring_thread():
    """Остановка мониторинга токенов"""
    global stop_monitoring
    
    stop_monitoring = True
    
    # Ждем завершения потока
    if monitoring_thread and monitoring_thread.is_alive():
        monitoring_thread.join(timeout=10)
        return True
    
    return False

# Экспортируем функции для использования в других модулях
__all__ = [
    'start_monitoring',
    'stop_monitoring_thread',
    'buy_token_for_user',
    'sell_token_for_user'
]