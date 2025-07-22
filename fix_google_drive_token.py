#!/usr/bin/env python3
"""
Исправление проблемы с token.pickle для Google Drive в Google Colab
"""
import os
import sys
import logging
import pickle
import shutil
from pathlib import Path
import base64
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/content/videobot/logs/token_fix.log')
    ]
)
logger = logging.getLogger(__name__)

def fix_token_pickle():
    """
    Исправляет проблему с token.pickle для Google Drive
    
    1. Проверяет наличие token.pickle
    2. Если файл существует, копирует его в нужные места
    3. Если файла нет, пытается создать его из token.pickle.b64
    """
    logger.info("🔧 Начинаем исправление проблемы с token.pickle")
    
    # Пути к файлам
    source_token = Path("token.pickle")
    b64_token = Path("token.pickle.b64")
    target_paths = [
        Path("/content/videobot/token.pickle"),
        Path("app/token.pickle")
    ]
    
    # 1. Проверяем наличие token.pickle
    if source_token.exists():
        logger.info(f"✅ Найден файл token.pickle ({source_token.stat().st_size} байт)")
        
        # Проверяем валидность файла
        try:
            with open(source_token, 'rb') as f:
                token_data = pickle.load(f)
            logger.info(f"✅ Файл token.pickle успешно загружен")
            
            # Выводим информацию о токене
            if hasattr(token_data, 'valid'):
                logger.info(f"✅ Токен валиден: {token_data.valid}")
            if hasattr(token_data, 'expired'):
                logger.info(f"⏱️ Токен истек: {token_data.expired}")
            if hasattr(token_data, 'token_uri'):
                logger.info(f"🔗 URI токена: {token_data.token_uri}")
            if hasattr(token_data, 'scopes'):
                logger.info(f"🔑 Области токена: {token_data.scopes}")
        except Exception as e:
            logger.error(f"❌ Ошибка проверки token.pickle: {e}")
            logger.info("⚠️ Файл token.pickle поврежден, попробуем восстановить из token.pickle.b64")
            source_token = None
    else:
        logger.warning("⚠️ Файл token.pickle не найден")
        source_token = None
    
    # 2. Если token.pickle не найден или поврежден, пытаемся создать его из token.pickle.b64
    if source_token is None and b64_token.exists():
        logger.info(f"🔄 Пытаемся создать token.pickle из token.pickle.b64")
        
        try:
            # Читаем base64 данные
            with open(b64_token, 'r') as f:
                b64_data = f.read().strip()
            
            # Декодируем base64 в бинарные данные
            binary_data = base64.b64decode(b64_data)
            
            # Записываем в token.pickle
            with open("token.pickle", 'wb') as f:
                f.write(binary_data)
            
            logger.info(f"✅ Файл token.pickle успешно создан из token.pickle.b64")
            source_token = Path("token.pickle")
            
            # Проверяем валидность созданного файла
            try:
                with open(source_token, 'rb') as f:
                    token_data = pickle.load(f)
                logger.info(f"✅ Созданный token.pickle успешно загружен")
            except Exception as e:
                logger.error(f"❌ Ошибка проверки созданного token.pickle: {e}")
                source_token = None
        except Exception as e:
            logger.error(f"❌ Ошибка создания token.pickle из token.pickle.b64: {e}")
            source_token = None
    
    # 3. Копируем token.pickle в нужные места
    if source_token:
        for target_path in target_paths:
            try:
                # Создаем директорию если нужно
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Копируем файл
                shutil.copy2(source_token, target_path)
                logger.info(f"✅ Скопировано token.pickle в {target_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка копирования token.pickle в {target_path}: {e}")
    else:
        logger.error("❌ Не удалось найти или создать валидный token.pickle")
        return False
    
    return True

def fix_google_drive_service():
    """
    Исправляет GoogleDriveService для корректной работы с token.pickle
    
    1. Проверяет наличие файла app/services/google_drive.py
    2. Модифицирует код для правильной обработки token.pickle
    """
    logger.info("🔧 Исправляем GoogleDriveService для корректной работы с token.pickle")
    
    service_file = Path("app/services/google_drive.py")
    
    if not service_file.exists():
        logger.error(f"❌ Файл {service_file} не найден")
        return False
    
    try:
        # Читаем файл
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, нужно ли исправление
        if "token_path = \"token.pickle\"" in content and "if not creds:" in content:
            logger.info("🔍 Найден код, требующий исправления")
            
            # Заменяем путь к token.pickle
            content = content.replace(
                'token_path = "token.pickle"',
                'token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "token.pickle")'
            )
            
            # Добавляем больше логирования
            content = content.replace(
                "logger.info(\"Loaded existing OAuth credentials from token.pickle\")",
                "logger.info(f\"Loaded existing OAuth credentials from {token_path} (size: {os.path.getsize(token_path) if os.path.exists(token_path) else 'N/A'} bytes)\")"
            )
            
            # Улучшаем обработку ошибок
            content = content.replace(
                "logger.error(f\"Failed to load OAuth token: {e}\")",
                "logger.error(f\"Failed to load OAuth token from {token_path}: {e}\")"
            )
            
            # Сохраняем изменения
            with open(service_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ GoogleDriveService успешно исправлен")
            return True
        else:
            logger.info("✅ GoogleDriveService не требует исправления или имеет нестандартную структуру")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка исправления GoogleDriveService: {e}")
        return False

def check_google_drive_integration():
    """
    Проверяет интеграцию с Google Drive
    
    1. Проверяет наличие необходимых библиотек
    2. Проверяет наличие token.pickle
    3. Проверяет наличие google-credentials.json
    4. Тестирует подключение к Google Drive
    """
    logger.info("🔍 Проверка интеграции с Google Drive")
    
    # 1. Проверяем наличие необходимых библиотек
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        logger.info("✅ Необходимые библиотеки установлены")
    except ImportError as e:
        logger.error(f"❌ Отсутствуют необходимые библиотеки: {e}")
        logger.info("💡 Установите необходимые библиотеки: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return False
    
    # 2. Проверяем наличие token.pickle
    token_paths = [
        Path("token.pickle"),
        Path("/content/videobot/token.pickle"),
        Path("app/token.pickle")
    ]
    
    token_found = False
    for token_path in token_paths:
        if token_path.exists():
            logger.info(f"✅ Найден token.pickle: {token_path} ({token_path.stat().st_size} байт)")
            token_found = True
            
            # Проверяем валидность файла
            try:
                with open(token_path, 'rb') as f:
                    token_data = pickle.load(f)
                logger.info(f"✅ Файл {token_path} успешно загружен")
            except Exception as e:
                logger.error(f"❌ Ошибка проверки {token_path}: {e}")
    
    if not token_found:
        logger.error("❌ Файл token.pickle не найден ни в одном из ожидаемых мест")
        return False
    
    # 3. Проверяем наличие google-credentials.json
    creds_path = Path("google-credentials.json")
    if creds_path.exists():
        logger.info(f"✅ Найден google-credentials.json ({creds_path.stat().st_size} байт)")
    else:
        logger.warning("⚠️ Файл google-credentials.json не найден")
    
    # 4. Тестируем подключение к Google Drive
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = None
        token_path = "token.pickle"
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("🔄 Обновляем истекший токен...")
                creds.refresh(Request())
                
                # Сохраняем обновленный токен
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("✅ Токен успешно обновлен и сохранен")
            else:
                logger.error("❌ Нет валидных учетных данных")
                return False
        
        # Тестируем подключение
        service = build('drive', 'v3', credentials=creds)
        
        # Простой запрос для проверки подключения
        results = service.files().list(pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        # Получаем информацию о пользователе
        about = service.about().get(fields="user").execute()
        user_info = about.get('user', {})
        
        logger.info("✅ Подключение к Google Drive успешно установлено!")
        logger.info(f"👤 Пользователь: {user_info.get('emailAddress', 'N/A')}")
        logger.info(f"📁 Доступ к файлам: {len(files) > 0}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Google Drive: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("🔧 VideoGenerator3000 - Google Drive Token Fix")
    logger.info("=" * 50)
    
    # Исправляем token.pickle
    token_fixed = fix_token_pickle()
    
    # Исправляем GoogleDriveService
    service_fixed = fix_google_drive_service()
    
    # Проверяем интеграцию с Google Drive
    integration_ok = check_google_drive_integration()
    
    logger.info("=" * 50)
    logger.info("📊 РЕЗУЛЬТАТЫ:")
    logger.info(f"✅ Исправление token.pickle: {'Успешно' if token_fixed else 'Ошибка'}")
    logger.info(f"✅ Исправление GoogleDriveService: {'Успешно' if service_fixed else 'Ошибка'}")
    logger.info(f"✅ Интеграция с Google Drive: {'Работает' if integration_ok else 'Не работает'}")
    
    if token_fixed and service_fixed and integration_ok:
        logger.info("🎉 Все проблемы с Google Drive успешно решены!")
    else:
        logger.info("⚠️ Некоторые проблемы с Google Drive остались нерешенными.")
        logger.info("💡 Рекомендации:")
        if not token_fixed:
            logger.info("1. Создайте новый token.pickle: python setup_oauth.py")
        if not service_fixed:
            logger.info("2. Проверьте код в app/services/google_drive.py")
        if not integration_ok:
            logger.info("3. Проверьте подключение к Google Drive: python test_google_drive.py")

if __name__ == "__main__":
    main() 