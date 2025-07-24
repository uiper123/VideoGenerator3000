#!/usr/bin/env python3
"""
Конвертер token.pickle в base64 для переменных окружения
"""
import os
import base64

def convert_token_to_base64():
    """Конвертирует token.pickle в base64 строку"""
    token_path = "token.pickle"
    
    if not os.path.exists(token_path):
        print("❌ token.pickle файл не найден")
        print("Сначала запустите setup_oauth.py для создания токена")
        return None
    
    try:
        # Читаем token.pickle файл
        with open(token_path, 'rb') as f:
            token_data = f.read()
        
        # Конвертируем в base64
        token_base64 = base64.b64encode(token_data).decode('utf-8')
        
        print("✅ token.pickle успешно конвертирован в base64")
        print(f"📊 Размер файла: {len(token_data)} байт")
        print(f"📊 Размер base64: {len(token_base64)} символов")
        print()
        print("🔑 GOOGLE_OAUTH_TOKEN_BASE64:")
        print("=" * 50)
        print(token_base64)
        print("=" * 50)
        print()
        print("📋 Скопируйте эту строку и добавьте в переменные окружения Railway:")
        print("GOOGLE_OAUTH_TOKEN_BASE64=" + token_base64)
        
        return token_base64
        
    except Exception as e:
        print(f"❌ Ошибка конвертации: {e}")
        return None

if __name__ == "__main__":
    print("🔄 Конвертация token.pickle в base64...")
    convert_token_to_base64()