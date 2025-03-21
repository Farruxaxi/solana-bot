# models.py - Модели данных для проекта

from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Подключение к MongoDB
client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017/"))
db = client["solana_bot_db"]

class User:
    """Модель пользователя"""
    
    collection = db["users"]
    
    @staticmethod
    def create(username, password_hash, role="user", wallet_address=None, wallet_private_key=None, 
               telegram_chat_id=None, language="ru", active=True):
        """Создание нового пользователя"""
        user_data = {
            "username": username,
            "password": password_hash,
            "role": role,
            "wallet_address": wallet_address,
            "wallet_private_key": wallet_private_key,
            "telegram_chat_id": telegram_chat_id,
            "language": language,
            "active": active,
            "created_at": datetime.now()
        }
        
        result = User.collection.insert_one(user_data)
        return result.inserted_id
    
    @staticmethod
    def find_by_username(username):
        """Поиск пользователя по имени"""
        return User.collection.find_one({"username": username})
    
    @staticmethod
    def find_by_telegram_chat_id(chat_id):
        """Поиск пользователя по Telegram chat ID"""
        return User.collection.find_one({"telegram_chat_id": str(chat_id)})
    
    @staticmethod
    def find_by_id(user_id):
        """Поиск пользователя по ID"""
        return User.collection.find_one({"_id": user_id})
    
    @staticmethod
    def get_all_active():
        """Получение всех активных пользователей"""
        return list(User.collection.find({"active": True}))
    
    @staticmethod
    def update(user_id, data):
        """Обновление данных пользователя"""
        User.collection.update_one({"_id": user_id}, {"$set": data})
    
    @staticmethod
    def deactivate(user_id):
        """Деактивация пользователя"""
        User.collection.update_one({"_id": user_id}, {"$set": {"active": False}})
    
    @staticmethod
    def activate(user_id):
        """Активация пользователя"""
        User.collection.update_one({"_id": user_id}, {"$set": {"active": True}})

class Token:
    """Модель токена"""
    
    collection = db["tokens"]
    
    @staticmethod
    def create(address, name, symbol, platform, last_migration_percentage=0, status="tracking"):
        """Создание новой записи о токене"""
        token_data = {
            "address": address,
            "name": name,
            "symbol": symbol,
            "platform": platform,
            "last_migration_percentage": last_migration_percentage,
            "status": status,
            "time_added": datetime.now(),
            "last_updated": datetime.now()
        }
        
        result = Token.collection.insert_one(token_data)
        return result.inserted_id
    
    @staticmethod
    def find_by_address(address):
        """Поиск токена по адресу"""
        return Token.collection.find_one({"address": address})
    
    @staticmethod
    def update_migration_percentage(address, percentage):
        """Обновление процента миграции токена"""
        Token.collection.update_one(
            {"address": address},
            {
                "$set": {
                    "last_migration_percentage": percentage,
                    "last_updated": datetime.now()
                }
            }
        )
    
    @staticmethod
    def update_status(address, status):
        """Обновление статуса токена"""
        Token.collection.update_one(
            {"address": address},
            {
                "$set": {
                    "status": status,
                    "last_updated": datetime.now()
                }
            }
        )
    
    @staticmethod
    def get_tracking_tokens():
        """Получение всех отслеживаемых токенов"""
        return list(Token.collection.find({"status": "tracking"}))
    
    @staticmethod
    def get_all():
        """Получение всех токенов"""
        return list(Token.collection.find())

class Transaction:
    """Модель транзакции покупки/продажи токена"""
    
    collection = db["transactions"]
    
    @staticmethod
    def create_purchase(user_id, token_address, token_name, token_symbol, purchase_price, 
                      purchase_amount, purchase_sol):
        """Создание новой записи о покупке токена"""
        transaction_data = {
            "user_id": user_id,
            "token_address": token_address,
            "token_name": token_name,
            "token_symbol": token_symbol,
            "purchase_price": purchase_price,
            "purchase_amount": purchase_amount,
            "purchase_sol": purchase_sol,
            "status": "bought",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = Transaction.collection.insert_one(transaction_data)
        return result.inserted_id
    
    @staticmethod
    def update_sale(transaction_id, sell_price, sell_amount, profit_percentage):
        """Обновление транзакции после продажи токена"""
        Transaction.collection.update_one(
            {"_id": transaction_id},
            {
                "$set": {
                    "sell_price": sell_price,
                    "sell_amount": sell_amount,
                    "profit_percentage": profit_percentage,
                    "status": "sold",
                    "updated_at": datetime.now()
                }
            }
        )
    
    @staticmethod
    def find_purchase(user_id, token_address):
        """Поиск записи о покупке токена для пользователя"""
        return Transaction.collection.find_one({
            "user_id": user_id,
            "token_address": token_address,
            "status": "bought"
        })
    
    @staticmethod
    def get_user_transactions(user_id):
        """Получение всех транзакций пользователя"""
        return list(Transaction.collection.find({"user_id": user_id}).sort("created_at", -1))
    
    @staticmethod
    def get_user_stats(user_id):
        """Получение статистики торговли пользователя"""
        all_transactions = list(Transaction.collection.find({"user_id": user_id}))
        
        total_trades = len(all_transactions)
        successful_trades = len([t for t in all_transactions if t.get("status") == "sold" and t.get("profit_percentage", 0) > 0])
        
        total_profit_sol = 0
        for t in all_transactions:
            if t.get("status") == "sold" and "sell_price" in t and "sell_amount" in t and "purchase_price" in t and "purchase_amount" in t:
                total_profit_sol += (t["sell_price"] * t["sell_amount"]) - (t["purchase_price"] * t["purchase_amount"])
        
        return {
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "total_profit": round(total_profit_sol, 4)
        }

# Экспортируем классы для использования в других модулях
__all__ = [
    'User',
    'Token',
    'Transaction'
]