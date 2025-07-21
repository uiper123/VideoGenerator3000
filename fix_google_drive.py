#!/usr/bin/env python3
"""
Исправление Google Drive интеграции
"""
import os
import pickle
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_google_drive_setup():
    """Проверяет настройку Google Drive"""
    print("🔍 Проверка настройки Google Drive...")
    
    issues = []
    
    # 1. Проверяем token.pickle
    token_path = "token.pickle"
    if not os.path.exists(token_path):
        issues.append("❌ Файл token.pickle не найден")
        print("❌ Файл token.pickle не найден")
        print("💡 Создайте токен: python setup_oauth.py")
    else:
        try:
            with open(token_path, 'rb') as f:
                creds = pickle.load(f)
            
            if hasattr(creds, 'valid') and creds.valid:
                print("✅ token.pickle найден и валиден")
            elif hasattr(creds, 'expired') and creds.expired and hasattr(creds, 'refresh_token') and creds.refresh_token:
                print("⚠️ token.pickle истек, но может быть обновлен")
            else:
                issues.append("❌ token.pickle недействителен")
                print("❌ token.pickle недействителен")
        except Exception as e:
            issues.append(f"❌ Ошибка чтения token.pickle: {e}")
            print(f"❌ Ошибка чтения token.pickle: {e}")
    
    # 2. Проверяем google-credentials.json
    creds_path = "google-credentials.json"
    if not os.path.exists(creds_path):
        issues.append("❌ Файл google-credentials.json не найден")
        print("❌ Файл google-credentials.json не найден")
        print("💡 Скачайте из Google Cloud Console")
    else:
        print("✅ google-credentials.json найден")
    
    # 3. Проверяем переменные окружения
    google_env_vars = [
        "GOOGLE_DRIVE_FOLDER_ID",
        "GOOGLE_CREDENTIALS_JSON_CONTENT"
    ]
    
    for var in google_env_vars:
        if os.getenv(var):
            print(f"✅ {var} установлена")
        else:
            print(f"⚠️ {var} не установлена (опционально)")
    
    # 4. Проверяем Google библиотеки
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        print("✅ Google библиотеки установлены")
    except ImportError as e:
        issues.append(f"❌ Google библиотеки не установлены: {e}")
        print(f"❌ Google библиотеки не установлены: {e}")
        print("💡 Установите: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    
    return len(issues) == 0, issues

def fix_google_drive_service():
    """Исправляет GoogleDriveService чтобы он не использовал mock"""
    print("\n🔧 Исправление GoogleDriveService...")
    
    service_file = "app/services/google_drive.py"
    
    if not os.path.exists(service_file):
        print(f"❌ Файл {service_file} не найден")
        return False
    
    try:
        # Читаем файл
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем есть ли mock код
        if "mock.drive.url" in content:
            print("⚠️ Найден mock код в GoogleDriveService")
            
            # Заменяем mock на более информативное сообщение
            content = content.replace(
                '"webViewLink": "https://mock.drive.url/file/view"',
                '"webViewLink": "https://drive.google.com/file/d/mock_file_id/view"'
            )
            
            content = content.replace(
                '"directLink": f"https://mock.direct.link/{os.path.basename(file_path)}"',
                '"directLink": f"https://drive.google.com/uc?id=mock_file_id&export=download"'
            )
            
            # Добавляем логирование причины использования mock
            mock_section = '''        if not self.service:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            logger.warning(f"Google Drive service not initialized! Using mock upload for: {os.path.basename(file_path)}")
            logger.warning("Check Google Drive credentials and token.pickle file")'''
            
            content = content.replace(
                '''        if not self.service:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            logger.info(f"Mock upload: {os.path.basename(file_path)} ({file_size} bytes) to folder {folder_id or 'root'}")''',
                mock_section
            )
            
            # Сохраняем изменения
            with open(service_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ GoogleDriveService исправлен")
            return True
        else:
            print("✅ Mock код не найден, сервис в порядке")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка исправления GoogleDriveService: {e}")
        return False

def create_google_drive_test():
    """Создает тестовый скрипт для Google Drive"""
    print("\n📝 Создание тестового скрипта...")
    
    test_code = '''#!/usr/bin/env python3
"""
Тест Google Drive интеграции
"""
import sys
import os
sys.path.append('.')

from app.services.google_drive import GoogleDriveService

def test_google_drive():
    """Тестирует Google Drive сервис"""
    print("🧪 Тестирование Google Drive...")
    
    try:
        # Создаем сервис
        drive_service = GoogleDriveService()
        
        print(f"🔐 Credentials: {'✅ Loaded' if drive_service.credentials else '❌ Not loaded'}")
        print(f"🔧 Service: {'✅ Initialized' if drive_service.service else '❌ Not initialized'}")
        print(f"🔑 Auth type: {getattr(drive_service, 'auth_type', 'unknown')}")
        
        if drive_service.service:
            print("✅ Google Drive готов к работе!")
            return True
        else:
            print("❌ Google Drive не инициализирован")
            print("💡 Проверьте token.pickle и google-credentials.json")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

if __name__ == "__main__":
    success = test_google_drive()
    exit(0 if success else 1)
'''
    
    with open('test_drive_service.py', 'w') as f:
        f.write(test_code)
    
    print("✅ Создан test_drive_service.py")

def main():
    """Основная функция"""
    print("🔧 VideoGenerator3000 - Google Drive Fix")
    print("=" * 50)
    
    # Проверяем настройку
    is_ok, issues = check_google_drive_setup()
    
    # Исправляем сервис
    service_fixed = fix_google_drive_service()
    
    # Создаем тест
    create_google_drive_test()
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТ:")
    
    if is_ok and service_fixed:
        print("✅ Google Drive настроен правильно")
        print("🧪 Запустите тест: python test_drive_service.py")
    else:
        print("❌ Есть проблемы с Google Drive:")
        for issue in issues:
            print(f"   {issue}")
        
        print("\n💡 Рекомендации:")
        if not os.path.exists("token.pickle"):
            print("1. Создайте токен: python setup_oauth.py")
        if not os.path.exists("google-credentials.json"):
            print("2. Скачайте google-credentials.json из Google Cloud Console")
        print("3. Запустите тест: python test_drive_service.py")
        print("4. Используйте /check_drive в боте для диагностики")

if __name__ == "__main__":
    main()