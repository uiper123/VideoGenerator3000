#!/usr/bin/env python3
"""
Улучшение логирования в Google Colab для VideoGenerator3000
"""
import os
import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/content/videobot/logs/colab.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_enhanced_logging():
    """
    Настраивает улучшенное логирование для Google Colab
    
    1. Создает директорию для логов
    2. Настраивает логирование для всех модулей
    3. Перенаправляет вывод Celery в файл
    """
    logger.info("🔧 Настройка улучшенного логирования для Google Colab")
    
    # 1. Создаем директорию для логов
    logs_dir = Path("/content/videobot/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Настраиваем логирование для всех модулей
    logging.getLogger("app").setLevel(logging.DEBUG)
    logging.getLogger("app.video_processing").setLevel(logging.DEBUG)
    logging.getLogger("app.workers").setLevel(logging.DEBUG)
    logging.getLogger("app.services").setLevel(logging.DEBUG)
    
    # 3. Создаем файловые обработчики для разных модулей
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Логи скачивания видео
    download_handler = logging.FileHandler('/content/videobot/logs/download.log')
    download_handler.setFormatter(formatter)
    download_handler.setLevel(logging.DEBUG)
    logging.getLogger("app.video_processing.downloader").addHandler(download_handler)
    
    # Логи обработки видео
    processing_handler = logging.FileHandler('/content/videobot/logs/processing.log')
    processing_handler.setFormatter(formatter)
    processing_handler.setLevel(logging.DEBUG)
    logging.getLogger("app.video_processing.processor").addHandler(processing_handler)
    
    # Логи Google Drive
    drive_handler = logging.FileHandler('/content/videobot/logs/drive.log')
    drive_handler.setFormatter(formatter)
    drive_handler.setLevel(logging.DEBUG)
    logging.getLogger("app.services.google_drive").addHandler(drive_handler)
    
    logger.info("✅ Улучшенное логирование настроено")
    return True

def patch_celery_logging():
    """
    Патчит логирование Celery для отображения в Colab
    """
    logger.info("🔧 Настройка логирования Celery")
    
    # Создаем файл с настройками логирования для Celery
    celery_logging_config = """
from celery.signals import setup_logging

@setup_logging.connect
def configure_logging(*args, **kwargs):
    import logging
    from logging.config import dictConfig
    
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(process)d] - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': '/content/videobot/logs/celery.log',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'celery': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'app': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
        }
    })
    """
    
    # Записываем настройки в файл
    celery_logging_path = Path("/content/videobot/app/workers/celery_logging.py")
    celery_logging_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(celery_logging_path, 'w') as f:
        f.write(celery_logging_config)
    
    # Добавляем импорт в celery_app.py
    celery_app_path = Path("/content/videobot/app/workers/celery_app.py")
    
    if celery_app_path.exists():
        with open(celery_app_path, 'r') as f:
            content = f.read()
        
        # Проверяем, нужно ли добавить импорт
        if "import celery_logging" not in content:
            # Находим импорты
            import_section_end = content.find("\n\n", content.find("import"))
            if import_section_end != -1:
                # Добавляем импорт после секции импортов
                content = content[:import_section_end] + "\n# Import enhanced logging\nimport app.workers.celery_logging" + content[import_section_end:]
                
                # Записываем изменения
                with open(celery_app_path, 'w') as f:
                    f.write(content)
                
                logger.info("✅ Добавлен импорт улучшенного логирования в celery_app.py")
            else:
                logger.warning("⚠️ Не удалось найти секцию импортов в celery_app.py")
        else:
            logger.info("✅ Импорт логирования уже добавлен в celery_app.py")
    else:
        logger.warning(f"⚠️ Файл {celery_app_path} не найден")
    
    logger.info("✅ Логирование Celery настроено")
    return True

def add_progress_logging():
    """
    Добавляет вывод прогресса для длительных операций
    """
    logger.info("🔧 Добавление логирования прогресса")
    
    # Создаем файл с функциями для отображения прогресса
    progress_code = """
import sys
import time
from datetime import datetime

class ProgressLogger:
    def __init__(self, total, description="Progress", update_interval=1.0):
        self.total = total
        self.description = description
        self.start_time = datetime.now()
        self.last_update = time.time()
        self.update_interval = update_interval
        self.current = 0
        self.last_percent = 0
        
    def update(self, current):
        self.current = current
        current_time = time.time()
        
        # Обновляем только через интервал или если это последнее обновление
        if current_time - self.last_update >= self.update_interval or current >= self.total:
            percent = min(100, int(current * 100 / self.total))
            
            # Обновляем только если процент изменился или это последнее обновление
            if percent != self.last_percent or current >= self.total:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                
                # Оценка оставшегося времени
                if current > 0:
                    eta = elapsed * (self.total - current) / current
                    eta_str = f"{int(eta / 60)}:{int(eta % 60):02d}"
                else:
                    eta_str = "N/A"
                
                # Создаем строку прогресса
                bar_length = 30
                filled_length = int(bar_length * current / self.total)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                # Выводим прогресс
                print(f"\\r{self.description}: |{bar}| {percent}% ({current}/{self.total}) ETA: {eta_str}", end='')
                sys.stdout.flush()
                
                if current >= self.total:
                    print()  # Перевод строки после завершения
                
                self.last_update = current_time
                self.last_percent = percent
"""
    
    # Записываем код в файл
    progress_path = Path("/content/videobot/app/utils/progress.py")
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(progress_path, 'w') as f:
        f.write(progress_code)
    
    logger.info("✅ Добавлено логирование прогресса")
    return True

def create_log_viewer():
    """
    Создает скрипт для просмотра логов в реальном времени
    """
    logger.info("🔧 Создание скрипта для просмотра логов")
    
    script_content = """#!/bin/bash
# Log Viewer Script

echo "📋 VideoGenerator3000 - Log Viewer"
echo "=================================="

case "$1" in
    "download")
        echo "🔽 Просмотр логов скачивания..."
        tail -f /content/videobot/logs/download.log
        ;;
    "processing")
        echo "⚙️ Просмотр логов обработки видео..."
        tail -f /content/videobot/logs/processing.log
        ;;
    "drive")
        echo "☁️ Просмотр логов Google Drive..."
        tail -f /content/videobot/logs/drive.log
        ;;
    "celery")
        echo "🔄 Просмотр логов Celery..."
        tail -f /content/videobot/logs/celery.log
        ;;
    "all")
        echo "📋 Просмотр всех логов..."
        tail -f /content/videobot/logs/*.log
        ;;
    *)
        echo "Использование: $0 {download|processing|drive|celery|all}"
        echo ""
        echo "Доступные файлы логов:"
        ls -la /content/videobot/logs/
        ;;
esac
"""
    
    # Записываем скрипт в файл
    script_path = Path("/content/videobot/view_logs.sh")
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Делаем скрипт исполняемым
    os.chmod(script_path, 0o755)
    
    logger.info(f"✅ Создан скрипт для просмотра логов: {script_path}")
    return True

def main():
    """Основная функция"""
    logger.info("🔧 VideoGenerator3000 - Улучшение логирования в Google Colab")
    logger.info("=" * 50)
    
    # Настраиваем улучшенное логирование
    setup_enhanced_logging()
    
    # Патчим логирование Celery
    patch_celery_logging()
    
    # Добавляем логирование прогресса
    add_progress_logging()
    
    # Создаем скрипт для просмотра логов
    create_log_viewer()
    
    logger.info("=" * 50)
    logger.info("✅ Улучшение логирования завершено!")
    logger.info("")
    logger.info("📋 Для просмотра логов используйте:")
    logger.info("  - Скачивание видео: !bash /content/videobot/view_logs.sh download")
    logger.info("  - Обработка видео: !bash /content/videobot/view_logs.sh processing")
    logger.info("  - Google Drive: !bash /content/videobot/view_logs.sh drive")
    logger.info("  - Celery: !bash /content/videobot/view_logs.sh celery")
    logger.info("  - Все логи: !bash /content/videobot/view_logs.sh all")

if __name__ == "__main__":
    main() 