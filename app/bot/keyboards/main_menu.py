"""
Main menu keyboards for the Video Bot.
"""
from aiogram.types import (
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.config.constants import MENU_EMOJIS, UserRole


class MenuAction(CallbackData, prefix="menu"):
    """Callback data for menu actions."""
    action: str


class VideoAction(CallbackData, prefix="video"):
    """Callback data for video processing actions."""
    action: str


class VideoTaskAction(CallbackData, prefix="vtask"):
    """Callback data for video task actions."""
    action: str
    task_id: str


class SettingsAction(CallbackData, prefix="settings"):
    """Callback data for settings actions."""
    action: str


class SettingsValueAction(CallbackData, prefix="setval"):
    """Callback data for settings with values."""
    action: str
    value: str


class StyleAction(CallbackData, prefix="style"):
    """Callback data for style actions."""
    action: str
    text_type: str = ""  # title or subtitle
    style_type: str = ""  # color, size, etc.
    value: str = ""


def get_main_menu_keyboard(user_role: UserRole = UserRole.USER) -> InlineKeyboardMarkup:
    """
    Get main menu inline keyboard.
    
    Args:
        user_role: User's role to determine available options
        
    Returns:
        InlineKeyboardMarkup: Main menu keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Main video processing button
    builder.button(
        text=f"{MENU_EMOJIS['video']} Обработать видео",
        callback_data=MenuAction(action="video_menu")
    )
    
    # Settings button
    builder.button(
        text=f"{MENU_EMOJIS['settings']} Настройки",
        callback_data=MenuAction(action="settings_menu")
    )
    
    # Statistics button
    builder.button(
        text=f"{MENU_EMOJIS['stats']} Моя статистика",
        callback_data=MenuAction(action="stats_menu")
    )
    
    # Help button
    builder.button(
        text=f"{MENU_EMOJIS['help']} Помощь",
        callback_data=MenuAction(action="help")
    )
    
    # Admin panel for admins and moderators
    if user_role in [UserRole.ADMIN, UserRole.MODERATOR]:
        builder.button(
            text=f"{MENU_EMOJIS['admin']} Админ-панель",
            callback_data=MenuAction(action="admin_menu")
        )
    
    # Arrange buttons in a 2x2 grid
    builder.adjust(2, 2)
    
    # Add admin button separately if needed
    if user_role in [UserRole.ADMIN, UserRole.MODERATOR]:
        builder.adjust(2, 2, 1)
    
    return builder.as_markup()


def get_video_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Get video processing menu keyboard.
    
    Returns:
        InlineKeyboardMarkup: Video menu keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Input method buttons
    builder.button(
        text=f"{MENU_EMOJIS['link']} Вставить ссылку",
        callback_data=VideoAction(action="input_url")
    )
    
    builder.button(
        text=f"{MENU_EMOJIS['file']} Загрузить файл",
        callback_data=VideoAction(action="upload_file")
    )
    
    builder.button(
        text=f"{MENU_EMOJIS['batch']} Пакетная обработка",
        callback_data=VideoAction(action="batch_processing")
    )
    
    builder.button(
        text=f"{MENU_EMOJIS['tasks']} Мои задачи",
        callback_data=VideoAction(action="my_tasks")
    )
    
    # Back button
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=MenuAction(action="main_menu")
    )
    
    # Arrange in 2x2 + 1 layout
    builder.adjust(2, 2, 1)
    
    return builder.as_markup()


def get_video_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Get video processing settings keyboard.
    
    Returns:
        InlineKeyboardMarkup: Video settings keyboard
    """
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
    builder.button(
        text="📝 Субтитры: ВКЛ",
        callback_data=SettingsValueAction(action="subtitles", value="toggle")
    )
    
    # Title setting
    builder.button(
        text="📋 Заголовок",
        callback_data=SettingsValueAction(action="title", value="set")
    )
    
    # Part numbering setting
    builder.button(
        text="🔢 Нумерация частей: ВЫКЛ",
        callback_data=SettingsValueAction(action="part_numbers", value="toggle")
    )
    
    # Proxy settings button - NEW
    builder.button(
        text="🌐 Прокси для скачивания",
        callback_data=SettingsAction(action="proxy_settings")
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
    
    return builder.as_markup()


def get_settings_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Get settings menu keyboard.
    
    Returns:
        InlineKeyboardMarkup: Settings menu keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Font settings
    builder.button(
        text="🔤 Выбор шрифтов",
        callback_data=SettingsAction(action="font_settings")
    )
    
    # Style settings - NEW!
    builder.button(
        text="🎨 Стили текста",
        callback_data=SettingsAction(action="style_settings")
    )
    
    # Video settings
    builder.button(
        text="🎬 Настройки видео",
        callback_data=SettingsAction(action="video_settings")
    )
    
    # Storage settings
    builder.button(
        text="💾 Настройки сохранения",
        callback_data=SettingsAction(action="storage_settings")
    )
    
    # Notification settings
    builder.button(
        text="🔔 Уведомления",
        callback_data=SettingsAction(action="notifications")
    )
    
    # Proxy settings - NEW
    builder.button(
        text="🌐 Прокси для скачивания",
        callback_data=SettingsAction(action="proxy_settings")
    )
    # Profile settings
    builder.button(
        text="👤 Профиль",
        callback_data=SettingsAction(action="profile")
    )
    
    # Back button
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=MenuAction(action="main_menu")
    )
    
    # Arrange in 2x3 + 1 layout
    builder.adjust(2, 2, 2, 1)
    
    return builder.as_markup()


def get_back_keyboard(callback_action: str = "main_menu") -> InlineKeyboardMarkup:
    """
    Get simple back button keyboard.
    
    Args:
        callback_action: Action to call when back button is pressed
        
    Returns:
        InlineKeyboardMarkup: Back button keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=MenuAction(action=callback_action)
    )
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Get cancel button keyboard.
    
    Returns:
        InlineKeyboardMarkup: Cancel button keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="❌ Отменить",
        callback_data=MenuAction(action="cancel")
    )
    
    return builder.as_markup()


def get_task_status_keyboard(task_id: str, can_cancel: bool = True) -> InlineKeyboardMarkup:
    """
    Get task status keyboard with available actions.
    
    Args:
        task_id: Task identifier
        can_cancel: Whether the cancel button should be shown
        
    Returns:
        InlineKeyboardMarkup: Task status keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Refresh status button
    builder.button(
        text="🔄 Обновить статус",
        callback_data=VideoTaskAction(action="refresh_status", task_id=task_id)
    )
    
    # Cancel button if task can be canceled
    if can_cancel:
        builder.button(
            text="❌ Отменить задачу",
            callback_data=VideoTaskAction(action="cancel_task", task_id=task_id)
        )
    
    # Back to tasks list
    builder.button(
        text=f"{MENU_EMOJIS['back']} К списку задач",
        callback_data=VideoAction(action="my_tasks")
    )
    
    # Arrange buttons
    if can_cancel:
        builder.adjust(1, 1, 1)  # One button per row
    else:
        builder.adjust(1, 1)
    
    return builder.as_markup()


def get_confirmation_keyboard(confirm_action: str, cancel_action: str = "cancel") -> InlineKeyboardMarkup:
    """
    Get confirmation keyboard with Yes/No buttons.
    
    Args:
        confirm_action: Action to call when confirmed
        cancel_action: Action to call when canceled
        
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="✅ Да",
        callback_data=MenuAction(action=confirm_action)
    )
    
    builder.button(
        text="❌ Нет",
        callback_data=MenuAction(action=cancel_action)
    )
    
    # Two buttons in one row
    builder.adjust(2)
    
    return builder.as_markup()


# Reply keyboard for common commands
def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Get main reply keyboard with common commands.
    
    Returns:
        ReplyKeyboardMarkup: Main reply keyboard
    """
    builder = ReplyKeyboardBuilder()
    
    # Main menu button
    builder.button(text="🏠 Главное меню")
    
    # Quick video processing
    builder.button(text="🎬 Быстрая обработка")
    
    # My tasks
    builder.button(text="📋 Мои задачи")
    
    # Help
    builder.button(text="❓ Помощь")
    
    # Arrange in 2x2 layout
    builder.adjust(2, 2)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие..."
    )


def get_style_settings_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Get style settings menu keyboard.
    
    Returns:
        InlineKeyboardMarkup: Style settings menu keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Title style settings
    builder.button(
        text="📋 Настройки заголовка",
        callback_data=StyleAction(action="text_settings", text_type="title")
    )
    
    # Subtitle style settings
    builder.button(
        text="📝 Настройки субтитров",
        callback_data=StyleAction(action="text_settings", text_type="subtitle")
    )
    
    # Preview button
    builder.button(
        text="👁️ Предпросмотр стилей",
        callback_data=StyleAction(action="preview_styles")
    )
    
    # Reset to defaults
    builder.button(
        text="🔄 Сбросить к умолчанию",
        callback_data=StyleAction(action="reset_styles")
    )
    
    # Back button
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=MenuAction(action="settings_menu")
    )
    
    # Arrange buttons
    builder.adjust(2, 1, 1, 1)
    
    return builder.as_markup()


def get_text_settings_keyboard(text_type: str) -> InlineKeyboardMarkup:
    """
    Get text settings keyboard for title or subtitle.
    
    Args:
        text_type: 'title' or 'subtitle'
        
    Returns:
        InlineKeyboardMarkup: Text settings keyboard
    """
    builder = InlineKeyboardBuilder()
    
    text_label = "заголовка" if text_type == "title" else "субтитров"
    
    # Color settings
    builder.button(
        text=f"🎨 Цвет {text_label}",
        callback_data=StyleAction(action="color_settings", text_type=text_type)
    )
    
    # Size settings
    builder.button(
        text=f"📏 Размер {text_label}",
        callback_data=StyleAction(action="size_settings", text_type=text_type)
    )
    
    # Font settings (link to existing font system)
    builder.button(
        text=f"🔤 Шрифт {text_label}",
        callback_data=SettingsAction(action="font_settings")
    )
    
    # Back button
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=StyleAction(action="style_menu")
    )
    
    # Arrange buttons
    builder.adjust(1, 1, 1, 1)
    
    return builder.as_markup()


def get_color_settings_keyboard(text_type: str) -> InlineKeyboardMarkup:
    """
    Get color settings keyboard.
    
    Args:
        text_type: 'title' or 'subtitle'
        
    Returns:
        InlineKeyboardMarkup: Color settings keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Color options with emojis
    colors = [
        ("⚪ Белый", "white"),
        ("🔴 Красный", "red"),
        ("🔵 Синий", "blue"),
        ("🟡 Желтый", "yellow"),
        ("🟢 Зеленый", "green"),
        ("🟠 Оранжевый", "orange"),
        ("🟣 Фиолетовый", "purple"),
        ("🌸 Розовый", "pink"),
    ]
    
    for color_name, color_value in colors:
        builder.button(
            text=color_name,
            callback_data=StyleAction(
                action="set_color", 
                text_type=text_type, 
                style_type="color", 
                value=color_value
            )
        )
    
    # Back button
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=StyleAction(action="text_settings", text_type=text_type)
    )
    
    # Arrange in 2x4 + 1 layout
    builder.adjust(2, 2, 2, 2, 1)
    
    return builder.as_markup()


def get_size_settings_keyboard(text_type: str) -> InlineKeyboardMarkup:
    """
    Get size settings keyboard.
    
    Args:
        text_type: 'title' or 'subtitle'
        
    Returns:
        InlineKeyboardMarkup: Size settings keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Size options
    sizes = [
        ("📏 Маленький", "small"),
        ("📐 Средний", "medium"),
        ("📊 Большой", "large"),
        ("📈 Очень большой", "extra_large"),
    ]
    
    for size_name, size_value in sizes:
        builder.button(
            text=size_name,
            callback_data=StyleAction(
                action="set_size", 
                text_type=text_type, 
                style_type="size", 
                value=size_value
            )
        )
    
    # Back button
    builder.button(
        text=f"{MENU_EMOJIS['back']} Назад",
        callback_data=StyleAction(action="text_settings", text_type=text_type)
    )
    
    # Arrange in 2x2 + 1 layout
    builder.adjust(2, 2, 1)
    
    return builder.as_markup() 