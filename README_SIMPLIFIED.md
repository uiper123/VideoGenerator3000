# Video Bot - Упрощенная версия

Упрощенная версия бота для обработки видео без базы данных и админки.

## Что изменилось

### Удалено:
- ❌ База данных PostgreSQL
- ❌ Админ-панель
- ❌ Настройки пользователей
- ❌ Статистика
- ❌ Система ролей
- ❌ Шрифты и стили

### Оставлено:
- ✅ Обработка видео по ссылке
- ✅ Обработка загруженных файлов
- ✅ Нарезка на фрагменты
- ✅ Добавление субтитров
- ✅ Конвертация в формат 9:16

## Структура проекта

```
app/
├── bot/
│   ├── handlers/
│   │   ├── user_handlers.py      # Основные команды
│   │   └── video_handlers.py     # Обработка видео
│   └── keyboards/
│       └── main_menu.py          # Клавиатуры
├── config/
│   ├── constants.py              # Константы
│   └── settings.py               # Настройки
├── services/
│   ├── google_drive.py           # Google Drive
│   ├── google_sheets.py          # Google Sheets
│   └── redis_service.py          # Redis
├── video_processing/
│   ├── downloader.py             # Скачивание видео
│   └── processor.py              # Обработка видео
├── workers/
│   ├── celery_app.py             # Celery конфигурация
│   ├── video_tasks.py            # Задачи обработки
│   └── upload_tasks.py           # Задачи загрузки
└── main.py                       # Точка входа
```

## Запуск

### 1. Настройка окружения

Создайте файл `.env`:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Google Services (опционально)
GOOGLE_CREDENTIALS_JSON_CONTENT=your_google_credentials_json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_SHEETS_ID=your_sheets_id

# Video Processing
VIDEO_TEMP_DIR=/tmp/videos
VIDEO_MAX_DURATION=10800
VIDEO_MAX_FILE_SIZE=2147483648
VIDEO_OUTPUT_QUALITY=1080p

# Debug
DEBUG=true
LOG_LEVEL=INFO
```

### 2. Запуск через Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### 3. Локальный запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск Redis (если не используете Docker)
redis-server

# Запуск Celery Worker
celery -A app.workers.celery_app worker --loglevel=info

# Запуск бота
python -m app.main
```

## Использование

1. Запустите бота командой `/start`
2. Нажмите "🎬 Обработать видео"
3. Выберите способ ввода:
   - "📎 Вставить ссылку" - для YouTube, TikTok и др.
   - "📁 Загрузить файл" - для локальных файлов
4. Настройте параметры обработки
5. Нажмите "✅ Начать обработку"

## Поддерживаемые источники

- YouTube (youtube.com, youtu.be)
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Vimeo (vimeo.com)
- Twitter/X (twitter.com, x.com)

## Поддерживаемые форматы файлов

- MP4, AVI, MKV, MOV
- WMV, FLV, WebM, M4V

## Ограничения

- Максимальная длительность: 3 часа
- Максимальный размер файла: 2GB (для загрузки через Telegram)
- Формат вывода: 1080x1920 (9:16)

## Архитектура

Упрощенная архитектура без базы данных:

1. **Telegram Bot** - принимает запросы пользователей
2. **Redis** - очередь задач для Celery
3. **Celery Worker** - обрабатывает видео
4. **FFmpeg** - конвертация и обработка видео
5. **yt-dlp** - скачивание видео с платформ

## Мониторинг

Логи доступны через Docker Compose:

```bash
# Логи бота
docker-compose logs -f videobot

# Логи Celery Worker
docker-compose logs -f celery_worker

# Логи Redis
docker-compose logs -f redis
```

## Troubleshooting

### Проблемы со скачиванием YouTube

1. Проверьте, что ссылка корректная
2. Некоторые видео могут быть заблокированы
3. Попробуйте другое видео

### Проблемы с обработкой

1. Проверьте логи Celery Worker
2. Убедитесь, что FFmpeg установлен
3. Проверьте доступное место на диске

### Проблемы с Redis

1. Убедитесь, что Redis запущен
2. Проверьте настройки подключения в `.env`
3. Перезапустите сервисы

## Восстановление полной функциональности

Если нужно вернуть базу данных и админку:

1. Восстановите файлы из git истории
2. Добавьте PostgreSQL в docker-compose.yml
3. Восстановите зависимости в requirements.txt
4. Запустите миграции базы данных