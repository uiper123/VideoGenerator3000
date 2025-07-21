# 🎬 VideoGenerator3000 - Colab Usage Guide

## 🚀 Быстрый старт

### 1. Загрузка в Google Colab
1. Откройте [Google Colab](https://colab.research.google.com/)
2. Загрузите файл `VideoGenerator3000_Colab.ipynb`
3. Выполните ячейки по порядку

### 2. Выполнение ячеек
- **Шаг 1**: Клонирование репозитория и системная настройка
- **Шаг 2**: Копирование файлов и исправление импортов
- **Шаг 3**: Настройка конфигурации (токен уже вставлен)
- **Шаг 4**: Запуск бота

## 🔧 Новые возможности в Colab версии

### 📊 Команды мониторинга в боте:
- `/start` - Приветствие и список команд
- `/status` - Статус системы и temp файлов
- `/logs` - Логи бота (последние 20 строк)
- `/worker_logs` - Логи Celery worker'ов (последние 30 строк)
- `/all_logs` - Все логи вместе
- `/check_drive` - **НОВОЕ!** Проверка Google Drive интеграции

### 🔍 Проверка Google Drive
Команда `/check_drive` покажет:
- ✅/❌ Установлены ли Google библиотеки
- ✅/❌ Найден ли файл `google-credentials.json`
- ✅/⚠️/❌ Статус токена `token.pickle`
- ✅/❌ Подключение к Google Drive API
- 📧 Email пользователя Google Drive
- ⏰ Время истечения токена

### 📋 Пример вывода `/check_drive`:
```
🔍 Google Drive Integration Check
========================================
✅ Libraries: Google libraries available
✅ Credentials: Credentials file found and valid
✅ Token: Token file found: token.pickle
   Valid: True
   Expired: False
   Expires in: 23.5 hours
✅ Drive Connection: Google Drive connection successful
   User: your-email@gmail.com

✅ Overall Status: SUCCESS
```

## 🛠️ Диагностика проблем

### Если видео не загружается в Google Drive:
1. Используйте `/check_drive` для диагностики
2. Проверьте статус токена
3. Если токен истек - обновите его

### Если нет логов worker'ов:
1. Убедитесь что Celery worker запущен
2. Проверьте папку `/content/videobot/logs/`
3. Используйте `/all_logs` для полной картины

### Если обработка зависает:
1. Используйте `/worker_logs` для проверки процесса
2. Проверьте размер temp файлов через `/status`
3. Очистите temp папку если нужно

## 📁 Структура файлов в Colab

```
/content/videobot/
├── app/                    # Основное приложение
├── temp/                   # Временные файлы
├── logs/                   # Логи
│   ├── bot.log            # Логи бота
│   ├── worker.log         # Логи worker'ов
│   └── celery_worker.log  # Логи Celery
├── fonts/                 # Шрифты (копируются из репозитория)
├── google_drive_checker.py # Проверка Google Drive
├── enhanced_worker_logger.py # Логирование worker'ов
├── .env                   # Конфигурация
└── main.py               # Точка входа
```

## 🔄 Мониторинг в реальном времени

### В Colab ячейках:
```python
# Просмотр логов в реальном времени
!tail -f /content/videobot/logs/worker.log

# Проверка процессов
!ps aux | grep -E '(celery|python)' | grep -v grep

# Размер temp файлов
!du -sh /content/videobot/temp/*
```

### В Telegram боте:
- Отправьте видео или YouTube ссылку
- Используйте `/worker_logs` для отслеживания прогресса
- Используйте `/check_drive` перед обработкой

## ⚠️ Важные моменты

### Ограничения Colab:
- Сессия живет 12-24 часа
- Все данные удаляются при перезапуске
- Ограниченные ресурсы CPU/RAM
- Максимум 30 минут на видео

### Рекомендации:
- Регулярно проверяйте статус через `/status`
- Используйте `/check_drive` перед важными задачами
- Сохраняйте резервные копии перед завершением сессии
- Очищайте temp файлы после обработки

## 🎯 Типичные сценарии использования

### 1. Обработка YouTube видео:
1. Отправьте ссылку боту
2. Используйте `/worker_logs` для отслеживания
3. Проверьте загрузку в Drive через `/check_drive`

### 2. Диагностика проблем:
1. `/status` - общий статус
2. `/all_logs` - все логи
3. `/check_drive` - статус Google Drive

### 3. Мониторинг ресурсов:
1. `/status` - temp файлы и размер
2. Colab ячейка с `!df -h /content`
3. Очистка через `!rm -rf /content/videobot/temp/*`

## 🔧 Устранение неполадок

### Проблема: "Данные файла не найдены"
**Решение**: Используйте `/worker_logs` для проверки процесса скачивания

### Проблема: Видео не загружается в Drive
**Решение**: `/check_drive` → проверьте токен → обновите если нужно

### Проблема: Долгая обработка
**Решение**: `/worker_logs` → проверьте прогресс FFmpeg

### Проблема: Нет логов worker'ов
**Решение**: Перезапустите Celery worker в отдельной ячейке

Теперь у вас есть полная диагностическая система для отслеживания всех процессов обработки видео! 🎉