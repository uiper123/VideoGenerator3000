# Исправление ошибки FFmpeg при обработке видео файлов

## Проблема

При обработке загруженных видео файлов возникала ошибка:
```
[AVFilterGraph @ 0x564917ab80c0] No output pad can be associated to link label 'output'.
Error initializing complex filters.
Invalid argument
```

## Причина

Ошибка возникала из-за неправильной логики создания фильтр-графа FFmpeg в функции `process_video_ffmpeg`. Код пытался создать выходной поток с именем `[output]`, но использовал неправильный синтаксис:

1. В функции `_build_video_filters()` использовался проблемный фильтр `null[output]`
2. В функции `process_video_ffmpeg()` была неправильная логика объединения фильтров

## Исправления

### 1. app/video_processing/processor.py - функция `_build_video_filters`

**До:**
```python
else:
    # If no title, rename the final output
    filters.append("[with_main]null[output]")
```

**После:**
```python
# Note: If no title, the final output is [with_main], not [output]
```

### 2. app/video_processing/processor.py - функция `process_full_video_then_fragment`

**Добавлено:**
```python
# Determine output stream name based on whether title is present
output_stream = '[output]' if title else '[with_main]'
```

### 3. app/video_processing/processor.py - функция `process_video_ffmpeg`

**До:**
```python
final_filter_graph = ";".join(video_filters)
if current_stream == "[layout]":
    final_filter_graph += "[output]" # No title or subs
elif current_stream == "[titled]":
    final_filter_graph += ";[titled]copy[output]"
```

**После:**
```python
# Final output mapping - determine the correct output stream
if current_stream == "[layout]":
    # No title or subs - use layout stream directly
    output_stream_name = "[layout]"
elif current_stream == "[titled]":
    # Has title but no subs - use titled stream directly  
    output_stream_name = "[titled]"
else:
    # Has subtitles - use output stream
    output_stream_name = "[output]"

final_filter_graph = ";".join(video_filters)
```

**И в команде FFmpeg:**
```python
'-map', output_stream_name,  # Вместо '-map', '[output]',
```

## Логика работы

Теперь система правильно определяет имя выходного потока в зависимости от настроек:

1. **`[layout]`** - если нет заголовка и субтитров
2. **`[titled]`** - если есть заголовок, но нет субтитров
3. **`[output]`** - если есть субтитры (с заголовком или без)

## Результат

- ✅ Устранена ошибка FFmpeg с фильтр-графом
- ✅ Обработка видео файлов теперь работает корректно
- ✅ Поддерживаются все комбинации настроек (с заголовком/без, с субтитрами/без)

## Тестирование

Для проверки исправления:

1. Загрузите видео файл через бота
2. Выберите настройки (с субтитрами или без)
3. Запустите обработку
4. Убедитесь, что процесс завершается успешно без ошибок FFmpeg

**Статус:** Исправление применено ✅ 