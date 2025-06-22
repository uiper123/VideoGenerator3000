# 🚀 Quick Start Guide - Video Bot

Быстрый старт для запуска Telegram бота для автоматической нарезки видео.

## 📋 Предварительные требования

- Python 3.11+
- PostgreSQL
- Redis
- FFmpeg
- Telegram Bot Token (от [@BotFather](https://t.me/botfather))

## ⚡ Быстрый запуск

### 1. Клонирование и установка

```bash
git clone <repository-url>
cd VideoGenerator3000

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Копирование примера конфигурации
cp env.example .env

# Отредактируйте .env файл с вашими настройками
```

**Минимальные настройки для запуска:**
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
DATABASE_URL=postgresql+asyncpg://videobot:password@localhost:5432/videobot
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 3. Запуск с Docker Compose (Рекомендуется)

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f videobot

# Остановка
docker-compose down
```

### 4. Ручной запуск

**Терминал 1: База данных и Redis**
```bash
# Запуск PostgreSQL и Redis (если не используете Docker)
# Или используйте только нужные сервисы из docker-compose:
docker-compose up -d postgres redis
```

**Терминал 2: Celery Worker**
```bash
celery -A app.workers.celery_app worker --loglevel=info
```

**Терминал 3: Celery Beat (опционально)**
```bash
celery -A app.workers.celery_app beat --loglevel=info
```

**Терминал 4: Telegram Bot**
```bash
python run_bot.py
# или
python app/main.py
```

## 🎯 Первый запуск

1. **Создайте бота в Telegram:**
   - Напишите [@BotFather](https://t.me/botfather)
   - Выполните команду `/newbot`
   - Скопируйте токен в `.env` файл

2. **Запустите бота:**
   ```bash
   docker-compose up -d
   ```

3. **Протестируйте бота:**
   - Найдите вашего бота в Telegram
   - Отправьте `/start`
   - Попробуйте обработать тестовое видео

## 🔧 Разработка

### Структура проекта
```
VideoGenerator3000/
├── app/                    # Основное приложение
│   ├── bot/               # Telegram bot логика
│   ├── workers/           # Celery задачи
│   ├── database/          # Модели БД
│   ├── config/            # Конфигурация
│   └── main.py           # Точка входа
├── requirements.txt       # Python зависимости
├── docker-compose.yml     # Docker конфигурация
└── README.md             # Полная документация
```

### Полезные команды

```bash
# Проверка статуса сервисов
docker-compose ps

# Перезапуск бота
docker-compose restart videobot

# Просмотр логов конкретного сервиса
docker-compose logs -f videobot

# Подключение к базе данных
docker-compose exec postgres psql -U videobot -d videobot

# Подключение к Redis
docker-compose exec redis redis-cli

# Мониторинг Celery (Flower)
open http://localhost:5555
```

### Режимы работы

**Polling (по умолчанию):**
- Бот получает обновления через long polling
- Подходит для разработки и небольших нагрузок

**Webhook:**
- Установите `TELEGRAM_WEBHOOK_URL` в `.env`
- Telegram отправляет обновления на ваш сервер
- Подходит для production

## ⚠️ Устранение проблем

### Общие проблемы

1. **"Database connection failed"**
   ```bash
   # Проверьте запуск PostgreSQL
   docker-compose ps postgres
   
   # Проверьте подключение
   docker-compose exec postgres pg_isready -U videobot
   ```

2. **"Redis connection failed"**
   ```bash
   # Проверьте запуск Redis
   docker-compose ps redis
   
   # Проверьте подключение
   docker-compose exec redis redis-cli ping
   ```

3. **"Bot token is invalid"**
   - Проверьте токен в `.env` файле
   - Убедитесь, что токен не содержит лишних пробелов
   - Создайте новый токен через @BotFather

4. **"Celery tasks not working"**
   ```bash
   # Проверьте Celery worker
   docker-compose logs celery_worker
   
   # Перезапустите worker
   docker-compose restart celery_worker
   ```

### Логи и отладка

```bash
# Все логи
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f videobot

# Логи с ограничением
docker-compose logs --tail=100 videobot

# Реальное время с фильтрацией
docker-compose logs -f | grep ERROR
```

## 📚 Дополнительно

- **Полная документация:** [README.md](README.md)
- **Детальный план:** [detailed_video_bot_plan.md](detailed_video_bot_plan.md)
- **Конфигурация:** [env.example](env.example)

## 🆘 Поддержка

Если возникли проблемы:

1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что все сервисы запущены: `docker-compose ps`
3. Проверьте настройки в `.env` файле
4. Обратитесь к [полной документации](README.md)

---

**Готово! 🎉** Ваш Video Bot должен быть запущен и готов к работе. 