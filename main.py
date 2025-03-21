# main.py - Главный файл для запуска приложения

import os
import threading
import signal
import sys
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Импорт модулей приложения
from app import app
import telegram_service
import token_monitor

# Обработчик сигналов для корректного завершения приложения
def signal_handler(sig, frame):
    print("\nОстановка приложения...")
    # Останавливаем мониторинг токенов
    token_monitor.stop_monitoring_thread()
    sys.exit(0)

# Регистрируем обработчик сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Получаем порт из переменных окружения или используем 5000 по умолчанию
    port = int(os.environ.get("PORT", 5000))
    
    # Запускаем мониторинг токенов в отдельном потоке
    token_monitor.start_monitoring()
    print("Мониторинг токенов запущен.")
    
    # Запускаем Telegram бота в отдельном потоке
    telegram_thread = threading.Thread(target=telegram_service.start_bot)
    telegram_thread.daemon = True
    telegram_thread.start()
    print("Telegram бот запущен.")
    
    # Запускаем Flask сервер
    print(f"Сервер запущен на порту {port}. Нажмите Ctrl+C для остановки.")
    app.run(host='0.0.0.0', port=port, debug=False)