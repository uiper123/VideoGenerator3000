#!/usr/bin/env python3
"""
Enhanced Worker Logger - добавляет детальное логирование в Celery tasks
"""
import os
import logging
import sys
from datetime import datetime
from pathlib import Path

# Настройка детального логирования для worker'ов
def setup_worker_logging():
    """Настраивает детальное логирование для Celery worker'ов"""
    
    # Создаем папку для логов
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [WORKER:%(process)d] - %(message)s'
    )
    
    # Основной логгер для worker'ов
    worker_logger = logging.getLogger('app.workers')
    worker_logger.setLevel(logging.DEBUG)
    
    # Файл для логов worker'ов
    worker_handler = logging.FileHandler('logs/worker.log')
    worker_handler.setLevel(logging.DEBUG)
    worker_handler.setFormatter(formatter)
    
    # Консольный вывод для worker'ов
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    worker_logger.addHandler(worker_handler)
    worker_logger.addHandler(console_handler)
    
    # Логгер для видео обработки
    video_logger = logging.getLogger('app.video_processing')
    video_logger.setLevel(logging.DEBUG)
    video_logger.addHandler(worker_handler)
    video_logger.addHandler(console_handler)
    
    # Логгер для Celery
    celery_logger = logging.getLogger('celery')
    celery_logger.setLevel(logging.INFO)
    celery_logger.addHandler(worker_handler)
    
    return worker_logger

# Декоратор для логирования задач
def log_task_execution(func):
    """Декоратор для детального логирования выполнения задач"""
    def wrapper(self, *args, **kwargs):
        logger = logging.getLogger('app.workers')
        task_name = func.__name__
        task_id = getattr(self, 'request', {}).get('id', 'unknown')
        
        logger.info(f"🚀 TASK START: {task_name} (ID: {task_id})")
        logger.info(f"📋 TASK ARGS: {args}")
        logger.info(f"⚙️ TASK KWARGS: {kwargs}")
        
        start_time = datetime.now()
        
        try:
            result = func(self, *args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ TASK SUCCESS: {task_name} (Duration: {duration:.2f}s)")
            logger.info(f"📤 TASK RESULT: {result}")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"❌ TASK FAILED: {task_name} (Duration: {duration:.2f}s)")
            logger.error(f"💥 TASK ERROR: {str(e)}")
            logger.exception("Full traceback:")
            
            raise
    
    return wrapper

# Функция для чтения логов worker'ов
def get_worker_logs(lines: int = 50) -> str:
    """Получает последние логи worker'ов"""
    try:
        log_file = Path("logs/worker.log")
        if not log_file.exists():
            return "❌ Файл логов worker'ов не найден"
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
        return ''.join(recent_lines)
    
    except Exception as e:
        return f"❌ Ошибка чтения логов: {e}"

# Функция для очистки старых логов
def cleanup_old_logs(days: int = 7):
    """Очищает логи старше указанного количества дней"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return
        
        import time
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        for log_file in logs_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                print(f"🧹 Удален старый лог: {log_file}")
                
    except Exception as e:
        print(f"❌ Ошибка очистки логов: {e}")

if __name__ == "__main__":
    # Тестирование системы логирования
    logger = setup_worker_logging()
    logger.info("🧪 Тестирование системы логирования worker'ов")
    logger.debug("🔍 Debug сообщение")
    logger.warning("⚠️ Warning сообщение")
    logger.error("❌ Error сообщение")
    
    print("\n📋 Последние логи:")
    print(get_worker_logs(10))