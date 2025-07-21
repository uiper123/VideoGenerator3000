#!/usr/bin/env python3
"""
Тестирование Google Drive интеграции и токена
"""
import os
import pickle
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_token_pickle():
    """Тестирует token.pickle файл"""
    print("🔍 Проверка token.pickle...")
    
    token_path = "token.pickle"
    
    if not os.path.exists(token_path):
        print("❌ Файл token.pickle не найден!")
        print("💡 Создайте токен с помощью setup_oauth.py")
        return False
    
    try:
        with open(token_path, 'rb') as token_file:
            creds = pickle.load(token_file)
        
        print(f"✅ Файл token.pickle загружен")
        print(f"📋 Тип токена: {type(creds)}")
        
        # Проверяем свойства токена
        if hasattr(creds, 'valid'):
            print(f"🔐 Токен валидный: {creds.valid}")
        
        if hasattr(creds, 'expired'):
            print(f"⏰ Токен истек: {creds.expired}")
        
        if hasattr(creds, 'expiry'):
            if creds.expiry:
                print(f"📅 Истекает: {creds.expiry}")
                hours_left = (creds.expiry - datetime.utcnow()).total_seconds() / 3600
                if hours_left > 0:
                    print(f"⏳ Осталось: {hours_left:.1f} часов")
                else:
                    print(f"⚠️ Истек {abs(hours_left):.1f} часов назад")
        
        if hasattr(creds, 'scopes'):
            print(f"🔑 Разрешения: {creds.scopes}")
        
        if hasattr(creds, 'refresh_token'):
            has_refresh = bool(creds.refresh_token)
            print(f"🔄 Refresh token: {'Есть' if has_refresh else 'Нет'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка чтения token.pickle: {e}")
        return False

def test_google_drive_connection():
    """Тестирует подключение к Google Drive"""
    print("\n🔗 Тестирование подключения к Google Drive...")
    
    try:
        # Импортируем Google библиотеки
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        
        print("✅ Google библиотеки доступны")
        
    except ImportError as e:
        print(f"❌ Google библиотеки не установлены: {e}")
        print("💡 Установите: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return False
    
    # Загружаем токен
    token_path = "token.pickle"
    if not os.path.exists(token_path):
        print("❌ token.pickle не найден")
        return False
    
    try:
        with open(token_path, 'rb') as token_file:
            creds = pickle.load(token_file)
        
        # Проверяем и обновляем токен если нужно
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Обновляем истекший токен...")
                creds.refresh(Request())
                
                # Сохраняем обновленный токен
                with open(token_path, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                print("✅ Токен обновлен и сохранен")
            else:
                print("❌ Токен недействителен и не может быть обновлен")
                return False
        
        # Тестируем API
        print("🔗 Подключаемся к Google Drive API...")
        service = build('drive', 'v3', credentials=creds)
        
        # Простой запрос для проверки
        print("📋 Получаем информацию о пользователе...")
        about = service.about().get(fields="user,storageQuota").execute()
        
        user_info = about.get('user', {})
        storage_info = about.get('storageQuota', {})
        
        print(f"✅ Подключение успешно!")
        print(f"👤 Пользователь: {user_info.get('displayName', 'N/A')}")
        print(f"📧 Email: {user_info.get('emailAddress', 'N/A')}")
        
        # Информация о хранилище
        if storage_info:
            limit = int(storage_info.get('limit', 0))
            usage = int(storage_info.get('usage', 0))
            
            if limit > 0:
                used_gb = usage / (1024**3)
                total_gb = limit / (1024**3)
                free_gb = total_gb - used_gb
                usage_percent = (usage / limit) * 100
                
                print(f"💾 Хранилище: {used_gb:.1f}GB / {total_gb:.1f}GB ({usage_percent:.1f}%)")
                print(f"📁 Свободно: {free_gb:.1f}GB")
                
                if usage_percent > 90:
                    print("⚠️ Внимание: Хранилище почти заполнено!")
                elif usage_percent > 95:
                    print("🚨 Критично: Хранилище переполнено!")
        
        # Тестируем создание папки
        print("\n📁 Тестируем создание папки...")
        test_folder_name = f"VideoBot_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        folder_metadata = {
            'name': test_folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(body=folder_metadata, fields='id,name').execute()
        folder_id = folder.get('id')
        
        print(f"✅ Тестовая папка создана: {folder.get('name')} (ID: {folder_id})")
        
        # Удаляем тестовую папку
        service.files().delete(fileId=folder_id).execute()
        print("🗑️ Тестовая папка удалена")
        
        return True
        
    except HttpError as e:
        print(f"❌ Google Drive API ошибка: {e}")
        if e.resp.status == 403:
            print("💡 Возможно, превышена квота API или нет разрешений")
        elif e.resp.status == 401:
            print("💡 Проблема с авторизацией, попробуйте пересоздать токен")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_upload_function():
    """Тестирует функцию загрузки из кода бота"""
    print("\n🧪 Тестирование функции загрузки бота...")
    
    try:
        # Импортируем сервис из бота
        from app.services.google_drive import GoogleDriveService
        
        print("✅ GoogleDriveService импортирован")
        
        # Создаем экземпляр сервиса
        drive_service = GoogleDriveService()
        
        if drive_service.credentials:
            print("✅ Сервис инициализирован с токеном")
            print(f"🔐 Тип авторизации: {getattr(drive_service, 'auth_type', 'unknown')}")
            
            # Проверяем метод загрузки
            if hasattr(drive_service, 'upload_multiple_files'):
                print("✅ Метод upload_multiple_files доступен")
            else:
                print("❌ Метод upload_multiple_files не найден")
            
            return True
        else:
            print("❌ Сервис не смог загрузить токен")
            return False
            
    except ImportError as e:
        print(f"❌ Не удалось импортировать GoogleDriveService: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка тестирования сервиса: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 VideoGenerator3000 - Google Drive Test")
    print("=" * 50)
    
    # Проверяем рабочую директорию
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"📋 Файлы в директории:")
    for file in os.listdir('.'):
        if file.endswith(('.pickle', '.json', '.py')):
            print(f"   - {file}")
    
    print("\n" + "=" * 50)
    
    # Тест 1: Проверка token.pickle
    token_ok = test_token_pickle()
    
    # Тест 2: Подключение к Google Drive
    if token_ok:
        connection_ok = test_google_drive_connection()
    else:
        connection_ok = False
    
    # Тест 3: Функция загрузки бота
    upload_ok = test_upload_function()
    
    # Итоговый результат
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"🔐 Token.pickle: {'✅ OK' if token_ok else '❌ FAIL'}")
    print(f"🔗 Google Drive API: {'✅ OK' if connection_ok else '❌ FAIL'}")
    print(f"🧪 Upload функция: {'✅ OK' if upload_ok else '❌ FAIL'}")
    
    if all([token_ok, connection_ok, upload_ok]):
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ! Google Drive готов к работе!")
        return True
    else:
        print("\n❌ ЕСТЬ ПРОБЛЕМЫ! Проверьте ошибки выше.")
        
        if not token_ok:
            print("💡 Создайте новый токен: python setup_oauth.py")
        if not connection_ok:
            print("💡 Проверьте интернет и разрешения Google Drive")
        if not upload_ok:
            print("💡 Проверьте код GoogleDriveService")
        
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)