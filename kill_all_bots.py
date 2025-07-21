#!/usr/bin/env python3
"""
Скрипт для остановки всех процессов бота
"""
import os
import subprocess
import signal
import psutil

def kill_bot_processes():
    """Останавливает все процессы связанные с ботом"""
    print("🔍 Поиск процессов бота...")
    
    # Список процессов для поиска
    process_names = [
        'python',
        'celery',
        'video_bot',
        'main.py',
        'run_bot.py'
    ]
    
    killed_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Проверяем имя процесса и командную строку
            proc_info = proc.info
            cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
            
            # Ищем процессы связанные с ботом
            if any(name in cmdline.lower() for name in ['video_bot', 'telegram', 'aiogram', 'celery']):
                print(f"🎯 Найден процесс: PID {proc_info['pid']} - {cmdline[:100]}...")
                
                try:
                    # Пытаемся завершить процесс мягко
                    proc.terminate()
                    proc.wait(timeout=5)
                    killed_processes.append(proc_info['pid'])
                    print(f"✅ Процесс {proc_info['pid']} остановлен")
                except psutil.TimeoutExpired:
                    # Если не получилось мягко, убиваем принудительно
                    proc.kill()
                    killed_processes.append(proc_info['pid'])
                    print(f"💀 Процесс {proc_info['pid']} убит принудительно")
                except Exception as e:
                    print(f"❌ Не удалось остановить процесс {proc_info['pid']}: {e}")
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if killed_processes:
        print(f"\n✅ Остановлено процессов: {len(killed_processes)}")
        print(f"PIDs: {killed_processes}")
    else:
        print("\n✅ Активных процессов бота не найдено")
    
    return len(killed_processes)

def kill_by_port():
    """Освобождает порты используемые ботом"""
    print("\n🔍 Проверка портов...")
    
    # Порты которые может использовать бот
    ports_to_check = [8000, 5555, 6379, 5432]  # FastAPI, Flower, Redis, PostgreSQL
    
    for port in ports_to_check:
        try:
            # Ищем процессы использующие порт
            result = subprocess.run(
                ['netstat', '-ano'], 
                capture_output=True, 
                text=True, 
                shell=True
            )
            
            lines = result.stdout.split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    # Извлекаем PID
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit():
                            print(f"🎯 Порт {port} используется процессом {pid}")
                            try:
                                os.kill(int(pid), signal.SIGTERM)
                                print(f"✅ Процесс {pid} (порт {port}) остановлен")
                            except:
                                print(f"❌ Не удалось остановить процесс {pid}")
        except:
            continue

def main():
    """Основная функция"""
    print("🛑 VideoGenerator3000 - Process Killer")
    print("=" * 40)
    
    # Останавливаем процессы по имени
    killed_count = kill_bot_processes()
    
    # Освобождаем порты
    kill_by_port()
    
    print("\n" + "=" * 40)
    print("✅ Очистка завершена!")
    print("\n💡 Теперь можно запускать бота заново")
    print("Рекомендуется подождать 10-15 секунд перед запуском")

if __name__ == "__main__":
    main()