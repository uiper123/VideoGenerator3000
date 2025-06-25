#!/usr/bin/env python3
"""
Simplified OAuth 2.0 setup script for Google Drive.
This script doesn't depend on the main app settings.
"""
import os
import json
import pickle
import logging
from urllib.parse import urlparse, parse_qs
import webbrowser

from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']

def create_oauth_flow() -> Flow:
    """Create OAuth 2.0 flow for user authentication."""
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set")
    
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/callback"]
        }
    }
    
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = "http://localhost:8080/callback"
    
    return flow

def get_oauth_authorization_url() -> str:
    """Get OAuth authorization URL."""
    try:
        flow = create_oauth_flow()
        auth_url, _ = flow.authorization_url(prompt='consent')
        return auth_url
    except Exception as e:
        logger.error(f"Failed to create OAuth authorization URL: {e}")
        return ""

def handle_oauth_callback(authorization_code: str) -> bool:
    """Handle OAuth callback and save credentials."""
    try:
        flow = create_oauth_flow()
        flow.fetch_token(code=authorization_code)
        
        creds = flow.credentials
        
        # Save credentials
        with open("token.pickle", 'wb') as token:
            pickle.dump(creds, token)
        
        logger.info("Successfully saved OAuth credentials")
        return True
        
    except Exception as e:
        logger.error(f"Failed to handle OAuth callback: {e}")
        return False

def check_oauth_status():
    """Check current OAuth status."""
    token_path = "token.pickle"
    
    if not os.path.exists(token_path):
        print("❌ OAuth токен не найден")
        return False
    
    try:
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
        
        if creds and creds.valid:
            print("✅ OAuth токен действителен")
            print(f"Токен истекает: {creds.expiry}")
            return True
        elif creds and creds.expired and creds.refresh_token:
            print("🔄 Обновляем токен...")
            creds.refresh(Request())
            
            # Save refreshed token
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            
            print("✅ Токен обновлен успешно")
            return True
        else:
            print("❌ Токен недействителен, нужна повторная авторизация")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {e}")
        return False

def setup_oauth():
    """Setup OAuth 2.0 authentication."""
    print("🔐 Настройка OAuth 2.0 для Google Drive")
    print("=" * 50)
    
    # Check environment variables
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ Ошибка: Переменные окружения не настроены!")
        print()
        print("Необходимо настроить:")
        print("GOOGLE_OAUTH_CLIENT_ID=your_client_id")
        print("GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret")
        print()
        print("Ваши credentials:")
        print("Client ID:", client_id or "НЕ УСТАНОВЛЕН")
        print("Client Secret:", "*" * 20 if client_secret else "НЕ УСТАНОВЛЕН")
        return False
    
    print("✅ Переменные окружения настроены")
    print(f"Client ID: {client_id[:30]}...")
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
        
        # Try to open browser
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
        
        # Parse authorization code
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' not in query_params:
            print("❌ Не найден код авторизации в URL")
            return False
        
        auth_code = query_params['code'][0]
        print(f"✅ Код авторизации получен: {auth_code[:20]}...")
        
        # Handle callback
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

if __name__ == "__main__":
    print("🚀 Простая настройка OAuth для Google Drive")
    print("=" * 50)
    
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "check":
        check_oauth_status()
    else:
        setup_oauth() 