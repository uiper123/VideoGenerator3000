"""
Settings handlers for the Telegram bot.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.main_menu import (
    SettingsAction,
    StyleAction,
    get_back_keyboard,
    get_confirmation_keyboard,
    get_style_settings_menu_keyboard,
    get_text_settings_keyboard,
    get_color_settings_keyboard,
    get_size_settings_keyboard
)
from app.config.constants import MENU_EMOJIS
from app.database.connection import get_db_session
from app.database.models import User
from app.services.user_settings import UserSettingsService

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(SettingsAction.filter(F.action == "video_settings"))
async def show_video_settings(callback: CallbackQuery) -> None:
    """
    Show video processing settings.
    
    Args:
        callback: Callback query
    """
    text = f"""
🎬 <b>Настройки видео</b>

<b>Параметры по умолчанию:</b>
⏱️ Длительность фрагментов: 30 сек
📊 Качество: 1080p
📝 Субтитры: Включены
🎨 Формат: 9:16 (Shorts)

<b>Дополнительные настройки:</b>
🔊 Громкость: Авто-нормализация
🎭 Переходы: Плавные
📐 Обрезка: Умная (по содержимому)
🌈 Фильтры: Автоулучшение

<i>Эти настройки применяются ко всем новым видео</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("settings_menu"),
        parse_mode="HTML"
    )


@router.callback_query(SettingsAction.filter(F.action == "storage_settings"))
async def show_storage_settings(callback: CallbackQuery) -> None:
    """
    Show storage settings.
    
    Args:
        callback: Callback query
    """
    text = f"""
💾 <b>Настройки сохранения</b>

<b>Google Drive:</b>
📁 Папка: /VideoBot/Processed
🔗 Статус: Не подключен
📋 Формат имен: video_YYYYMMDD_HHMMSS

<b>Локальное сохранение:</b>
💿 Статус: Отключено
📁 Путь: -

<b>Автоочистка:</b>
🗑️ Удалять через: 30 дней
📊 Сохранять статистику: Да

<i>Настройте подключение к Google Drive для автоматического сохранения</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("settings_menu"),
        parse_mode="HTML"
    )


@router.callback_query(SettingsAction.filter(F.action == "notifications"))
async def show_notification_settings(callback: CallbackQuery) -> None:
    """
    Show notification settings.
    
    Args:
        callback: Callback query
    """
    text = f"""
🔔 <b>Настройки уведомлений</b>

<b>Уведомления о процессе:</b>
✅ Начало обработки: Включено
✅ Завершение: Включено
❌ Прогресс (каждые 25%): Отключено
✅ Ошибки: Включено

<b>Ежедневные отчеты:</b>
❌ Статистика дня: Отключено
❌ Время: 20:00

<b>Системные уведомления:</b>
✅ Обновления бота: Включено
❌ Рекламные сообщения: Отключено

<i>Настройте какие уведомления вы хотите получать</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("settings_menu"),
        parse_mode="HTML"
    )


@router.callback_query(SettingsAction.filter(F.action == "profile"))
async def show_profile_settings(callback: CallbackQuery) -> None:
    """
    Show profile settings.
    
    Args:
        callback: Callback query
    """
    user_id = callback.from_user.id
    
    async with get_db_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        text = f"""
👤 <b>Настройки профиля</b>

<b>Информация:</b>
🆔 ID: <code>{user.id}</code>
👤 Имя: {user.display_name}
📝 Username: @{user.username or 'не указан'}
🔰 Роль: {user.role.value.title()}
📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}

<b>Статистика:</b>
📹 Обработано видео: 0
⏱️ Общее время: 0 мин
💾 Данных обработано: 0 МБ

<b>Настройки приватности:</b>
🔒 Профиль: Приватный
📊 Статистика: Скрыта
        """
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("settings_menu"),
            parse_mode="HTML"
        )


@router.callback_query(SettingsAction.filter(F.action == "style_settings"))
async def show_style_settings(callback: CallbackQuery) -> None:
    """
    Show style settings menu.
    
    Args:
        callback: Callback query
    """
    text = f"""
🎨 <b>Настройки стилей текста</b>

Здесь вы можете настроить внешний вид заголовков и субтитров:

📋 <b>Заголовки:</b>
• Цвет, размер, шрифт
• Положение на экране
• Стиль оформления

📝 <b>Субтитры:</b>
• Цвет, размер, шрифт  
• Анимация появления
• Прозрачность и обводка

👁️ <b>Предпросмотр:</b>
Проверьте как будут выглядеть ваши настройки

<i>Все изменения сохраняются автоматически</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_style_settings_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(StyleAction.filter(F.action == "text_settings"))
async def show_text_settings(callback: CallbackQuery, callback_data: StyleAction) -> None:
    """
    Show text settings for title or subtitle.
    
    Args:
        callback: Callback query
        callback_data: Style action data
    """
    user_id = callback.from_user.id
    text_type = callback_data.text_type
    text_label = "заголовка" if text_type == "title" else "субтитров"
    text_emoji = "📋" if text_type == "title" else "📝"
    
    # Get current user settings
    settings_key = f"{text_type}_style"
    current_color = await UserSettingsService.get_style_setting(user_id, settings_key, 'color')
    current_size = await UserSettingsService.get_style_setting(user_id, settings_key, 'size')
    current_font = await UserSettingsService.get_style_setting(user_id, settings_key, 'font')
    
    # Get human-readable names
    color_name = UserSettingsService.get_color_name(current_color)
    size_name = UserSettingsService.get_size_name(current_size)
    
    text = f"""
{text_emoji} <b>Настройки {text_label}</b>

<b>Текущие настройки:</b>
🎨 Цвет: {color_name}
📏 Размер: {size_name}
🔤 Шрифт: {current_font}

<b>Доступные настройки:</b>
• Выберите цвет из палитры
• Установите оптимальный размер
• Подберите подходящий шрифт

<i>Изменения сохраняются автоматически</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_text_settings_keyboard(text_type),
        parse_mode="HTML"
    )


@router.callback_query(StyleAction.filter(F.action == "color_settings"))
async def show_color_settings(callback: CallbackQuery, callback_data: StyleAction) -> None:
    """
    Show color settings.
    
    Args:
        callback: Callback query
        callback_data: Style action data
    """
    text_type = callback_data.text_type
    text_label = "заголовка" if text_type == "title" else "субтитров"
    
    text = f"""
🎨 <b>Выбор цвета {text_label}</b>

Выберите цвет из палитры:

<b>Популярные цвета:</b>
• ⚪ Белый - классический, хорошо читается
• 🔴 Красный - яркий, привлекает внимание  
• 🔵 Синий - профессиональный, надежный
• 🟡 Желтый - энергичный, заметный

<b>Дополнительные цвета:</b>
• 🟢 Зеленый - природный, успокаивающий
• 🟠 Оранжевый - теплый, дружелюбный
• 🟣 Фиолетовый - творческий, необычный
• 🌸 Розовый - нежный, женственный

<i>Выберите цвет, который подходит вашему стилю</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_color_settings_keyboard(text_type),
        parse_mode="HTML"
    )


@router.callback_query(StyleAction.filter(F.action == "size_settings"))
async def show_size_settings(callback: CallbackQuery, callback_data: StyleAction) -> None:
    """
    Show size settings.
    
    Args:
        callback: Callback query
        callback_data: Style action data
    """
    text_type = callback_data.text_type
    text_label = "заголовка" if text_type == "title" else "субтитров"
    
    text = f"""
📏 <b>Выбор размера {text_label}</b>

Выберите оптимальный размер текста:

📏 <b>Маленький</b> - для деликатного оформления
📐 <b>Средний</b> - универсальный выбор
📊 <b>Большой</b> - для важной информации  
📈 <b>Очень большой</b> - максимальная читаемость

<b>Рекомендации:</b>
• Заголовки: средний или большой
• Субтитры: маленький или средний
• Учитывайте размер экрана зрителей

<i>Размер автоматически адаптируется под разрешение видео</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_size_settings_keyboard(text_type),
        parse_mode="HTML"
    )


@router.callback_query(StyleAction.filter(F.action == "set_color"))
async def set_text_color(callback: CallbackQuery, callback_data: StyleAction) -> None:
    """
    Set text color.
    
    Args:
        callback: Callback query
        callback_data: Style action data
    """
    user_id = callback.from_user.id
    text_type = callback_data.text_type
    color = callback_data.value
    text_label = "заголовка" if text_type == "title" else "субтитров"
    
    # Save color to user settings
    settings_key = f"{text_type}_style"
    success = await UserSettingsService.set_style_setting(user_id, settings_key, 'color', color)
    
    if success:
        color_name = UserSettingsService.get_color_name(color)
        await callback.answer(f"✅ Цвет {text_label} изменен на {color_name}", show_alert=True)
    else:
        await callback.answer("❌ Ошибка сохранения настроек", show_alert=True)
    
    # Return to color settings
    await show_color_settings(callback, callback_data)


@router.callback_query(StyleAction.filter(F.action == "set_size"))
async def set_text_size(callback: CallbackQuery, callback_data: StyleAction) -> None:
    """
    Set text size.
    
    Args:
        callback: Callback query
        callback_data: Style action data
    """
    user_id = callback.from_user.id
    text_type = callback_data.text_type
    size = callback_data.value
    text_label = "заголовка" if text_type == "title" else "субтитров"
    
    # Save size to user settings
    settings_key = f"{text_type}_style"
    success = await UserSettingsService.set_style_setting(user_id, settings_key, 'size', size)
    
    if success:
        size_name = UserSettingsService.get_size_name(size)
        await callback.answer(f"✅ Размер {text_label} изменен на {size_name}", show_alert=True)
    else:
        await callback.answer("❌ Ошибка сохранения настроек", show_alert=True)
    
    # Return to size settings
    await show_size_settings(callback, callback_data)


@router.callback_query(StyleAction.filter(F.action == "preview_styles"))
async def preview_styles(callback: CallbackQuery) -> None:
    """
    Show style preview.
    
    Args:
        callback: Callback query
    """
    user_id = callback.from_user.id
    
    # Get current user settings
    title_color = await UserSettingsService.get_style_setting(user_id, 'title_style', 'color')
    title_size = await UserSettingsService.get_style_setting(user_id, 'title_style', 'size')
    title_font = await UserSettingsService.get_style_setting(user_id, 'title_style', 'font')
    
    subtitle_color = await UserSettingsService.get_style_setting(user_id, 'subtitle_style', 'color')
    subtitle_size = await UserSettingsService.get_style_setting(user_id, 'subtitle_style', 'size')
    subtitle_font = await UserSettingsService.get_style_setting(user_id, 'subtitle_style', 'font')
    
    # Get human-readable names
    title_color_name = UserSettingsService.get_color_name(title_color)
    title_size_name = UserSettingsService.get_size_name(title_size)
    subtitle_color_name = UserSettingsService.get_color_name(subtitle_color)
    subtitle_size_name = UserSettingsService.get_size_name(subtitle_size)
    
    text = f"""
👁️ <b>Предпросмотр стилей</b>

<b>Ваши текущие настройки:</b>

📋 <b>Заголовок:</b>
• Цвет: {title_color_name}
• Размер: {title_size_name}
• Шрифт: {title_font}

📝 <b>Субтитры:</b>
• Цвет: {subtitle_color_name}
• Размер: {subtitle_size_name}
• Шрифт: {subtitle_font}

<i>💡 Совет: Обработайте видео чтобы увидеть реальный результат с вашими настройками!</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_style_settings_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(StyleAction.filter(F.action == "reset_styles"))
async def reset_styles(callback: CallbackQuery) -> None:
    """
    Reset styles to default.
    
    Args:
        callback: Callback query
    """
    user_id = callback.from_user.id
    
    # Reset user settings to default
    success = await UserSettingsService.reset_user_settings(user_id)
    
    if success:
        await callback.answer("✅ Стили сброшены к настройкам по умолчанию", show_alert=True)
    else:
        await callback.answer("❌ Ошибка сброса настроек", show_alert=True)
    
    # Return to style menu
    await show_style_settings(callback)


@router.callback_query(StyleAction.filter(F.action == "style_menu"))
async def return_to_style_menu(callback: CallbackQuery) -> None:
    """
    Return to style settings menu.
    
    Args:
        callback: Callback query
    """
    await show_style_settings(callback) 