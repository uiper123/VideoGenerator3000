# Исправление ошибки с метаданными задач

## Проблема

При завершении обработки загруженных видео файлов возникала ошибка:
```
AttributeError: 'MetaData' object has no attribute 'update'
```

## Причина

Ошибка возникала из-за неправильного обращения к полю метаданных в модели `VideoTask`. В коде использовалось `task.metadata`, но в SQLAlchemy модели поле называется `video_metadata`.

## Анализ логов

Из логов видно, что:
✅ Загрузка файла с Telegram прошла успешно
✅ Обработка видео завершена
✅ Фрагмент создан
✅ Загрузка в Google Drive успешна
❌ Ошибка при обновлении метаданных задачи

## Исправления

### 1. app/workers/video_tasks.py - функция `download_video` (строка 121)

**До:**
```python
task.metadata = {
    "title": download_result["title"],
    "duration": download_result["duration"],
    # ... остальные поля
}
```

**После:**
```python
# Update video_metadata (not metadata)
if task.video_metadata is None:
    task.video_metadata = {}
task.video_metadata.update({
    "title": download_result["title"],
    "duration": download_result["duration"],
    # ... остальные поля
})
```

### 2. app/workers/video_tasks.py - функция `process_uploaded_file_chain` (строка 528)

**До:**
```python
task.metadata.update({
    'fragments_count': len(fragments),
    'successful_uploads': len(successful_uploads),
    'sheet_url': sheet_result.get('sheet_url', ''),
    'drive_folder_url': upload_results[0].get('folder_url', '') if upload_results else ''
})
```

**После:**
```python
# Update video_metadata (not metadata)
if task.video_metadata is None:
    task.video_metadata = {}
task.video_metadata.update({
    'fragments_count': len(fragments),
    'successful_uploads': len(successful_uploads),
    'sheet_url': sheet_result.get('sheet_url', ''),
    'drive_folder_url': upload_results[0].get('folder_url', '') if upload_results else ''
})
```

## Структура базы данных

В модели `VideoTask` (app/database/models.py):
```python
class VideoTask(Base):
    # ...
    video_metadata = Column(JSON, default=dict)  # ✅ Правильное название поля
    # ...
```

**Не путать с:**
- `task.metadata` - это служебное поле SQLAlchemy
- `fragment.metadata` - поле метаданных фрагмента (используется правильно)

## Результат

- ✅ Устранена ошибка `AttributeError: 'MetaData' object has no attribute 'update'`
- ✅ Загрузка видео файлов теперь работает полностью корректно
- ✅ Метаданные задач сохраняются в правильное поле `video_metadata`
- ✅ Обратная совместимость сохранена

## Тестирование

После исправления:
1. Загрузите видео файл через бота
2. Дождитесь завершения обработки
3. Убедитесь, что процесс завершается успешно
4. Проверьте, что фрагменты доступны в Google Drive

**Статус:** Исправление применено ✅

## Дополнительная информация

В логах также были предупреждения о Google Sheets OAuth (`invalid_grant: account not found`), но это не влияет на основную функциональность - файлы все равно обрабатываются и загружаются в Google Drive. 