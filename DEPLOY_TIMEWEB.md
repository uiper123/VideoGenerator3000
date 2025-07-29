# Развертывание Video Bot на TimeWeb

## Подготовка проекта

### 1. Структура проекта для TimeWeb

TimeWeb поддерживает Docker, поэтому мы будем использовать контейнеризацию.

### 2. Создание оптимизированного Dockerfile

```dockerfile
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание директорий для временных файлов
RUN mkdir -p /tmp/videos /tmp/processed

# Установка прав
RUN chmod +x entrypoint.sh

# Порт для приложения
EXPOSE 8000

# Команда запуска
CMD ["python", "-m", "app.main"]
```

### 3. Создание docker-compose для TimeWeb

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    container_name: videobot_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  videobot:
    build: .
    container_name: videobot_app
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - video_temp:/tmp/videos
      - ./fonts:/app/fonts
    restart: unless-stopped

  celery_worker:
    build: .
    container_name: videobot_celery_worker
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    env_file:
      - .env
    volumes:
      - video_temp:/tmp/videos
      - ./fonts:/app/fonts
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    restart: unless-stopped

volumes:
  redis_data:
  video_temp:
```

## Пошаговое развертывание на TimeWeb

### Шаг 1: Подготовка аккаунта TimeWeb

1. **Регистрация и вход**

   - Зайдите на [timeweb.cloud](https://timeweb.cloud)
   - Зарегистрируйтесь или войдите в аккаунт
   - Пополните баланс (минимум 100-200 рублей для тестирования)

2. **Создание проекта**
   - Перейдите в раздел "Облачные серверы"
   - Нажмите "Создать сервер"
   - Выберите конфигурацию:
     - **ОС**: Ubuntu 22.04 LTS
     - **Конфигурация**: минимум 2 CPU, 4GB RAM, 40GB SSD
     - **Регион**: выберите ближайший

### Шаг 2: Настройка сервера

1. **Подключение к серверу**

```bash
ssh root@YOUR_SERVER_IP
```

2. **Обновление системы**

```bash
apt update && apt upgrade -y
```

3. **Установка Docker и Docker Compose**

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker --version
docker-compose --version
```

4. **Установка дополнительных утилит**

```bash
apt install -y git nano htop
```

### Шаг 3: Загрузка проекта

1. **Клонирование репозитория**

```bash
cd /opt
git clone YOUR_REPOSITORY_URL videobot
cd videobot
```

2. **Или загрузка через SCP/SFTP**

```bash
# С локальной машины
scp -r ./project-folder root@YOUR_SERVER_IP:/opt/videobot
```

### Шаг 4: Настройка окружения

1. **Создание .env файла**

```bash
nano .env
```

2. **Содержимое .env файла**

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Video Processing
VIDEO_TEMP_DIR=/tmp/videos
VIDEO_MAX_DURATION=10800
VIDEO_MAX_FILE_SIZE=2147483648
VIDEO_OUTPUT_QUALITY=1080p
VIDEO_MAX_CONCURRENT_TASKS=2

# Google Services (опционально)
GOOGLE_CREDENTIALS_JSON_CONTENT=your_google_credentials_json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_SHEETS_ID=your_sheets_id

# YouTube Cookies (опционально)
YOUTUBE_COOKIES_CONTENT=your_youtube_cookies

# Debug
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Шаг 5: Настройка файрвола

1. **Настройка UFW**

```bash
ufw allow ssh
ufw allow 8000
ufw enable
```

2. **Проверка портов**

```bash
ufw status
```

### Шаг 6: Запуск приложения

1. **Сборка и запуск контейнеров**

```bash
cd /opt/videobot
docker-compose up -d --build
```

2. **Проверка статуса**

```bash
docker-compose ps
docker-compose logs -f
```

3. **Проверка работы**

```bash
curl http://localhost:8000/health
```

### Шаг 7: Настройка автозапуска

1. **Создание systemd сервиса**

```bash
nano /etc/systemd/system/videobot.service
```

2. **Содержимое сервиса**

```ini
[Unit]
Description=Video Bot Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/videobot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

3. **Активация сервиса**

```bash
systemctl daemon-reload
systemctl enable videobot.service
systemctl start videobot.service
```

### Шаг 8: Настройка мониторинга

1. **Создание скрипта мониторинга**

```bash
nano /opt/videobot/monitor.sh
```

```bash
#!/bin/bash
cd /opt/videobot

# Проверка статуса контейнеров
if ! docker-compose ps | grep -q "Up"; then
    echo "$(date): Restarting containers..."
    docker-compose restart
fi

# Очистка старых логов
find /tmp/videos -type f -mtime +7 -delete
find /tmp/processed -type f -mtime +7 -delete
```

2. **Добавление в crontab**

```bash
chmod +x /opt/videobot/monitor.sh
crontab -e

# Добавить строку:
*/5 * * * * /opt/videobot/monitor.sh >> /var/log/videobot-monitor.log 2>&1
```

## Настройка домена (опционально)

### Шаг 1: Настройка Nginx

1. **Установка Nginx**

```bash
apt install -y nginx
```

2. **Создание конфигурации**

```bash
nano /etc/nginx/sites-available/videobot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Активация конфигурации**

```bash
ln -s /etc/nginx/sites-available/videobot /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Шаг 2: SSL сертификат

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## Мониторинг и логи

### Просмотр логов

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f videobot
docker-compose logs -f celery_worker
docker-compose logs -f redis

# Системные логи
journalctl -u videobot.service -f
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование диска
df -h
du -sh /tmp/videos /tmp/processed

# Память и CPU
htop
```

## Обновление приложения

```bash
cd /opt/videobot

# Остановка сервисов
docker-compose down

# Обновление кода
git pull origin main

# Пересборка и запуск
docker-compose up -d --build

# Проверка
docker-compose ps
```

## Резервное копирование

```bash
# Создание бэкапа
tar -czf videobot-backup-$(date +%Y%m%d).tar.gz /opt/videobot

# Бэкап Redis данных
docker exec videobot_redis redis-cli BGSAVE
```

## Troubleshooting

### Проблемы с памятью

```bash
# Увеличение swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Проблемы с дисковым пространством

```bash
# Очистка Docker
docker system prune -a

# Очистка временных файлов
rm -rf /tmp/videos/* /tmp/processed/*
```

### Проблемы с сетью

```bash
# Проверка портов
netstat -tlnp | grep :8000

# Проверка DNS
nslookup google.com
```

## Стоимость на TimeWeb

**Примерная стоимость в месяц:**

- Сервер 2 CPU, 4GB RAM, 40GB SSD: ~800-1200 рублей
- Трафик: обычно включен
- Дополнительные услуги: по необходимости

**Рекомендации по экономии:**

- Используйте автоматическое масштабирование
- Настройте мониторинг ресурсов
- Регулярно очищайте временные файлы
- Оптимизируйте настройки Celery

Проект готов к работе на TimeWeb! 🚀
