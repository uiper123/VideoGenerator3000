# 🚀 VideoGenerator3000 - Render Deployment Guide

## 📋 Подготовка к деплою

### 1. Создание аккаунта на Render
1. Зарегистрируйтесь на [render.com](https://render.com)
2. Подключите ваш GitHub репозиторий

### 2. Подготовка переменных окружения
Подготовьте следующие переменные:

#### Обязательные:
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота
- `TELEGRAM_ADMIN_IDS` - ваш Telegram ID (например: 123456789)

#### Google Drive (опционально):
- `GOOGLE_CREDENTIALS_JSON_CONTENT` - содержимое файла google-credentials.json
- `GOOGLE_DRIVE_FOLDER_ID` - ID папки в Google Drive для сохранения видео

## 🐳 Способ 1: Автоматический деплой через render.yaml

### Шаги:
1. **Форкните репозиторий** или загрузите код на GitHub
2. **В Render Dashboard:**
   - Нажмите "New" → "Blueprint"
   - Подключите ваш GitHub репозиторий
   - Render автоматически найдет `render.yaml` и создаст все сервисы

3. **Настройте переменные окружения:**
   - PostgreSQL создастся автоматически
   - Redis создастся автоматически
   - В настройках Web Service добавьте:
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_ADMIN_IDS`
     - `GOOGLE_CREDENTIALS_JSON_CONTENT` (если нужен Google Drive)
     - `GOOGLE_DRIVE_FOLDER_ID` (если нужен Google Drive)

### Что создастся автоматически:
- ✅ PostgreSQL Database (Free tier)
- ✅ Redis Cache (Free tier)
- ✅ Web Service (Main bot)
- ✅ Background Worker (Celery)

## 🔧 Способ 2: Ручная настройка

### 1. Создание PostgreSQL Database
1. **New** → **PostgreSQL**
2. **Name:** `videobot-postgres`
3. **Database:** `videobot`
4. **User:** `videobot`
5. **Region:** выберите ближайший
6. **Plan:** Free
7. Нажмите **Create Database**

### 2. Создание Redis
1. **New** → **Redis**
2. **Name:** `videobot-redis`
3. **Plan:** Free
4. Нажмите **Create Redis**

### 3. Создание Web Service (Main Bot)
1. **New** → **Web Service**
2. **Connect Repository:** выберите ваш репозиторий
3. **Name:** `videobot-app`
4. **Environment:** Docker
5. **Plan:** Free
6. **Build Command:** `pip install -r requirements.txt`
7. **Start Command:** `python start_render.py`

#### Environment Variables:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_IDS=your_telegram_id_here
DATABASE_URL=[Auto-filled from PostgreSQL]
REDIS_URL=[Auto-filled from Redis]
CELERY_BROKER_URL=[Auto-filled from Redis]
CELERY_RESULT_BACKEND=[Auto-filled from Redis]
DEBUG=false
LOG_LEVEL=INFO
GOOGLE_CREDENTIALS_JSON_CONTENT=your_google_credentials_json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
```

### 4. Создание Background Worker (Celery)
1. **New** → **Background Worker**
2. **Connect Repository:** тот же репозиторий
3. **Name:** `videobot-worker`
4. **Environment:** Docker
5. **Plan:** Free
6. **Build Command:** `pip install -r requirements.txt`
7. **Start Command:** `python start_worker_render.py`

#### Environment Variables (те же что и для Web Service):
```
DATABASE_URL=[Auto-filled from PostgreSQL]
REDIS_URL=[Auto-filled from Redis]
CELERY_BROKER_URL=[Auto-filled from Redis]
CELERY_RESULT_BACKEND=[Auto-filled from Redis]
GOOGLE_CREDENTIALS_JSON_CONTENT=your_google_credentials_json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
```

## 🔍 Мониторинг и диагностика

### Health Check
Ваш бот будет доступен по адресу: `https://your-app-name.onrender.com/health`

Ответ должен быть:
```json
{
  "status": "healthy",
  "service": "VideoGenerator3000",
  "timestamp": "2025-01-21T12:00:00.000Z",
  "version": "1.0.0"
}
```

### Логи
- **Web Service логи:** Render Dashboard → your-app → Logs
- **Worker логи:** Render Dashboard → your-worker → Logs
- **Database логи:** Render Dashboard → your-postgres → Logs

### Команды диагностики в боте:
- `/status` - статус системы
- `/check_drive` - проверка Google Drive (если настроен)

## ⚠️ Важные моменты

### Ограничения Free Tier:
- **Web Service:** 750 часов в месяц
- **Background Worker:** 750 часов в месяц
- **PostgreSQL:** 1GB хранилища
- **Redis:** 25MB памяти
- **Bandwidth:** 100GB в месяц

### Автоматическое засыпание:
- Free tier сервисы засыпают после 15 минут неактивности
- Первый запрос после сна может занять 30-60 секунд
- Для постоянной работы нужен Paid план

### Рекомендации:
1. **Используйте webhook вместо polling** для лучшей производительности
2. **Настройте мониторинг** через внешние сервисы (UptimeRobot)
3. **Регулярно проверяйте логи** на наличие ошибок
4. **Настройте Google Drive** для сохранения обработанных видео

## 🔧 Troubleshooting

### Проблема: Сервис не запускается
**Решение:**
1. Проверьте логи в Render Dashboard
2. Убедитесь что все переменные окружения настроены
3. Проверьте что PostgreSQL и Redis запущены

### Проблема: Celery Worker не работает
**Решение:**
1. Проверьте логи Background Worker
2. Убедитесь что REDIS_URL правильно настроен
3. Проверьте что DATABASE_URL доступен для worker'а

### Проблема: Google Drive не работает
**Решение:**
1. Используйте команду `/check_drive` в боте
2. Проверьте что `GOOGLE_CREDENTIALS_JSON_CONTENT` правильно настроен
3. Убедитесь что токен Google OAuth не истек

### Проблема: Видео не обрабатываются
**Решение:**
1. Проверьте что Celery Worker запущен
2. Проверьте логи worker'а на наличие ошибок
3. Убедитесь что FFmpeg доступен в контейнере

## 📊 Мониторинг производительности

### Метрики для отслеживания:
- **Response Time** - время ответа health check
- **Memory Usage** - использование памяти
- **CPU Usage** - использование процессора
- **Database Connections** - количество подключений к БД
- **Queue Length** - длина очереди Celery

### Настройка алертов:
1. Используйте Render встроенные алерты
2. Настройте внешний мониторинг (UptimeRobot, Pingdom)
3. Мониторьте логи на наличие ошибок

## 🎯 Оптимизация для Render

### Для лучшей производительности:
1. **Используйте webhook** вместо polling
2. **Оптимизируйте Docker образ** - минимизируйте размер
3. **Настройте кэширование** - используйте Redis эффективно
4. **Ограничьте concurrency** Celery worker'а до 1-2
5. **Настройте таймауты** для длительных операций

Теперь ваш VideoGenerator3000 готов к деплою на Render! 🚀