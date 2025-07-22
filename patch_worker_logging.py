#!/usr/bin/env python3
"""
Патч для улучшения логирования процесса обработки видео в Google Colab
"""
import os
import sys
import logging
from pathlib import Path
import importlib
import types
import functools
import inspect

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/content/videobot/logs/enhanced_worker.log')
    ]
)
logger = logging.getLogger(__name__)

def patch_function(module_name, function_name, wrapper_func):
    """
    Патчит функцию в модуле для добавления логирования или изменения поведения
    
    Args:
        module_name: Имя модуля (например, 'app.workers.video_tasks')
        function_name: Имя функции для патча
        wrapper_func: Функция-обертка для применения
    """
    try:
        # Импортируем модуль
        module = importlib.import_module(module_name)
        
        # Получаем оригинальную функцию
        original_func = getattr(module, function_name)
        
        # Создаем обертку
        @functools.wraps(original_func)
        def wrapped_func(*args, **kwargs):
            return wrapper_func(original_func, *args, **kwargs)
        
        # Заменяем оригинальную функцию
        setattr(module, function_name, wrapped_func)
        logger.info(f"✅ Успешно пропатчена функция {module_name}.{function_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка патча функции {module_name}.{function_name}: {e}")
        return False

def patch_method(class_path, method_name, wrapper_func):
    """
    Патчит метод класса
    
    Args:
        class_path: Путь к классу (например, 'app.services.google_drive.GoogleDriveService')
        method_name: Имя метода
        wrapper_func: Функция-обертка для применения
    """
    try:
        # Разбиваем путь на модуль и класс
        module_path, class_name = class_path.rsplit('.', 1)
        
        # Импортируем модуль
        module = importlib.import_module(module_path)
        
        # Получаем класс
        cls = getattr(module, class_name)
        
        # Получаем оригинальный метод
        original_method = getattr(cls, method_name)
        
        # Создаем обертку
        @functools.wraps(original_method)
        def wrapped_method(self, *args, **kwargs):
            return wrapper_func(original_method, self, *args, **kwargs)
        
        # Заменяем оригинальный метод
        setattr(cls, method_name, wrapped_method)
        logger.info(f"✅ Успешно пропатчен метод {class_path}.{method_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка патча метода {class_path}.{method_name}: {e}")
        return False

# Патч для улучшения логирования скачивания видео
def download_video_wrapper(original_func, self, task_id, url, quality="best", settings_dict=None):
    """Обертка для улучшения логирования download_video"""
    logger.info(f"🔽 Начинаем скачивание видео для задачи {task_id}: {url}")
    
    try:
        # Вызываем оригинальную функцию
        result = original_func(self, task_id, url, quality, settings_dict)
        
        # Логируем успешное скачивание
        file_size_mb = result.get('file_size', 0) / (1024 * 1024)
        logger.info(f"✅ Видео успешно скачано: {result.get('title')} ({file_size_mb:.2f} МБ)")
        logger.info(f"📁 Локальный путь: {result.get('local_path')}")
        logger.info(f"⏱️ Длительность: {result.get('duration')} секунд")
        
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка скачивания видео: {e}")
        raise

# Патч для улучшения логирования обработки видео
def process_video_wrapper(original_func, self, task_id, local_path, settings_dict):
    """Обертка для улучшения логирования process_video"""
    logger.info(f"⚙️ Начинаем обработку видео для задачи {task_id}")
    logger.info(f"📁 Исходный файл: {local_path}")
    logger.info(f"🛠️ Настройки обработки: {settings_dict}")
    
    try:
        # Вызываем оригинальную функцию
        result = original_func(self, task_id, local_path, settings_dict)
        
        # Логируем успешную обработку
        logger.info(f"✅ Видео успешно обработано для задачи {task_id}")
        logger.info(f"🎬 Создано фрагментов: {len(result)}")
        
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка обработки видео: {e}")
        raise

# Патч для улучшения логирования загрузки на Google Drive
def upload_to_drive_wrapper(original_func, task_id, fragments):
    """Обертка для улучшения логирования upload_to_drive"""
    logger.info(f"☁️ Начинаем загрузку на Google Drive для задачи {task_id}")
    logger.info(f"🎬 Загружаем {len(fragments)} фрагментов")
    
    try:
        # Вызываем оригинальную функцию
        result = original_func(task_id, fragments)
        
        # Логируем успешную загрузку
        logger.info(f"✅ Загрузка на Google Drive завершена для задачи {task_id}")
        logger.info(f"📊 Загружено файлов: {len(result)}")
        
        # Выводим ссылки на файлы
        for i, upload_result in enumerate(result):
            logger.info(f"🔗 Фрагмент {i+1}: {upload_result.get('direct_url', 'N/A')}")
        
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки на Google Drive: {e}")
        raise

# Патч для улучшения логирования GoogleDriveService.upload_multiple_files
def upload_multiple_files_wrapper(original_method, self, file_paths, task_id=None):
    """Обертка для улучшения логирования GoogleDriveService.upload_multiple_files"""
    logger.info(f"☁️ GoogleDriveService: Загрузка {len(file_paths)} файлов на Google Drive")
    logger.info(f"🔐 Аутентификация: {self.auth_type}, Сервис инициализирован: {self.service is not None}")
    
    # Проверяем наличие token.pickle
    token_path = "token.pickle"
    if os.path.exists(token_path):
        logger.info(f"✅ Найден token.pickle: {os.path.getsize(token_path)} байт")
    else:
        logger.warning(f"⚠️ Файл token.pickle не найден!")
    
    try:
        # Вызываем оригинальный метод
        result = original_method(self, file_paths, task_id)
        
        # Логируем результат
        successful = [r for r in result if r.get("success")]
        failed = [r for r in result if not r.get("success")]
        
        logger.info(f"📊 Результат загрузки: {len(successful)}/{len(result)} успешно, {len(failed)} с ошибками")
        
        # Выводим ссылки на успешно загруженные файлы
        for i, upload_result in enumerate(successful):
            logger.info(f"🔗 Файл {i+1}: {upload_result.get('direct_url', upload_result.get('file_url', 'N/A'))}")
        
        # Выводим ошибки
        for i, upload_result in enumerate(failed):
            logger.error(f"❌ Ошибка загрузки файла {upload_result.get('file_path', f'#{i+1}')}: {upload_result.get('error', 'Неизвестная ошибка')}")
        
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка в GoogleDriveService.upload_multiple_files: {e}")
        raise

def main():
    """Основная функция для применения всех патчей"""
    logger.info("🔧 Применение патчей для улучшения логирования в Google Colab")
    
    # Патчим функции для улучшения логирования
    patches = [
        # Улучшение логирования скачивания видео
        {
            'module': 'app.workers.video_tasks',
            'function': 'download_video',
            'wrapper': download_video_wrapper
        },
        # Улучшение логирования обработки видео
        {
            'module': 'app.workers.video_tasks',
            'function': 'process_video',
            'wrapper': process_video_wrapper
        },
        # Улучшение логирования загрузки на Google Drive
        {
            'module': 'app.workers.video_tasks',
            'function': 'upload_to_drive',
            'wrapper': upload_to_drive_wrapper
        },
    ]
    
    # Применяем патчи функций
    for patch in patches:
        patch_function(patch['module'], patch['function'], patch['wrapper'])
    
    # Патчим методы классов
    method_patches = [
        # Улучшение логирования загрузки файлов на Google Drive
        {
            'class_path': 'app.services.google_drive.GoogleDriveService',
            'method': 'upload_multiple_files',
            'wrapper': upload_multiple_files_wrapper
        },
    ]
    
    # Применяем патчи методов
    for patch in method_patches:
        patch_method(patch['class_path'], patch['method'], patch['wrapper'])
    
    logger.info("✅ Патчи для улучшения логирования успешно применены")

if __name__ == "__main__":
    main()