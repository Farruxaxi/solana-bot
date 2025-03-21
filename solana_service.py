# solana_service.py - Сервис для работы с Solana блокчейном

import base58
import json
import requests
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.system_program import SYS_PROGRAM_ID, TransferParams, transfer
from solders.instruction import Instruction
from base58 import b58encode, b58decode
import time
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Инициализация клиента Solana
solana_client = Client(os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"))

# Функция для получения баланса кошелька
def get_wallet_balance(wallet_address):
    try:
        response = solana_client.get_balance(PublicKey(wallet_address))
        balance_lamports = response['result']['value']
        balance_sol = balance_lamports / 1_000_000_000  # 1 SOL = 1,000,000,000 lamports
        return {
            "success": True,
            "balance_lamports": balance_lamports,
            "balance_sol": balance_sol
        }
    except Exception as e:
        print(f"Ошибка при получении баланса кошелька {wallet_address}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Функция для проверки миграции токена на pump.fun
def check_token_migration(token_address):
    try:
        # URL API pump.fun (заменить на реальный URL)
        api_url = f"https://api.pump.fun/tokens/{token_address}"
        
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            if "migrationPercentage" in data:
                return {
                    "success": True,
                    "migration_percentage": data["migrationPercentage"],
                    "above_threshold": data["migrationPercentage"] >= 98
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
            if "migrationPercentage" in data:
                return {
                    "success": True,
                    "migration_percentage": data["migrationPercentage"],
                    "above_threshold": data["migrationPercentage"] >= 98
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
            if isinstance(data, list):
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
            if isinstance(data, list):
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

# Функция для отправки транзакции SOL
def send_sol(from_private_key, to_address, amount_sol):
    try:
        # Создаем keypair из приватного ключа
        keypair = Keypair.from_secret_key(b58decode(from_private_key))
        
        # Преобразуем SOL в lamports
        amount_lamports = int(amount_sol * 1_000_000_000)
        
        # Создаем инструкцию перевода
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=keypair.public_key,
                to_pubkey=PublicKey(to_address),
                lamports=amount_lamports
            )
        )
        
        # Создаем транзакцию
        transaction = Transaction().add(transfer_ix)
        
        # Получаем последний блокхеш
        recent_blockhash = solana_client.get_recent_blockhash()['result']['value']['blockhash']
        transaction.recent_blockhash = recent_blockhash
        
        # Подписываем транзакцию
        transaction.sign(keypair)
        
        # Отправляем транзакцию
        response = solana_client.send_transaction(transaction)
        
        return {
            "success": True,
            "signature": response['result'],
            "amount_sol": amount_sol
        }
    except Exception as e:
        print(f"Ошибка при отправке SOL: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Функция для покупки токена (упрощенная симуляция)
def buy_token(wallet_private_key, token_address, amount_in_sol):
    try:
        # В реальном сценарии здесь будет логика взаимодействия с DEX
        # Для этого примера мы просто симулируем покупку
        
        # Получаем информацию о токене (в реальности запрос к API)
        token_info = {
            "name": "Sample Token",
            "symbol": "SMPL",
            "decimals": 9
        }
        
        # Симуляция цены токена
        token_price = 0.0001  # SOL за токен
        
        # Рассчитываем количество токенов
        token_amount = amount_in_sol / token_price
        
        # В реальном сценарии здесь был бы код для отправки транзакции
        # на контракт DEX для свапа SOL на токен
        
        return {
            "success": True,
            "token_address": token_address,
            "token_name": token_info["name"],
            "token_symbol": token_info["symbol"],
            "amount_in_sol": amount_in_sol,
            "token_amount": token_amount,
            "token_price": token_price,
            "transaction_signature": "SimulatedSignature"
        }
    except Exception as e:
        print(f"Ошибка при покупке токена {token_address}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Функция для продажи токена (упрощенная симуляция)
def sell_token(wallet_private_key, token_address, token_amount, purchase_price):
    try:
        # В реальном сценарии здесь будет логика взаимодействия с DEX
        # Для этого примера мы просто симулируем продажу
        
        # Получаем информацию о токене
        token_info = {
            "name": "Sample Token",
            "symbol": "SMPL",
            "decimals": 9
        }
        
        # Симуляция текущей цены токена с прибылью 10%
        current_price = purchase_price * 1.1
        
        # Рассчитываем количество SOL, полученных от продажи
        sol_received = token_amount * current_price
        
        # Рассчитываем процент прибыли
        profit_percentage = ((current_price - purchase_price) / purchase_price) * 100
        
        # В реальном сценарии здесь был бы код для отправки транзакции
        # на контракт DEX для свапа токена на SOL
        
        return {
            "success": True,
            "token_address": token_address,
            "token_name": token_info["name"],
            "token_symbol": token_info["symbol"],
            "token_amount": token_amount,
            "purchase_price": purchase_price,
            "current_price": current_price,
            "sol_received": sol_received,
            "profit_percentage": profit_percentage,
            "transaction_signature": "SimulatedSignature"
        }
    except Exception as e:
        print(f"Ошибка при продаже токена {token_address}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Функция для получения всех SPL-токенов на кошельке
def get_token_accounts(wallet_address):
    try:
        response = solana_client.get_token_accounts_by_owner(
            PublicKey(wallet_address),
            {"programId": PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}  # SPL Token Program ID
        )
        
        token_accounts = []
        for account in response['result']['value']:
            token_accounts.append({
                "pubkey": account['pubkey'],
                "account": account['account'],
                "mint": account['account']['data']['parsed']['info']['mint'],
                "owner": account['account']['data']['parsed']['info']['owner'],
                "amount": int(account['account']['data']['parsed']['info']['tokenAmount']['amount']),
                "decimals": account['account']['data']['parsed']['info']['tokenAmount']['decimals'],
                "uiAmount": account['account']['data']['parsed']['info']['tokenAmount']['uiAmount']
            })
        
        return {
            "success": True,
            "token_accounts": token_accounts
        }
    except Exception as e:
        print(f"Ошибка при получении SPL токенов кошелька {wallet_address}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Экспортируем функции для использования в других модулях
__all__ = [
    'get_wallet_balance',
    'check_token_migration',
    'check_raydium_token_migration',
    'get_new_pumpfun_tokens',
    'get_new_raydium_tokens',
    'send_sol',
    'buy_token',
    'sell_token',
    'get_token_accounts'
]