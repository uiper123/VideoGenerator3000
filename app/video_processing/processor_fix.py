# Это исправление для строки 549 в processor.py
# Нужно заменить:
# subtitle_style=subtitle_style
# на:
# subtitle_style=subtitle_style,
# font_path=font_path

# В методе create_fragments_with_subtitles вызов _process_professional_fragment должен быть:
fragment_info = self._process_professional_fragment(
    video_path=video_path,
    output_path=fragment_path,
    start_time=start_time,
    duration=actual_duration,
    quality=quality,
    title=fragment_title,
    subtitle_style=subtitle_style,
    font_path=font_path
) 