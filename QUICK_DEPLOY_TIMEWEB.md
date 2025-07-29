# 🚀 Быстрое развертывание на TimeWeb

## Подготовка (5 минут)

### 1. Создайте сервер на TimeWeb
- Зайдите на [timeweb.cloud](https://timeweb.cloud)
- Создайте сервер: **Ubuntu 22.04**, минимум **2 CPU, 4GB RAM, 40GB SSD**
- Получите IP адрес сервера

### 2. Получите токен Telegram бота
- Напишите @BotFather в Telegram
- Создайте нового бота: `/newbot`
- Скопируйте токен (например: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Автоматическое развертывание (10 минут)

### 1. Подключитесь к серверу
```bash
ssh root@YOUR_SERVER_IP
```

### 2. Скачайте и запустите скрипт развертывания
```bash
# Скачивание проекта
cd /opt
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git videobot
cd videobot

# Или загрузите файлы через SCP/SFTP

# Запуск автоматического развертывания
chmod +x deploy-timeweb.sh
./deploy-timeweb.sh
```

### 3. Настройте переменные окружения
```bash
nano /opt/videobot/.env
```

**Обязательно заполните:**
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Опционально (для Google Drive):**
```env
GOOGLE_CREDENTIALS_JSON_CONTENT={"type":"service_account",...}
GOOGLE_DRIVE_FOLDER_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

### 4. Запустите проект
```bash
cd /opt/videobot
./manage.sh start
```

### 5. Проверьте работу
```bash
# Статус сервисов
./manage.sh status

# Логи
./manage.sh logs

# Проверка здоровья
curl http://localhost:8000/health
```

## Готово! 🎉

Ваш бот работает и готов к использованию!

## Команды управления

```bash
cd /opt/videobot

./manage.sh start    # Запуск
./manage.sh stop     # Остановка  
./manage.sh restart  # Перезапуск
./manage.sh logs     # Просмотр логов
./manage.sh status   # Статус сервисов
./manage.sh update   # Обновление
./manage.sh clean    # Очистка временных файлов
```

## Мониторинг

```bash
# Использование ресурсов
docker stats

# Логи мониторинга
tail -f /var/log/videobot-monitor.log

# Использование диска
df -h
```

## Troubleshooting

### Бот не отвечает
```bash
# Проверьте логи
./manage.sh logs

# Перезапустите сервисы
./manage.sh restart
```

### Проблемы с памятью
```bash
# Добавьте swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Очистка места на диске
```bash
# Очистка Docker
docker system prune -a

# Очистка временных файлов
./manage.sh clean
```

## Настройка домена (опционально)

### 1. Установите Nginx
```bash
apt install -y nginx
```

### 2. Создайте конфигурацию
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
    }
}
```

### 3. Активируйте конфигурацию
```bash
ln -s /etc/nginx/sites-available/videobot /etc/nginx/sites-enabled/
systemctl restart nginx
```

### 4. Установите SSL
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## Стоимость

**Примерная стоимость на TimeWeb:**
- Сервер 2 CPU, 4GB RAM: ~800-1200₽/месяц
- Трафик: обычно включен
- Домен: ~200-500₽/год (опционально)

**Итого: ~1000₽/месяц** для полнофункционального бота

---

**Нужна помощь?** Проверьте логи: `./manage.sh logs`