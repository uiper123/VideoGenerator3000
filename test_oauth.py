#!/usr/bin/env python3
"""
Тестовый скрипт для проверки OAuth токена из token.pickle
"""
import os
import pickle
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def test_oauth_token():
    """Тестируем OAuth токен из token.pickle"""
    token_path = "token.pickle"
    
    if not os.path.exists(token_path):
        print("❌ token.pickle файл не найден")
        return False
    
    try:
        # Загружаем токен
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
        
        print("✅ token.pickle успешно загружен")
        print(f"📧 Client ID: {getattr(creds, 'client_id', 'N/A')}")
        print(f"🔑 Has refresh token: {bool(getattr(creds, 'refresh_token', None))}")
        print(f"⏰ Valid: {creds.valid}")
        print(f"⏰ Expired: {creds.expired}")
        
        # Проверяем валидность
        if creds.valid:
            print("✅ Токен валиден и готов к использованию")
            return True
        elif creds.expired and creds.refresh_token:
            print("🔄 Токен истек, пробуем обновить...")
            try:
                creds.refresh(Request())
                print("✅ Токен успешно обновлен")
                
                # Сохраняем обновленный токен
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                print("💾 Обновленный токен сохранен в token.pickle")
                return True
            except Exception as e:
                print(f"❌ Ошибка обновления токена: {e}")
                return False
        else:
            print("❌ Токен недействителен и не может быть обновлен")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка загрузки token.pickle: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Тестирование OAuth токена...")
    success = test_oauth_token()
    
    if success:
        print("\n🎉 OAuth токен работает корректно!")
        print("Теперь можно запускать бота: python run_bot.py")
    else:
        print("\n❌ Проблемы с OAuth токеном")
        print("Запустите setup_oauth.py для повторной настройки")
    
    sys.exit(0 if success else 1)