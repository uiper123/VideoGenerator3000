#!/usr/bin/env python3
"""
Тестирование OAuth токена из переменной окружения
"""
import os
import sys
import base64
import pickle

# Добавляем путь к приложению
sys.path.insert(0, 'app')

def test_env_oauth():
    """Тестируем загрузку OAuth из переменной окружения"""
    
    # Читаем token.pickle и конвертируем в base64
    if os.path.exists("token.pickle"):
        with open("token.pickle", 'rb') as f:
            token_data = f.read()
        
        token_base64 = base64.b64encode(token_data).decode('utf-8')
        
        # Устанавливаем переменную окружения
        os.environ["GOOGLE_OAUTH_TOKEN_BASE64"] = token_base64
        print("✅ Установлена переменная окружения GOOGLE_OAUTH_TOKEN_BASE64")
        
        # Временно переименовываем token.pickle, чтобы протестировать загрузку из env
        if os.path.exists("token.pickle"):
            os.rename("token.pickle", "token.pickle.backup")
            print("📁 Временно переименован token.pickle -> token.pickle.backup")
        
        try:
            # Тестируем загрузку из переменной окружения
            from app.services.google_drive import get_google_credentials
            
            creds = get_google_credentials()
            
            if creds:
                print("✅ OAuth токен успешно загружен из переменной окружения")
                print(f"🔑 Client ID: {getattr(creds, 'client_id', 'N/A')}")
                print(f"⏰ Valid: {creds.valid}")
                return True
            else:
                print("❌ Не удалось загрузить OAuth токен из переменной окружения")
                return False
                
        finally:
            # Восстанавливаем token.pickle
            if os.path.exists("token.pickle.backup"):
                os.rename("token.pickle.backup", "token.pickle")
                print("📁 Восстановлен token.pickle")
    else:
        print("❌ token.pickle не найден")
        return False

if __name__ == "__main__":
    print("🧪 Тестирование OAuth токена из переменной окружения...")
    success = test_env_oauth()
    
    if success:
        print("\n🎉 Тест прошел успешно!")
        print("OAuth токен корректно работает через переменную окружения")
    else:
        print("\n❌ Тест не прошел")
    
    sys.exit(0 if success else 1)