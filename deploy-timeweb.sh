#!/bin/bash

# ===========================================
# СКРИПТ РАЗВЕРТЫВАНИЯ VIDEO BOT НА TIMEWEB
# ===========================================

set -e  # Остановка при ошибке

echo "🚀 Начинаем развертывание Video Bot на TimeWeb..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Проверка, что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then
    error "Пожалуйста, запустите скрипт от имени root: sudo $0"
fi

# Шаг 1: Обновление системы
log "Шаг 1/8: Обновление системы..."
apt update && apt upgrade -y

# Шаг 2: Установка Docker
log "Шаг 2/8: Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    log "Docker установлен успешно"
else
    log "Docker уже установлен"
fi

# Шаг 3: Установка Docker Compose
log "Шаг 3/8: Установка Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    log "Docker Compose установлен успешно"
else
    log "Docker Compose уже установлен"
fi

# Шаг 4: Установка дополнительных утилит
log "Шаг 4/8: Установка дополнительных утилит..."
apt install -y git nano htop curl wget ufw

# Шаг 5: Настройка файрвола
log "Шаг 5/8: Настройка файрвола..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 8000/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Шаг 6: Создание директории проекта
log "Шаг 6/8: Создание директории проекта..."
PROJECT_DIR="/opt/videobot"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Если проект уже существует, создаем бэкап
if [ -f "docker-compose.yml" ]; then
    warn "Найден существующий проект. Создаем бэкап..."
    tar -czf "backup-$(date +%Y%m%d-%H%M%S).tar.gz" . 2>/dev/null || true
fi

# Шаг 7: Настройка переменных окружения
log "Шаг 7/8: Настройка переменных окружения..."

if [ ! -f ".env" ]; then
    log "Создание файла .env..."
    cat > .env << 'EOF'
# Telegram Bot
TELEGRAM_BOT_TOKEN=

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Application
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO

# Video Processing
VIDEO_TEMP_DIR=/tmp/videos
VIDEO_MAX_DURATION=10800
VIDEO_MAX_FILE_SIZE=2147483648
VIDEO_OUTPUT_QUALITY=1080p
VIDEO_MAX_CONCURRENT_TASKS=2

# Google Services (Optional)
GOOGLE_CREDENTIALS_JSON_CONTENT=
GOOGLE_DRIVE_FOLDER_ID=
GOOGLE_SHEETS_ID=
EOF

    warn "ВАЖНО: Отредактируйте файл .env и добавьте ваш TELEGRAM_BOT_TOKEN!"
    warn "Используйте команду: nano .env"
else
    log "Файл .env уже существует"
fi

# Шаг 8: Создание systemd сервиса
log "Шаг 8/8: Создание systemd сервиса..."
cat > /etc/systemd/system/videobot.service << EOF
[Unit]
Description=Video Bot Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=300
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable videobot.service

# Создание скрипта мониторинга
log "Создание скрипта мониторинга..."
cat > $PROJECT_DIR/monitor.sh << 'EOF'
#!/bin/bash
cd /opt/videobot

# Проверка статуса контейнеров
if ! docker-compose ps | grep -q "Up"; then
    echo "$(date): Restarting containers..."
    docker-compose restart
fi

# Очистка старых файлов (старше 7 дней)
find /var/lib/docker/volumes/videobot_video_temp/_data -type f -mtime +7 -delete 2>/dev/null || true
find /var/lib/docker/volumes/videobot_processed_temp/_data -type f -mtime +7 -delete 2>/dev/null || true

# Проверка использования диска
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "$(date): High disk usage: ${DISK_USAGE}%. Cleaning up..."
    docker system prune -f
fi
EOF

chmod +x $PROJECT_DIR/monitor.sh

# Добавление в crontab
(crontab -l 2>/dev/null; echo "*/10 * * * * $PROJECT_DIR/monitor.sh >> /var/log/videobot-monitor.log 2>&1") | crontab -

# Создание скрипта управления
cat > $PROJECT_DIR/manage.sh << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "Запуск Video Bot..."
        docker-compose up -d
        ;;
    stop)
        echo "Остановка Video Bot..."
        docker-compose down
        ;;
    restart)
        echo "Перезапуск Video Bot..."
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f
        ;;
    status)
        docker-compose ps
        ;;
    update)
        echo "Обновление Video Bot..."
        docker-compose down
        docker-compose pull
        docker-compose up -d --build
        ;;
    clean)
        echo "Очистка временных файлов..."
        docker system prune -f
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|logs|status|update|clean}"
        exit 1
        ;;
esac
EOF

chmod +x $PROJECT_DIR/manage.sh

# Завершение
echo ""
echo "=============================================="
echo -e "${GREEN}✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО!${NC}"
echo "=============================================="
echo ""
echo -e "${BLUE}📁 Проект установлен в:${NC} $PROJECT_DIR"
echo -e "${BLUE}🔧 Файл настроек:${NC} $PROJECT_DIR/.env"
echo ""
echo -e "${YELLOW}⚠️  СЛЕДУЮЩИЕ ШАГИ:${NC}"
echo "1. Отредактируйте файл .env:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Добавьте ваш TELEGRAM_BOT_TOKEN в файл .env"
echo ""
echo "3. Запустите проект:"
echo "   cd $PROJECT_DIR"
echo "   ./manage.sh start"
echo ""
echo -e "${BLUE}🛠️  КОМАНДЫ УПРАВЛЕНИЯ:${NC}"
echo "   ./manage.sh start    - Запуск"
echo "   ./manage.sh stop     - Остановка"
echo "   ./manage.sh restart  - Перезапуск"
echo "   ./manage.sh logs     - Просмотр логов"
echo "   ./manage.sh status   - Статус сервисов"
echo "   ./manage.sh update   - Обновление"
echo "   ./manage.sh clean    - Очистка"
echo ""
echo -e "${BLUE}📊 МОНИТОРИНГ:${NC}"
echo "   docker stats                    - Использование ресурсов"
echo "   tail -f /var/log/videobot-monitor.log - Логи мониторинга"
echo ""
echo -e "${GREEN}🎉 Удачного использования!${NC}"
echo "=============================================="