#!/usr/bin/env python3
"""
Тест для проверки настроек размера заголовка
"""
import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.user_settings import UserSettingsService

async def test_title_size_settings():
    """Тест настроек размера заголовка"""
    test_user_id = 12345  # Тестовый ID пользователя
    
    print("🧪 Тестирование настроек размера заголовка...")
    
    # 1. Получаем текущие настройки
    print("\n1. Получение текущих настроек:")
    current_size = await UserSettingsService.get_style_setting(test_user_id, 'title_style', 'size')
    current_size_name = UserSettingsService.get_size_name(current_size)
    print(f"   Текущий размер: {current_size} ({current_size_name})")
    
    # 2. Изменяем размер на "huge"
    print("\n2. Изменение размера на 'huge':")
    success = await UserSettingsService.set_style_setting(test_user_id, 'title_style', 'size', 'huge')
    print(f"   Результат сохранения: {success}")
    
    # 3. Проверяем, что размер изменился
    print("\n3. Проверка изменения:")
    new_size = await UserSettingsService.get_style_setting(test_user_id, 'title_style', 'size')
    new_size_name = UserSettingsService.get_size_name(new_size)
    print(f"   Новый размер: {new_size} ({new_size_name})")
    
    # 4. Изменяем размер на "small"
    print("\n4. Изменение размера на 'small':")
    success = await UserSettingsService.set_style_setting(test_user_id, 'title_style', 'size', 'small')
    print(f"   Результат сохранения: {success}")
    
    # 5. Проверяем финальное состояние
    print("\n5. Финальная проверка:")
    final_size = await UserSettingsService.get_style_setting(test_user_id, 'title_style', 'size')
    final_size_name = UserSettingsService.get_size_name(final_size)
    print(f"   Финальный размер: {final_size} ({final_size_name})")
    
    # 6. Получаем все настройки пользователя
    print("\n6. Все настройки пользователя:")
    all_settings = await UserSettingsService.get_user_settings(test_user_id)
    print(f"   Настройки: {all_settings}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_title_size_settings())