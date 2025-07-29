"""
Video processing handlers for the Telegram bot.
"""
import os
import uuid
import re
import logging
from typing import Union
from urllib.parse import urlparse

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards.main_menu import (
    VideoAction,
    SettingsValueAction,
    get_cancel_keyboard,
    get_back_keyboard,
    MenuAction,
    MENU_EMOJIS
)
from app.config.constants import SUPPORTED_SOURCES, ERROR_MESSAGES, SUCCESS_MESSAGES

logger = logging.getLogger(__name__)
router = Router()


class VideoProcessingStates(StatesGroup):
    """States for video processing workflow."""
    waiting_for_url = State()
    waiting_for_file = State()
    configuring_settings = State()
    processing = State()
    waiting_for_title = State()
    waiting_for_custom_duration = State()


def is_valid_video_url(url: str) -> bool:
    """
    Validate if URL is a supported video URL.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if URL is valid
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check if domain is supported
        domain = parsed.netloc.lower()
        for source in SUPPORTED_SOURCES:
            if source in domain:
                return True
        
        return False
    except Exception:
        return False


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
• Максимальный размер: 50MB
• Максимальная длительность: 3 часа

<i>Для больших файлов используйте ссылку на видео</i>
<i>Просто отправьте файл следующим сообщением</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(VideoProcessingStates.waiting_for_file, ~(F.video | F.document))
async def process_invalid_file_input(message: Message, state: FSMContext) -> None:
    """
    Handle invalid input when waiting for file upload.
    
    Args:
        message: User message
        state: FSM context
    """
    await message.answer(
        "❌ <b>Неподдерживаемый тип сообщения</b>\n\n"
        "Пожалуйста, отправьте видео файл или документ.\n\n"
        "<i>Поддерживаемые форматы: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V</i>",
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
        
        # Check if document is a video file
        if file_name:
            valid_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v')
            if not file_name.lower().endswith(valid_extensions):
                await message.answer(
                    "❌ <b>Неподдерживаемый формат файла</b>\n\n"
                    f"Файл: {file_name}\n\n"
                    "Поддерживаемые форматы:\n"
                    "• MP4, AVI, MKV, MOV\n"
                    "• WMV, FLV, WebM, M4V",
                    reply_markup=get_cancel_keyboard(),
                    parse_mode="HTML"
                )
                return
    else:
        await message.answer(
            "❌ Неподдерживаемый тип файла",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Check file size (Telegram limit is usually 50MB for bots)
    if file_info.file_size and file_info.file_size > 50 * 1024 * 1024:
        await message.answer(
            "❌ <b>Файл слишком большой</b>\n\n"
            f"Размер файла: {file_info.file_size / (1024*1024):.1f} MB\n"
            "Максимальный размер: 50 MB\n\n"
            "Пожалуйста, сожмите видео или используйте ссылку на видео.",
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
        "title": ""
    })
    
    title_text = settings.get('title', '')
    title_display = f'"{title_text}"' if title_text else 'Не задан'
    
    text = f"""
⚙️ <b>Настройки обработки</b>

📹 <b>Источник:</b> {source[:50]}{'...' if len(source) > 50 else ''}

<b>Текущие настройки:</b>
⏱️ Длительность фрагментов: {settings['fragment_duration']} сек
📊 Качество: {settings['quality']}
📝 Субтитры: {'Включены' if settings['enable_subtitles'] else 'Отключены'}
📋 Заголовок: {title_display}

<b>Результат:</b>
🎬 Профессиональные шортсы с размытым фоном
📱 Формат 9:16 для TikTok/YouTube Shorts
🎯 Анимированные субтитры по словам

Настройте параметры обработки или нажмите "Начать обработку" для запуска с текущими настройками.
    """
    
    # Create dynamic keyboard with current settings
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
    
    # Arrange buttons: 4 duration, 3 quality, 1 subtitles, 1 title, 1 confirm, 1 back
    builder.adjust(4, 3, 1, 1, 1, 1)
    
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
        # Start custom duration input
        text = """
⏱️ <b>Кастомная длительность фрагментов</b>

Введите желаемую длительность фрагментов в секундах.

<b>Допустимые значения:</b>
• Минимум: 5 секунд
• Максимум: 300 секунд (5 минут)

<b>Примеры:</b>
• 25 - для фрагментов по 25 секунд
• 45 - для фрагментов по 45 секунд
• 90 - для фрагментов по 1.5 минуты

<i>Отправьте число следующим сообщением</i>
        """
        
        builder = InlineKeyboardBuilder()
        builder.button(
            text="⬅️ Назад",
            callback_data=MenuAction(action="video_menu")
        )
        builder.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        # Set state to wait for custom duration input
        await state.set_state(VideoProcessingStates.waiting_for_custom_duration)
        return
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


@router.callback_query(SettingsValueAction.filter(F.action == "title"))
async def set_title_setting(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Set title for video fragments.
    
    Args:
        callback: Callback query
        state: FSM context
    """
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


@router.message(VideoProcessingStates.waiting_for_custom_duration)
async def process_custom_duration_input(message: Message, state: FSMContext) -> None:
    """
    Process custom duration input from user.
    
    Args:
        message: User message with duration
        state: FSM context
    """
    try:
        # Parse duration
        duration_text = message.text.strip()
        duration = int(duration_text)
        
        # Validate duration
        if duration < 5:
            await message.answer(
                "❌ Слишком короткая длительность. Минимум 5 секунд.",
                reply_markup=get_cancel_keyboard()
            )
            return
        elif duration > 300:
            await message.answer(
                "❌ Слишком длинная длительность. Максимум 300 секунд (5 минут).",
                reply_markup=get_cancel_keyboard()
            )
            return
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите число в секундах (например: 45).",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Get current state data
    data = await state.get_data()
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True,
        "title": ""
    })
    
    # Update duration
    settings["fragment_duration"] = duration
    await state.update_data(settings=settings)
    await state.set_state(VideoProcessingStates.configuring_settings)
    
    # Show updated settings
    source = data.get("source_url", data.get("file_name", "Unknown"))
    await show_video_settings(message, state, source)


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
    settings = data.get("settings", {
        "fragment_duration": 30,
        "quality": "1080p",
        "enable_subtitles": True,
        "title": ""
    })
    
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
    
    try:
        task_id = str(uuid.uuid4())
        
        # Start processing workflow
        await state.set_state(VideoProcessingStates.processing)
        await state.update_data(task_id=task_id)
        
        text = f"""
🚀 <b>Обработка запущена!</b>

📋 ID задачи: <code>{task_id}</code>
⏱️ Ориентировочное время: 2-4 минуты

<b>Этапы обработки:</b>
1. ⏳ Скачивание видео...
2. ⏳ Обработка в формат Shorts...
3. ⏳ Нарезка на фрагменты...
4. ⏳ Добавление субтитров...
5. ⏳ Финальная обработка...

Я уведомлю вас о завершении обработки.
        """
        
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"{MENU_EMOJIS['back']} Главное меню",
            callback_data=MenuAction(action="main_menu")
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        # Start Celery task
        from app.workers.video_tasks import process_video_chain_optimized
        
        if data.get("input_type") == "url":
            # Process from URL
            settings = data.get("settings", {})
            source_url = data.get("source_url")
            
            # Set timeout limits
            soft_limit = 28800  # 8 hours
            hard_limit = 28800  # 8 hours
            
            settings['ffmpeg_timeout'] = 28800
            
            process_video_chain_optimized.apply_async(
                args=[task_id, source_url, settings],
                soft_time_limit=soft_limit,
                time_limit=hard_limit
            )
        else:
            # Process from uploaded file
            settings = data.get("settings", {})
            file_id = data.get("file_id")
            file_name = data.get("file_name")
            file_size = data.get("file_size")
            
            if not all([file_id, file_name, file_size]):
                await callback.message.edit_text(
                    "❌ <b>Ошибка</b>\n\nДанные файла не найдены. Попробуйте загрузить файл заново.",
                    parse_mode="HTML"
                )
                return
            
            # Start file processing task
            from app.workers.video_tasks import process_uploaded_file_chain
            
            soft_limit = 28800
            hard_limit = 28800
            settings['ffmpeg_timeout'] = 28800
            
            process_uploaded_file_chain.apply_async(
                args=[task_id, file_id, file_name, file_size, settings],
                soft_time_limit=soft_limit,
                time_limit=hard_limit
            )
        
        # Clear state after starting processing
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error starting video processing: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка запуска обработки</b>\n\n"
            "Произошла ошибка при запуске обработки видео. Попробуйте еще раз.",
            parse_mode="HTML"
        )