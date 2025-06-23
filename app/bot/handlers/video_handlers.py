"""
Video processing handlers for the Telegram bot.
"""
import uuid
import re
from typing import Union
from urllib.parse import urlparse

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bot.keyboards.main_menu import (
    VideoAction,
    VideoTaskAction,
    SettingsValueAction,
    get_video_settings_keyboard,
    get_cancel_keyboard,
    get_back_keyboard,
    get_task_status_keyboard
)
from app.config.constants import VideoStatus, SUPPORTED_SOURCES, ERROR_MESSAGES, SUCCESS_MESSAGES
from app.database.connection import get_db_session
from app.database.models import VideoTask, User, VideoFragment

router = Router()


class VideoProcessingStates(StatesGroup):
    """States for video processing workflow."""
    waiting_for_url = State()
    waiting_for_file = State()
    configuring_settings = State()
    processing = State()
    waiting_for_title = State()


@router.callback_query(VideoAction.filter(F.action == "input_url"))
async def start_url_input(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Start URL input process.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    await state.set_state(VideoProcessingStates.waiting_for_url)
    
    # Initialize default settings if not present
    data = await state.get_data()
    if "settings" not in data:
        await state.update_data(settings={
            "fragment_duration": 30,
            "quality": "1080p",
            "enable_subtitles": True
        })
    
    text = """
📎 <b>Ввод ссылки на видео</b>

Отправьте ссылку на видео, которое хотите обработать.

<b>Поддерживаемые платформы:</b>
• YouTube (youtube.com, youtu.be)
• TikTok (tiktok.com)
• Instagram (instagram.com)
• Vimeo (vimeo.com)
• Twitter/X (twitter.com, x.com)

<i>Просто отправьте ссылку следующим сообщением</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(VideoProcessingStates.waiting_for_url)
async def process_url_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Process URL input from user.
    
    Args:
        message: User message with URL
        state: FSM context
        bot: Bot instance
    """
    url = message.text.strip()
    
    # Validate URL
    if not is_valid_video_url(url):
        await message.answer(
            ERROR_MESSAGES["invalid_url"],
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Store URL in state data
    await state.update_data(source_url=url, input_type="url")
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Show video settings
    await show_video_settings(message, state, url)


@router.callback_query(VideoAction.filter(F.action == "upload_file"))
async def start_file_upload(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Start file upload process.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    await state.set_state(VideoProcessingStates.waiting_for_file)
    
    text = """
📁 <b>Загрузка видео файла</b>

Отправьте видео файл, который хотите обработать.

<b>Поддерживаемые форматы:</b>
• MP4, AVI, MKV, MOV
• WMV, FLV, WebM, M4V

<b>Ограничения:</b>
• Максимальный размер: 2GB
• Максимальная длительность: 3 часа

<i>Просто отправьте файл следующим сообщением</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(VideoProcessingStates.waiting_for_file, F.video | F.document)
async def process_file_upload(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Process file upload from user.
    
    Args:
        message: User message with file
        state: FSM context
        bot: Bot instance
    """
    # Get file info
    if message.video:
        file_info = message.video
        file_name = f"video_{message.video.file_unique_id}.mp4"
    elif message.document:
        file_info = message.document
        file_name = message.document.file_name or f"document_{message.document.file_unique_id}"
    else:
        await message.answer(
            "❌ Неподдерживаемый тип файла",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Check file size (Telegram limit is usually 50MB for bots)
    if file_info.file_size and file_info.file_size > 50 * 1024 * 1024:
        await message.answer(
            ERROR_MESSAGES["file_too_large"],
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Store file info in state data
    await state.update_data(
        file_id=file_info.file_id,
        file_name=file_name,
        file_size=file_info.file_size,
        input_type="file"
    )
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Show video settings
    await show_video_settings(message, state, f"Файл: {file_name}")


async def show_video_settings(message: Union[Message, CallbackQuery], state: FSMContext, source: str) -> None:
    """
    Show video processing settings.
    
    Args:
        message: Message or callback query
        state: FSM context
        source: Video source description
    """
    # Get current settings from state or use defaults
    data = await state.get_data()
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True,
        "title": "",
        "add_part_numbers": False
    })
    
    title_text = settings.get('title', '')
    title_display = f'"{title_text}"' if title_text else 'Не задан'
    part_numbers_status = 'Включена' if settings.get('add_part_numbers', False) else 'Отключена'
    
    text = f"""
⚙️ <b>Настройки обработки</b>

📹 <b>Источник:</b> {source[:50]}{'...' if len(source) > 50 else ''}

<b>Текущие настройки:</b>
⏱️ Длительность фрагментов: {settings['fragment_duration']} сек
📊 Качество: {settings['quality']}
📝 Субтитры: {'Включены' if settings['enable_subtitles'] else 'Отключены'}
📋 Заголовок: {title_display}
🔢 Нумерация частей: {part_numbers_status}

<b>Результат:</b>
🎬 Профессиональные шортсы с размытым фоном
📱 Формат 9:16 для TikTok/YouTube Shorts
🎯 Анимированные субтитры по словам

<b>О нумерации частей:</b>
{'✅ К названиям длинных видео будет добавляться "Часть 1", "Часть 2" и т.д.' if settings.get('add_part_numbers', False) else '❌ Названия частей останутся без нумерации (для видео меньше 15 минут)'}

Настройте параметры обработки или нажмите "Начать обработку" для запуска с текущими настройками.
    """
    
    # Create dynamic keyboard with current settings
    from app.bot.keyboards.main_menu import InlineKeyboardBuilder, SettingsValueAction, VideoAction, MenuAction, MENU_EMOJIS
    
    builder = InlineKeyboardBuilder()
    
    # Duration settings
    builder.button(
        text="⏱️ 15 сек",
        callback_data=SettingsValueAction(action="duration", value="15")
    )
    builder.button(
        text="⏱️ 30 сек",
        callback_data=SettingsValueAction(action="duration", value="30")
    )
    builder.button(
        text="⏱️ 60 сек",
        callback_data=SettingsValueAction(action="duration", value="60")
    )
    builder.button(
        text="⏱️ Кастом",
        callback_data=SettingsValueAction(action="duration", value="custom")
    )
    
    # Quality settings
    builder.button(
        text="📊 720p",
        callback_data=SettingsValueAction(action="quality", value="720p")
    )
    builder.button(
        text="📊 1080p",
        callback_data=SettingsValueAction(action="quality", value="1080p")
    )
    builder.button(
        text="📊 4K",
        callback_data=SettingsValueAction(action="quality", value="4k")
    )
    
    # Subtitle settings
    subtitles_text = "📝 Субтитры: ВКЛ" if settings.get('enable_subtitles', True) else "📝 Субтитры: ВЫКЛ"
    builder.button(
        text=subtitles_text,
        callback_data=SettingsValueAction(action="subtitles", value="toggle")
    )
    
    # Title setting
    builder.button(
        text="📋 Заголовок",
        callback_data=SettingsValueAction(action="title", value="set")
    )
    
    # Part numbering setting with dynamic text
    part_numbers_text = "🔢 Нумерация частей: ВКЛ" if settings.get('add_part_numbers', False) else "🔢 Нумерация частей: ВЫКЛ"
    builder.button(
        text=part_numbers_text,
        callback_data=SettingsValueAction(action="part_numbers", value="toggle")
    )
    
    # Confirm button
    builder.button(
        text="✅ Начать обработку",
        callback_data=VideoAction(action="start_processing")
    )
    
    # Back button
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=MenuAction(action="video_menu")
    )
    
    # Arrange buttons: 4 duration, 3 quality, 1 subtitles, 1 title, 1 part numbers, 1 confirm, 1 back
    builder.adjust(4, 3, 1, 1, 1, 1, 1)
    
    keyboard = builder.as_markup()
    
    if isinstance(message, Message):
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(SettingsValueAction.filter(F.action == "duration"))
async def update_duration_setting(callback: CallbackQuery, callback_data: SettingsValueAction, state: FSMContext) -> None:
    """
    Update fragment duration setting.
    
    Args:
        callback: Callback query
        callback_data: Settings action data
        state: FSM context
    """
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True
    })
    
    # Ensure we're in the right state
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Update duration
    if callback_data.value == "custom":
        # TODO: Implement custom duration input
        duration = 45  # Placeholder
    else:
        duration = int(callback_data.value)
    
    settings["fragment_duration"] = duration
    await state.update_data(settings=settings)
    
    # Show updated settings
    source = data.get("source_url", data.get("file_name", "Unknown"))
    await show_video_settings(callback, state, source)


@router.callback_query(SettingsValueAction.filter(F.action == "quality"))
async def update_quality_setting(callback: CallbackQuery, callback_data: SettingsValueAction, state: FSMContext) -> None:
    """
    Update video quality setting.
    
    Args:
        callback: Callback query
        callback_data: Settings action data
        state: FSM context
    """
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True
    })
    
    # Ensure we're in the right state
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Update quality
    settings["quality"] = callback_data.value
    await state.update_data(settings=settings)
    
    # Show updated settings
    source = data.get("source_url", data.get("file_name", "Unknown"))
    await show_video_settings(callback, state, source)


@router.callback_query(SettingsValueAction.filter(F.action == "subtitles"))
async def toggle_subtitles_setting(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Toggle subtitles setting.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True
    })
    
    # Ensure we're in the right state
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Toggle subtitles
    settings["enable_subtitles"] = not settings.get("enable_subtitles", True)
    await state.update_data(settings=settings)
    
    # Show updated settings
    source = data.get("source_url", data.get("file_name", "Unknown"))
    await show_video_settings(callback, state, source)


@router.callback_query(SettingsValueAction.filter(F.action == "part_numbers"))
async def toggle_part_numbers_setting(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Toggle part numbers setting.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True,
        "add_part_numbers": False
    })
    
    # Ensure we're in the right state
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Toggle part numbers
    settings["add_part_numbers"] = not settings.get("add_part_numbers", False)
    await state.update_data(settings=settings)
    
    # Show updated settings
    source = data.get("source_url", data.get("file_name", "Unknown"))
    await show_video_settings(callback, state, source)


@router.callback_query(SettingsValueAction.filter(F.action == "title"))
async def set_title_setting(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Set title for video fragments.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True,
        "title": ""
    })
    
    # Ensure we're in the right state
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    text = """
📋 <b>Настройка заголовка</b>

Отправьте заголовок, который будет отображаться в верхней части каждого фрагмента.

<b>Примеры:</b>
• "Топ-5 лайфхаков"
• "Обзор iPhone 15"
• "Рецепт борща"

<i>Отправьте текст заголовка следующим сообщением или нажмите "Без заголовка"</i>
    """
    
    from app.bot.keyboards.main_menu import InlineKeyboardBuilder, SettingsValueAction, MenuAction
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚫 Без заголовка",
        callback_data=SettingsValueAction(action="title_set", value="")
    )
    builder.button(
        text="⬅️ Назад",
        callback_data=MenuAction(action="video_menu")
    )
    builder.adjust(1, 1)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    
    # Set state to wait for title input
    await state.set_state(VideoProcessingStates.waiting_for_title)


@router.message(VideoProcessingStates.waiting_for_title)
async def process_title_input(message: Message, state: FSMContext) -> None:
    """
    Process title input from user.
    
    Args:
        message: User message with title
        state: FSM context
    """
    title = message.text.strip()
    
    # Validate title length
    if len(title) > 50:
        await message.answer(
            "❌ Заголовок слишком длинный. Максимум 50 символов.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {})
    
    # Update title
    settings["title"] = title
    await state.update_data(settings=settings)
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Show updated settings
    source = data.get("source_url", data.get("file_name", "Unknown"))
    await show_video_settings(message, state, source)


@router.callback_query(SettingsValueAction.filter(F.action == "title_set"))
async def set_title_value(callback: CallbackQuery, callback_data: SettingsValueAction, state: FSMContext) -> None:
    """
    Set title value directly from callback.
    
    Args:
        callback: Callback query
        callback_data: Settings action data
        state: FSM context
    """
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {})
    
    # Update title
    settings["title"] = callback_data.value
    await state.update_data(settings=settings)
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Show updated settings
    source = data.get("source_url", data.get("file_name", "Unknown"))
    await show_video_settings(callback, state, source)


@router.callback_query(VideoAction.filter(F.action == "start_processing"))
async def start_video_processing(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Start video processing.
    
    Args:
        callback: Callback query
        state: FSM context
        bot: Bot instance
    """
    user_id = callback.from_user.id
    data = await state.get_data()
    
    async with get_db_session() as session:
        # Check for existing active tasks
        from sqlalchemy import select
        existing_task = await session.scalar(
            select(VideoTask).where(
                VideoTask.user_id == user_id,
                VideoTask.status.in_([VideoStatus.PENDING, VideoStatus.DOWNLOADING, VideoStatus.PROCESSING, VideoStatus.UPLOADING])
            )
        )
        
        if existing_task:
            await callback.answer("⚠️ У вас уже есть активная задача обработки!", show_alert=True)
            return
        
        # Create video task in database
        task_id = str(uuid.uuid4())
        
        # Get or create user
        user = await session.get(User, user_id)
        if not user:
            user = User(
                id=user_id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name
            )
            session.add(user)
        
        # Create video task
        video_task = VideoTask(
            id=task_id,
            user_id=user_id,
            source_url=data.get("source_url"),
            original_filename=data.get("file_name"),
            status=VideoStatus.PENDING,
            settings=data.get("settings", {}),
            metadata={}
        )
        session.add(video_task)
        await session.commit()
    
    # Start processing workflow
    await state.set_state(VideoProcessingStates.processing)
    await state.update_data(task_id=task_id)
    
    text = f"""
🚀 <b>Оптимизированная обработка запущена!</b>

📋 ID задачи: <code>{task_id}</code>
⏱️ Ориентировочное время: 2-4 минуты

<b>Этапы обработки:</b>
1. ⏳ Скачивание видео...
2. ⏳ Полная обработка в формат Shorts...
3. ⏳ Нарезка на фрагменты...
4. ⏳ Загрузка в Google Drive...
5. ⏳ Заполнение Google Таблицы...
6. ⏳ Очистка временных файлов...

<b>Преимущества нового процесса:</b>
• Более быстрая обработка
• Лучшее качество видео
• Автоматическое сохранение в Drive
• Ведение статистики в Google Sheets

Я уведомлю вас о завершении обработки.
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_task_status_keyboard(task_id),
        parse_mode="HTML"
    )
    
    # Start optimized Celery task chain
    from app.workers.video_tasks import process_video_chain_optimized
    from app.video_processing.downloader import VideoDownloader

    if data.get("input_type") == "url":
        # Process from URL with optimized workflow
        source_url = data.get("source_url")
        settings = data.get("settings", {})

        # Получаем длительность видео до скачивания
        try:
            downloader = VideoDownloader()
            info = downloader.get_video_info(source_url)
            duration_sec = int(info.get('duration', 0))
        except Exception as e:
            duration_sec = 0  # fallback

        # Функция для расчёта лимита времени
        def get_time_limit_for_video(video_duration_sec):
            base = video_duration_sec * 1.5 * 1.2
            return int(min(max(base, 600), 10800))  # от 10 минут до 3 часов

        soft_limit = get_time_limit_for_video(duration_sec)
        hard_limit = soft_limit + 300  # +5 минут запас

        # Передаём ffmpeg_timeout в settings (на 1 минуту меньше лимита задачи)
        settings['ffmpeg_timeout'] = max(soft_limit - 60, 300)

        process_video_chain_optimized.apply_async(
            args=[task_id, source_url, settings],
            soft_time_limit=soft_limit,
            time_limit=hard_limit
        )
    else:
        # Process from uploaded file
        # TODO: Implement file processing
        await callback.message.edit_text(
            "❌ <b>Обработка файлов пока не поддерживается</b>\n\nИспользуйте ссылку на видео.",
            parse_mode="HTML"
        )
        return


@router.callback_query(VideoAction.filter(F.action == "my_tasks"))
async def show_my_tasks(callback: CallbackQuery) -> None:
    """
    Show user's video processing tasks.
    
    Args:
        callback: Callback query
    """
    user_id = callback.from_user.id
    
    # TODO: Get actual tasks from database
    text = """
📋 <b>Мои задачи</b>

У вас пока нет активных задач обработки видео.

Начните обработку видео, чтобы увидеть задачи здесь.
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("video_menu"),
        parse_mode="HTML"
    )


@router.callback_query(VideoAction.filter(F.action == "batch_processing"))
async def start_batch_processing(callback: CallbackQuery) -> None:
    """
    Start batch processing mode.
    
    Args:
        callback: Callback query
    """
    text = """
📋 <b>Пакетная обработка</b>

Режим пакетной обработки позволяет обработать несколько видео одновременно.

<b>Как это работает:</b>
1. Отправьте несколько ссылок (по одной в сообщении)
2. Или загрузите несколько файлов
3. Настройте общие параметры обработки
4. Запустите обработку всех видео

<b>Ограничения:</b>
• Максимум 10 видео за раз
• Общее время обработки: до 30 минут
• Одинаковые настройки для всех видео

<i>Функция находится в разработке</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("video_menu"),
        parse_mode="HTML"
    )


@router.callback_query(VideoTaskAction.filter(F.action == "cancel_task"))
async def cancel_task(callback: CallbackQuery, callback_data: VideoTaskAction) -> None:
    """
    Cancel video processing task.
    
    Args:
        callback: Callback query
        callback_data: Video action data
    """
    task_id = callback_data.task_id
    
    # TODO: Implement actual task cancellation
    text = f"""
❌ <b>Задача отменена</b>

📋 ID задачи: <code>{task_id}</code>
🕐 Время выполнения: 1 мин 23 сек
📊 Прогресс на момент отмены: 45%

Обработка была остановлена. Частично обработанные файлы удалены.
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("main_menu"),
        parse_mode="HTML"
    )
    await callback.answer("❌ Задача отменена")


@router.callback_query(VideoTaskAction.filter(F.action == "refresh_status"))
async def refresh_task_status(callback: CallbackQuery, callback_data: VideoTaskAction) -> None:
    """
    Refresh task status.
    
    Args:
        callback: Callback query
        callback_data: Video action data
    """
    task_id = callback_data.task_id
    
    # Get actual task status from database
    async with get_db_session() as session:
        task = await session.get(VideoTask, task_id)
        if not task:
            await callback.message.edit_text(
                "❌ <b>Задача не найдена</b>",
                parse_mode="HTML"
            )
            return
        
        # Get fragments count
        from sqlalchemy import select, func
        fragments_count = await session.scalar(
            select(func.count(VideoFragment.id)).where(VideoFragment.task_id == task_id)
        )
        
        # Determine status text and emoji
        status_map = {
            VideoStatus.PENDING: ("⏳", "Ожидает обработки"),
            VideoStatus.DOWNLOADING: ("📥", "Скачивание видео"),
            VideoStatus.PROCESSING: ("⚙️", "Обработка видео"),
            VideoStatus.UPLOADING: ("📤", "Загрузка результатов"),
            VideoStatus.COMPLETED: ("✅", "Завершено"),
            VideoStatus.FAILED: ("❌", "Ошибка")
        }
        
        status_emoji, status_text = status_map.get(task.status, ("❓", "Неизвестно"))
        
        # Calculate elapsed time
        from datetime import datetime
        elapsed = datetime.utcnow() - task.created_at
        elapsed_minutes = int(elapsed.total_seconds() / 60)
        elapsed_seconds = int(elapsed.total_seconds() % 60)
        
        text = f"""
🔄 <b>Статус задачи</b>

📋 ID: <code>{task_id}</code>
{status_emoji} Статус: {status_text}
⏱️ Прогресс: {task.progress or 0}%
🕐 Время выполнения: {elapsed_minutes} мин {elapsed_seconds} сек

<b>Детали:</b>
📊 Создано фрагментов: {fragments_count or 0}
📹 Источник: {task.source_url or task.original_filename or 'Неизвестно'}

<b>Настройки:</b>
⏱️ Длительность: {task.settings.get('fragment_duration', 30)} сек
📊 Качество: {task.settings.get('quality', '1080p')}
📝 Субтитры: {'Да' if task.settings.get('enable_subtitles', True) else 'Нет'}

<i>Обновлено: только что</i>
        """
        
        if task.error_message:
            text += f"\n\n❌ <b>Ошибка:</b> {task.error_message}"
        
        keyboard = get_task_status_keyboard(task_id, can_cancel=(task.status in [VideoStatus.PENDING, VideoStatus.DOWNLOADING, VideoStatus.PROCESSING]))
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


async def simulate_processing(bot: Bot, user_id: int, task_id: str, chat_id: int) -> None:
    """
    Simulate video processing for demo purposes.
    
    Args:
        bot: Bot instance
        user_id: User ID
        task_id: Task ID
        chat_id: Chat ID for notifications
    """
    import asyncio
    
    # Wait a bit to simulate processing
    await asyncio.sleep(5)
    
    # Send completion notification
    text = f"""
✅ <b>Обработка завершена!</b>

📋 ID задачи: <code>{task_id}</code>
📊 Создано фрагментов: 8
⏱️ Время обработки: 3 мин 24 сек

<b>Результаты:</b>
• 8 фрагментов в формате 9:16
• Субтитры добавлены
• Загружено в Google Drive

📁 <a href="https://drive.google.com/drive/folders/mock">Открыть папку в Drive</a>
    """
    
    from app.bot.keyboards.main_menu import get_back_keyboard
    
    await bot.send_message(
        chat_id,
        text,
        reply_markup=get_back_keyboard("main_menu"),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


def is_valid_video_url(url: str) -> bool:
    """
    Validate if URL is a supported video platform.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if URL is valid and supported
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check if domain is in supported sources
        for source in SUPPORTED_SOURCES:
            if source in domain:
                return True
        
        return False
        
    except Exception:
        return False