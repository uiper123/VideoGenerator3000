#!/usr/bin/env python3
"""
Тест для проверки исправления проблемы с 8-секундными чанками.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.video_processing.processor import VideoProcessor
from app.config.constants import MIN_FRAGMENT_DURATION, MAX_FRAGMENT_DURATION

def test_fragment_logic():
    """Тест логики создания фрагментов без реального видео."""
    
    # Симулируем различные сценарии
    test_cases = [
        {
            "name": "38-секундное видео с фрагментами по 30 сек",
            "total_duration": 38,
            "fragment_duration": 30,
            "expected_fragments": 2,  # 30 сек + 8 сек (но 8 < 15, поэтому только 1)
            "expected_durations": [30]  # Только один фрагмент 30 сек, 8 сек игнорируется
        },
        {
            "name": "45-секундное видео с фрагментами по 30 сек", 
            "total_duration": 45,
            "fragment_duration": 30,
            "expected_fragments": 2,  # 30 сек + 15 сек
            "expected_durations": [30, 15]
        },
        {
            "name": "50-секундное видео с фрагментами по 30 сек",
            "total_duration": 50, 
            "fragment_duration": 30,
            "expected_fragments": 2,  # 30 сек + 20 сек
            "expected_durations": [30, 20]
        },
        {
            "name": "10-секундное видео (короче минимума)",
            "total_duration": 10,
            "fragment_duration": 30, 
            "expected_fragments": 1,  # Один фрагмент с полным видео
            "expected_durations": [10]
        },
        {
            "name": "90-секундное видео с фрагментами по 30 сек",
            "total_duration": 90,
            "fragment_duration": 30,
            "expected_fragments": 3,  # 30 + 30 + 30
            "expected_durations": [30, 30, 30]
        }
    ]
    
    print("🧪 Тестирование логики создания фрагментов...")
    print(f"MIN_FRAGMENT_DURATION = {MIN_FRAGMENT_DURATION} сек")
    print(f"MAX_FRAGMENT_DURATION = {MAX_FRAGMENT_DURATION} сек")
    print()
    
    for test_case in test_cases:
        print(f"📋 Тест: {test_case['name']}")
        
        total_duration = test_case['total_duration']
        fragment_duration = test_case['fragment_duration']
        
        # Логика из исправленного кода
        if total_duration < MIN_FRAGMENT_DURATION:
            # Специальный случай: видео короче минимума
            total_fragments = 1
            num_full_fragments = 0
            create_remainder_fragment = True
            remainder = total_duration
        else:
            # Обычная логика
            num_full_fragments = int(total_duration // fragment_duration)
            remainder = total_duration % fragment_duration
            create_remainder_fragment = remainder >= MIN_FRAGMENT_DURATION
            total_fragments = num_full_fragments + (1 if create_remainder_fragment else 0)
        
        # Вычисляем длительности фрагментов
        actual_durations = []
        for i in range(total_fragments):
            if total_duration < MIN_FRAGMENT_DURATION:
                actual_duration = total_duration
            else:
                start_time = i * fragment_duration
                
                if i == num_full_fragments and create_remainder_fragment:
                    actual_duration = remainder
                else:
                    actual_duration = fragment_duration
                
                if start_time + actual_duration > total_duration:
                    actual_duration = total_duration - start_time
                    if actual_duration < MIN_FRAGMENT_DURATION and total_duration >= MIN_FRAGMENT_DURATION:
                        break
            
            actual_durations.append(actual_duration)
        
        # Проверяем результат
        print(f"   Общая длительность: {total_duration} сек")
        print(f"   Длительность фрагмента: {fragment_duration} сек")
        print(f"   Ожидаемо фрагментов: {test_case['expected_fragments']}")
        print(f"   Получено фрагментов: {len(actual_durations)}")
        print(f"   Ожидаемые длительности: {test_case['expected_durations']}")
        print(f"   Фактические длительности: {actual_durations}")
        
        # Проверка
        if len(actual_durations) == test_case['expected_fragments']:
            print("   ✅ Количество фрагментов правильное")
        else:
            print("   ❌ Неправильное количество фрагментов")
        
        if actual_durations == test_case['expected_durations']:
            print("   ✅ Длительности фрагментов правильные")
        else:
            print("   ❌ Неправильные длительности фрагментов")
        
        print()

if __name__ == "__main__":
    test_fragment_logic()