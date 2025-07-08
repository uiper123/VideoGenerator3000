"""
Settings handlers for the Telegram bot.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.bot.keyboards.main_menu import (
    SettingsAction,
    SettingsValueAction,
    StyleAction,
    get_back_keyboard,
    get_confirmation_keyboard,
    get_style_settings_menu_keyboard,
    get_text_settings_keyboard,
    get_color_settings_keyboard,
    get_size_settings_keyboard
)
from app.bot.keyboards.font_keyboards import FontAction
from app.config.constants import MENU_EMOJIS
from app.database.connection import get_db_session
from app.database.models import User
from app.services.user_settings import UserSettingsService, NoSettingsError
from app.bot.handlers.video_handlers import show_video_settings
from app.bot.handlers.video_handlers import VideoProcessingStates

logger = logging.getLogger(__name__)
router = Router()


class SettingsStates(StatesGroup):
    """States for settings management."""
    main = State()
    title_settings = State()
    subtitle_settings = State()


class ProxyStates(StatesGroup):
    input = State()


def parse_proxy_text(text: str) -> str:
    """
    Парсит текст с данными прокси и возвращает строку для yt-dlp.
    Если не удаётся — возвращает пустую строку.
    Если в тексте есть 'SOCKS' — использовать socks5://, иначе http://
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    login, password, ip, port = None, None, None, None
    protocol = "http"  # По умолчанию http
    for l in lines:
        if "socks" in l.lower():
            protocol = "socks5"
        elif "http" in l.lower():
            protocol = "http"
    for l in lines:
        if l.count('.') == 3 and all(part.isdigit() for part in l.split('.') if part):
            ip = l
        elif l.isdigit() and len(l) >= 4:
            port = l
        elif not login:
            login = l
        elif not password:
            password = l
    if ip and port and login and password:
        return f"{protocol}://{login}:{password}@{ip}:{port}"
    return ""


@router.callback_query(SettingsAction.filter(F.action == "open_settings_menu"))
async def show_settings_menu(callback: CallbackQuery, callback_data: SettingsAction, state: FSMContext) -> None:
    """
    Show settings menu.
    
    Args:
        callback: Callback query
        callback_data: Settings action data
        state: FSM context
    """
    try:
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
    except Exception as e:
        logger.error(f"Error in show_settings_menu: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке настроек", show_alert=True)


@router.callback_query(SettingsAction.filter(F.action == "title_settings"), SettingsStates.main)
async def show_title_settings(callback: CallbackQuery, callback_data: SettingsAction, state: FSMContext) -> None:
    """Show title settings menu."""
    await state.set_state(SettingsStates.title_settings)
    text = f"""
🎨 <b>Настройки стилей текста</b>

📋 <b>Заголовки:</b>
• Цвет, размер, шрифт
• Положение на экране
• Стиль оформления

👁️ <b>Предпросмотр:</b>
Проверьте как будут выглядеть ваши настройки

<i>Все изменения сохраняются автоматически</i>
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_style_settings_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(SettingsAction.filter(F.action == "subtitle_settings"), SettingsStates.main)
async def show_subtitle_settings(callback: CallbackQuery, callback_data: SettingsAction, state: FSMContext) -> None:
    """Show subtitle settings menu."""
    await state.set_state(SettingsStates.subtitle_settings)
    text = f"""
🎨 <b>Настройки стилей текста</b>

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


@router.callback_query(SettingsAction.filter(F.action == "preview_style"), SettingsStates.main)
async def preview_style(callback: CallbackQuery, state: FSMContext) -> None:
    """Generate and send a preview of the current style settings."""
    await callback.answer("⚙️ Генерируется предпросмотр...", show_alert=False)
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
    if not preview_style:
        await callback.answer("❌ Ошибка при создании предпросмотра.", show_alert=True)


@router.callback_query(SettingsAction.filter(F.action == "reset_to_defaults"), SettingsStates.main)
async def reset_settings_to_defaults(callback: CallbackQuery, state: FSMContext) -> None:
    """Reset user settings to default values."""
    user_id = callback.from_user.id
    
    # Reset user settings to default
    success = await UserSettingsService.reset_user_settings(user_id)
    
    if success:
        await callback.answer("✅ Стили сброшены к настройкам по умолчанию", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при сбросе настроек.", show_alert=True)
    
    # Return to style menu
    await show_style_settings(callback)


@router.callback_query(SettingsAction.filter(F.action == "back_to_settings"), SettingsStates)
async def back_to_settings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to the main settings menu."""
    await show_settings_menu(callback, SettingsAction(action="open_settings_menu"), state)


# --- Title Settings Handlers ---

@router.callback_query(SettingsValueAction.filter(F.entity == "title" and F.param == "color"), SettingsStates.title_settings)
async def set_title_color(callback: CallbackQuery, callback_data: SettingsValueAction, state: FSMContext) -> None:
    """Set the color for the title."""
    user_id = callback.from_user.id
    color = callback_data.value
    
    # Save color to user settings
    settings_key = "title_style"
    success = await UserSettingsService.set_style_setting(user_id, settings_key, 'color', color)
    
    if success:
        color_name = UserSettingsService.get_color_name(color)
        await callback.answer(f"✅ Цвет заголовка изменен на {color_name}", show_alert=True)
    else:
        await callback.answer("❌ Ошибка сохранения настроек", show_alert=True)
    
    # Return to title settings
    await show_title_settings(callback, SettingsAction(action="title_settings"), state)


@router.callback_query(SettingsValueAction.filter(F.entity == "title" and F.param == "size"), SettingsStates.title_settings)
async def set_title_size(callback: CallbackQuery, callback_data: SettingsValueAction, state: FSMContext) -> None:
    """Set the size for the title."""
    user_id = callback.from_user.id
    size = callback_data.value
    
    # Save size to user settings
    settings_key = "title_style"
    success = await UserSettingsService.set_style_setting(user_id, settings_key, 'size', size)
    
    if success:
        size_name = UserSettingsService.get_size_name(size)
        await callback.answer(f"✅ Размер заголовка изменен на {size_name}", show_alert=True)
    else:
        await callback.answer("❌ Ошибка сохранения настроек", show_alert=True)
    
    # Return to title settings
    await show_title_settings(callback, SettingsAction(action="title_settings"), state)


@router.callback_query(SettingsAction.filter(F.action == "font_settings"), SettingsStates.title_settings)
async def open_font_settings(callback: CallbackQuery, state: FSMContext) -> None:
    """Redirect to the font selection menu."""
    # We need to call the handler from font_handlers.py
    # To do this cleanly, we can use a dispatcher instance if available
    # or just inform the user. For now, let's just send a message.
    # A better way would be to refactor this to use a shared service or router.
    from app.bot.handlers.font_handlers import show_font_selection
    await callback.message.answer("Переход в меню выбора шрифтов...")
    # This simulates a user command to open the font menu
    # Note: This is a simplified approach.
    # A full solution might involve deeper integration between handlers.
    await show_font_selection(callback, FontAction(action="select_font"), state)


# --- Subtitle Settings Handlers ---

@router.callback_query(SettingsValueAction.filter(F.entity == "subtitle" and F.param == "color"), SettingsStates.subtitle_settings)
async def set_subtitle_color(callback: CallbackQuery, callback_data: SettingsValueAction, state: FSMContext) -> None:
    """Set the color for the subtitle."""
    user_id = callback.from_user.id
    color = callback_data.value
    
    # Save color to user settings
    settings_key = "subtitle_style"
    success = await UserSettingsService.set_style_setting(user_id, settings_key, 'color', color)
    
    if success:
        color_name = UserSettingsService.get_color_name(color)
        await callback.answer(f"✅ Цвет субтитров изменен на {color_name}", show_alert=True)
    else:
        await callback.answer("❌ Ошибка сохранения настроек", show_alert=True)
    
    # Return to subtitle settings
    await show_subtitle_settings(callback, SettingsAction(action="subtitle_settings"), state)


@router.callback_query(SettingsValueAction.filter(F.entity == "subtitle" and F.param == "size"), SettingsStates.subtitle_settings)
async def set_subtitle_size(callback: CallbackQuery, callback_data: SettingsValueAction, state: FSMContext) -> None:
    """Set the size for the subtitle."""
    user_id = callback.from_user.id
    size = callback_data.value
    
    # Save size to user settings
    settings_key = "subtitle_style"
    success = await UserSettingsService.set_style_setting(user_id, settings_key, 'size', size)
    
    if success:
        size_name = UserSettingsService.get_size_name(size)
        await callback.answer(f"✅ Размер субтитров изменен на {size_name}", show_alert=True)
    else:
        await callback.answer("❌ Ошибка сохранения настроек", show_alert=True)
    
    # Return to subtitle settings
    await show_subtitle_settings(callback, SettingsAction(action="subtitle_settings"), state)


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


@router.callback_query(StyleAction.filter(F.action == "text_settings"), SettingsStates.main)
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


@router.callback_query(SettingsAction.filter(F.action == "proxy_settings"))
async def show_proxy_settings(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info(f"[DEBUG] Кнопка 'Прокси для скачивания' нажата пользователем {callback.from_user.id}")
    await state.set_state(ProxyStates.input)
    text = (
        "🌐 <b>Прокси для скачивания</b>\n\n"
        "Вставьте сюда данные прокси (можно просто скопировать из письма/кабинета):\n\n"
        "<i>Пример:</i>\nPv4 Shared\nРоссия\nlZOy6obFDx\nGkiORLG8mS\n109.120.147.249\n55799\n24933\n20 Mbps\n11.07.2025, 9:53\nНе указан\n\n"
        "Бот автоматически преобразует их в нужный формат.\n\n"
        "<b>Внимание:</b> Прокси будет использоваться только для ваших загрузок!"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer() 


@router.callback_query(SettingsAction.filter(F.action == "proxy_settings"), VideoProcessingStates.configuring_settings)
async def show_proxy_settings_from_video(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать меню настройки прокси из окна обработки видео."""
    await state.set_state(ProxyStates.input)
    # Сохраняем, что нужно вернуться к настройкам видео
    await state.update_data(_return_to_video_settings=True)
    text = (
        "🌐 <b>Прокси для скачивания</b>\n\n"
        "Вставьте сюда данные прокси (можно просто скопировать из письма/кабинета):\n\n"
        "<i>Пример:</i>\nPv4 Shared\nРоссия\nlZOy6obFDx\nGkiORLG8mS\n109.120.147.249\n55799\n24933\n20 Mbps\n11.07.2025, 9:53\nНе указан\n\n"
        "Бот автоматически преобразует их в нужный формат.\n\n"
        "<b>Внимание:</b> Прокси будет использоваться только для ваших загрузок!"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.message(ProxyStates.input)
async def handle_proxy_input(message: Message, state: FSMContext) -> None:
    logger.info(f"[DEBUG] Пользователь {message.from_user.id} отправил данные для прокси: {message.text}")
    """Обрабатывает ввод данных прокси, парсит и сохраняет для пользователя. После успешного ввода возвращает к настройкам видео, если нужно."""
    user_id = message.from_user.id
    proxy_str = parse_proxy_text(message.text)
    data = await state.get_data()
    if proxy_str:
        # Сохраняем в пользовательских настройках
        await UserSettingsService.set_user_setting(user_id, 'download_proxy', proxy_str)
        await message.answer(f"✅ Прокси сохранён и будет использоваться для ваших загрузок!\n\n<code>{proxy_str}</code>", parse_mode="HTML")
        # Если нужно вернуться к настройкам видео — возвращаем
        if data.get('_return_to_video_settings'):
            await state.set_state(VideoProcessingStates.configuring_settings)
            source = data.get('source_url', data.get('file_name', ''))
            from app.bot.handlers.video_handlers import show_video_settings
            await show_video_settings(message, state, source)
        else:
            await state.clear()
    else:
        await message.answer("❌ Не удалось распознать данные прокси. Проверьте формат и попробуйте ещё раз.") 