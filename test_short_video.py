#!/usr/bin/env python3
"""
Тест для проверки обработки коротких видео (8 секунд).
"""
import os
import sys
import tempfile
import logging

# Добавляем путь к приложению
sys.path.append('/app')

from app.video_processing.processor import VideoProcessor
from app.config.constants import MIN_FRAGMENT_DURATION

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_short_video_processing():
    """
    Тест обработки короткого видео (8 секунд).
    """
    print("🧪 Тестирование обработки коротких видео...")
    print(f"📏 Минимальная длительность фрагмента: {MIN_FRAGMENT_DURATION} секунд")
    
    # Создаем временную директорию для тестов
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = VideoProcessor(temp_dir)
        
        # Создаем тестовое видео длительностью 8 секунд с помощью FFmpeg
        test_video_path = os.path.join(temp_dir, "test_8sec.mp4")
        
        # Создаем тестовое видео 8 секунд (цветные полосы с аудио)
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', 'testsrc2=duration=8:size=1920x1080:rate=30',
            '-f', 'lavfi', 
            '-i', 'sine=frequency=1000:duration=8',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-t', '8',
            '-y',
            test_video_path
        ]
        
        import subprocess
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✅ Создано тестовое видео: {test_video_path}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка создания тестового видео: {e}")
            return False
        
        # Получаем информацию о видео
        try:
            video_info = processor.get_video_info(test_video_path)
            print(f"📹 Информация о видео:")
            print(f"   - Длительность: {video_info['duration']} секунд")
            print(f"   - Разрешение: {video_info['width']}x{video_info['height']}")
            print(f"   - FPS: {video_info['fps']}")
        except Exception as e:
            print(f"❌ Ошибка получения информации о видео: {e}")
            return False
        
        # Тестируем создание фрагментов
        try:
            print("\n🔄 Тестирование create_fragments...")
            fragments = processor.create_fragments(
                video_path=test_video_path,
                fragment_duration=30,  # Запрашиваем 30 секунд, но видео только 8 секунд
                quality="1080p",
                title="Тест короткого видео"
            )
            
            print(f"✅ Создано фрагментов: {len(fragments)}")
            for i, fragment in enumerate(fragments):
                print(f"   Фрагмент {i+1}:")
                print(f"     - Файл: {fragment['filename']}")
                print(f"     - Длительность: {fragment['duration']} сек")
                print(f"     - Размер: {fragment['size_bytes']} байт")
                print(f"     - Существует: {os.path.exists(fragment['local_path'])}")
                
        except Exception as e:
            print(f"❌ Ошибка создания фрагментов: {e}")
            return False
        
        # Тестируем создание фрагментов с субтитрами
        try:
            print("\n🔄 Тестирование create_fragments_with_subtitles...")
            fragments_with_subs = processor.create_fragments_with_subtitles(
                video_path=test_video_path,
                fragment_duration=30,
                quality="1080p",
                title="Тест с субтитрами",
                subtitle_style="modern"
            )
            
            print(f"✅ Создано фрагментов с субтитрами: {len(fragments_with_subs)}")
            for i, fragment in enumerate(fragments_with_subs):
                print(f"   Фрагмент {i+1}:")
                print(f"     - Файл: {fragment['filename']}")
                print(f"     - Длительность: {fragment['duration']} сек")
                print(f"     - Размер: {fragment['size_bytes']} байт")
                print(f"     - Существует: {os.path.exists(fragment['local_path'])}")
                
        except Exception as e:
            print(f"❌ Ошибка создания фрагментов с субтитрами: {e}")
            return False
        
        print("\n🎉 Все тесты пройдены успешно!")
        return True

if __name__ == "__main__":
    success = test_short_video_processing()
    sys.exit(0 if success else 1)