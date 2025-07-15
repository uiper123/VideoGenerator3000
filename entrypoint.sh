#!/bin/bash
set -e

# Ограничение количества потоков для библиотек
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
export VECLIB_MAXIMUM_THREADS=4
export NUMEXPR_NUM_THREADS=4

# Ограничение для faster-whisper
export WHISPER_CPU_THREADS=4
export WHISPER_NUM_WORKERS=2

# Определяем команду для запуска
if [ "$1" = "bot" ]; then
    echo "Starting Telegram bot..."
    exec python run_bot.py
elif [ "$1" = "worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
elif [ "$1" = "beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A app.workers.celery_app beat --loglevel=info
elif [ "$1" = "flower" ]; then
    echo "Starting Flower..."
    exec celery -A app.workers.celery_app flower --port=5555
else
    echo "Command not recognized: $1"
    echo "Available commands: bot, worker, beat, flower"
    exit 1
fi 