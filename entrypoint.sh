#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# The first argument to the script is the type of service to run
SERVICE_TYPE="$1"

if [ "$SERVICE_TYPE" = "bot" ]; then
    echo "Starting Telegram Bot..."
    exec python run_bot.py
elif [ "$SERVICE_TYPE" = "worker" ]; then
    echo "Starting Celery Worker..."
    exec celery -A app.workers.celery_app.celery_app worker -l info
elif [ "$SERVICE_TYPE" = "beat" ]; then
    echo "Starting Celery Beat..."
    exec celery -A app.workers.celery_app.celery_app beat -l info
else
    echo "Error: Unknown service type '$SERVICE_TYPE'"
    exit 1
fi 