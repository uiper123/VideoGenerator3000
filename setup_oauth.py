#!/usr/bin/env python3
"""
Setup script for OAuth 2.0 authentication with Google Drive.
This script helps you authenticate your personal Google account.
"""
import os
import sys
import logging
from urllib.parse import urlparse, parse_qs
import webbrowser

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.google_drive import get_oauth_authorization_url, handle_oauth_callback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_oauth():
    """Setup OAuth 2.0 authentication."""
    print("🔐 Настройка OAuth 2.0 для Google Drive")
    print("=" * 50)
    
    # Check if environment variables are set
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ Ошибка: Переменные окружения не настроены!")
        print()
        print("Необходимо настроить:")
        print("GOOGLE_OAUTH_CLIENT_ID=your_client_id")
        print("GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret")
        print()
        print("Получить их можно в Google Cloud Console:")
        print("1. Перейдите на https://console.cloud.google.com/")
        print("2. Выберите или создайте проект")
        print("3. Включите Google Drive API")
        print("4. Создайте OAuth 2.0 credentials")
        print("5. Скачайте JSON или скопируйте Client ID и Secret")
        return False
    
    print("✅ Переменные окружения настроены")
    print(f"Client ID: {client_id[:20]}...")
    print()
    
    try:
        # Get authorization URL
        auth_url = get_oauth_authorization_url()
        if not auth_url:
            print("❌ Не удалось создать URL авторизации")
            return False
        
        print("📱 Откройте эту ссылку в браузере для авторизации:")
        print()
        print(auth_url)
        print()
        
        # Try to open browser automatically
        try:
            webbrowser.open(auth_url)
            print("🌐 Браузер открыт автоматически")
        except:
            print("⚠️  Не удалось открыть браузер автоматически")
            print("Скопируйте ссылку выше и откройте в браузере")
        
        print()
        print("После авторизации скопируйте полный URL страницы redirect:")
        print("(Он будет начинаться с http://localhost:8080/callback?code=...)")
        print()
        
        redirect_url = input("Вставьте полный redirect URL: ").strip()
        
        # Parse the authorization code from URL
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' not in query_params:
            print("❌ Не найден код авторизации в URL")
            return False
        
        auth_code = query_params['code'][0]
        print(f"✅ Код авторизации получен: {auth_code[:20]}...")
        
        # Handle the callback
        if handle_oauth_callback(auth_code):
            print("🎉 OAuth настройка завершена успешно!")
            print("Токены сохранены в token.pickle")
            print("Теперь бот будет сохранять файлы на ваш Google Drive")
            return True
        else:
            print("❌ Ошибка при обработке авторизации")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def check_authentication():
    """Check current authentication status."""
    from services.google_drive import GoogleDriveService
    
    print("🔍 Проверка текущей аутентификации...")
    
    drive_service = GoogleDriveService()
    auth_info = drive_service.get_authentication_info()
    
    print(f"Аутентифицирован: {auth_info['authenticated']}")
    print(f"Тип аутентификации: {auth_info['auth_type']}")
    
    if auth_info['auth_type'] == 'oauth':
        print("✅ Используется OAuth 2.0 (ваш личный Google Drive)")
    elif auth_info['auth_type'] == 'service_account':
        print("⚠️  Используется Service Account")
    else:
        print("❌ Аутентификация не настроена")
        if auth_info.get('oauth_url'):
            print(f"URL для OAuth: {auth_info['oauth_url']}")

if __name__ == "__main__":
    print("Google Drive OAuth Setup")
    print("=" * 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_authentication()
    else:
        setup_oauth() 