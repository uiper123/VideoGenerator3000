#!/usr/bin/env python3
"""
Патч для добавления детального логирования в Celery worker'ы
"""
import os
import sys
import shutil
from pathlib import Path

def patch_worker_files():
    """Добавляет детальное логирование в файлы worker'ов"""
    
    # Создаем папку для логов
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Патч для app/workers/video_tasks.py
    video_tasks_path = Path("app/workers/video_tasks.py")
    if video_tasks_path.exists():
        print("🔧 Patching app/workers/video_tasks.py...")
        
        # Читаем оригинальный файл
        with open(video_tasks_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Добавляем импорты для логирования
        logging_imports = '''
# Enhanced logging setup
import sys
from datetime import datetime
from pathlib import Path

# Setup enhanced logging for workers
def setup_worker_logging():
    """Setup detailed logging for Celery workers"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [WORKER:%(process)d] - %(message)s'
    )
    
    # Worker logger
    worker_logger = logging.getLogger('app.workers')
    worker_logger.setLevel(logging.DEBUG)
    
    # File handler
    worker_handler = logging.FileHandler('logs/worker.log')
    worker_handler.setLevel(logging.DEBUG)
    worker_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    worker_logger.addHandler(worker_handler)
    worker_logger.addHandler(console_handler)
    
    return worker_logger

# Initialize enhanced logging
enhanced_logger = setup_worker_logging()

def log_task_execution(func):
    """Decorator for detailed task logging"""
    def wrapper(self, *args, **kwargs):
        task_name = func.__name__
        task_id = getattr(self, 'request', {}).get('id', 'unknown')
        
        enhanced_logger.info(f"🚀 TASK START: {task_name} (ID: {task_id})")
        enhanced_logger.info(f"📋 TASK ARGS: {args}")
        enhanced_logger.info(f"⚙️ TASK KWARGS: {kwargs}")
        
        start_time = datetime.now()
        
        try:
            result = func(self, *args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            enhanced_logger.info(f"✅ TASK SUCCESS: {task_name} (Duration: {duration:.2f}s)")
            enhanced_logger.info(f"📤 TASK RESULT: {result}")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            enhanced_logger.error(f"❌ TASK FAILED: {task_name} (Duration: {duration:.2f}s)")
            enhanced_logger.error(f"💥 TASK ERROR: {str(e)}")
            enhanced_logger.exception("Full traceback:")
            
            raise
    
    return wrapper

'''
        
        # Вставляем импорты после существующих импортов
        import_end = content.find('\nlogger = logging.getLogger(__name__)')
        if import_end != -1:
            content = content[:import_end] + logging_imports + content[import_end:]
        
        # Добавляем декоратор к функциям задач
        functions_to_patch = [
            '@shared_task(base=VideoTask, bind=True)\ndef download_video(',
            '@shared_task(base=VideoTask, bind=True)\ndef process_video(',
            '@shared_task(base=VideoTask, bind=True)\ndef upload_to_drive(',
            '@shared_task(base=VideoTask, bind=True)\ndef process_video_chain_optimized('
        ]
        
        for func_signature in functions_to_patch:
            if func_signature in content:
                content = content.replace(
                    func_signature,
                    '@log_task_execution\n' + func_signature
                )
        
        # Создаем резервную копию
        shutil.copy2(video_tasks_path, f"{video_tasks_path}.backup")
        
        # Записываем патченый файл
        with open(video_tasks_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ app/workers/video_tasks.py patched successfully")
    else:
        print("❌ app/workers/video_tasks.py not found")
    
    # Патч для app/video_processing/processor.py
    processor_path = Path("app/video_processing/processor.py")
    if processor_path.exists():
        print("🔧 Patching app/video_processing/processor.py...")
        
        with open(processor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Добавляем детальное логирование в VideoProcessor
        enhanced_logging = '''
        # Enhanced logging for video processing
        self.logger.info(f"🎬 Starting video processing: {input_path}")
        self.logger.info(f"📁 Input file size: {os.path.getsize(input_path) if os.path.exists(input_path) else 'N/A'} bytes")
        self.logger.info(f"⚙️ Processing settings: {settings}")
        
        start_time = time.time()
'''
        
        # Ищем метод process и добавляем логирование
        if 'def process(' in content:
            content = content.replace(
                'def process(',
                'def process('
            )
            # Добавляем логирование в начало метода process
            process_start = content.find('def process(')
            if process_start != -1:
                # Находим начало тела функции
                func_body_start = content.find(':', process_start) + 1
                # Находим первую строку с отступом
                next_line = content.find('\n', func_body_start) + 1
                content = content[:next_line] + enhanced_logging + content[next_line:]
        
        # Создаем резервную копию
        shutil.copy2(processor_path, f"{processor_path}.backup")
        
        # Записываем патченый файл
        with open(processor_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ app/video_processing/processor.py patched successfully")
    else:
        print("❌ app/video_processing/processor.py not found")

def create_worker_start_script():
    """Создает скрипт для запуска worker'а с логированием"""
    
    script_content = '''#!/bin/bash
# Enhanced Celery Worker Startup Script

echo "🚀 Starting Celery Worker with enhanced logging..."

# Create logs directory
mkdir -p logs

# Set environment variables for better logging
export CELERY_LOG_LEVEL=DEBUG
export PYTHONUNBUFFERED=1

# Start Celery worker with enhanced logging
celery -A app.workers.celery_app worker \\
    --loglevel=DEBUG \\
    --concurrency=2 \\
    --logfile=logs/celery_worker.log \\
    --pidfile=logs/celery_worker.pid \\
    --hostname=worker@%h \\
    --queues=default,video_processing \\
    --max-tasks-per-child=10 \\
    --time-limit=3600 \\
    --soft-time-limit=3000

echo "👋 Celery Worker stopped"
'''
    
    with open('start_worker_enhanced.sh', 'w') as f:
        f.write(script_content)
    
    # Делаем скрипт исполняемым
    os.chmod('start_worker_enhanced.sh', 0o755)
    
    print("✅ Enhanced worker startup script created: start_worker_enhanced.sh")

def create_log_viewer_script():
    """Создает скрипт для просмотра логов в реальном времени"""
    
    script_content = '''#!/bin/bash
# Log Viewer Script

echo "📋 VideoGenerator3000 - Log Viewer"
echo "=================================="

case "$1" in
    "worker")
        echo "🔧 Watching worker logs..."
        tail -f logs/worker.log
        ;;
    "celery")
        echo "🔧 Watching celery logs..."
        tail -f logs/celery_worker.log
        ;;
    "bot")
        echo "🤖 Watching bot logs..."
        tail -f video_bot.log
        ;;
    "all")
        echo "📋 Watching all logs..."
        tail -f logs/worker.log logs/celery_worker.log video_bot.log
        ;;
    *)
        echo "Usage: $0 {worker|celery|bot|all}"
        echo ""
        echo "Available log files:"
        ls -la logs/ video_bot.log 2>/dev/null || echo "No log files found"
        ;;
esac
'''
    
    with open('view_logs.sh', 'w') as f:
        f.write(script_content)
    
    # Делаем скрипт исполняемым
    os.chmod('view_logs.sh', 0o755)
    
    print("✅ Log viewer script created: view_logs.sh")

def main():
    """Main function"""
    print("🔧 VideoGenerator3000 - Worker Logging Patcher")
    print("=" * 50)
    
    # Проверяем, что мы в правильной директории
    if not Path("app").exists():
        print("❌ Error: app/ directory not found!")
        print("Please run this script from the project root directory")
        return
    
    # Применяем патчи
    patch_worker_files()
    
    # Создаем вспомогательные скрипты
    create_worker_start_script()
    create_log_viewer_script()
    
    print("\n" + "=" * 50)
    print("✅ Patching completed!")
    print("\n📋 Next steps:")
    print("1. Restart Celery worker: ./start_worker_enhanced.sh")
    print("2. View logs in real-time: ./view_logs.sh worker")
    print("3. Use /worker_logs command in bot to see logs")
    print("\n⚠️ Backup files created with .backup extension")

if __name__ == "__main__":
    main()