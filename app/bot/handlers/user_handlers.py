"""
User handlers for basic bot commands and navigation.
"""
import logging
from typing import Any

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.main_menu import (
    MenuAction, 
    SettingsAction,
    get_main_menu_keyboard,
    get_video_menu_keyboard,
    get_settings_menu_keyboard,
    get_main_reply_keyboard
)
from app.bot.keyboards.font_keyboards import FontAction
from app.config.constants import UserRole, MENU_EMOJIS
from app.database.connection import get_db_session
from app.database.models import User


logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    """
    Handle /start command.
    
    Args:
        message: Telegram message
        bot: Bot instance
    """
    user_id = message.from_user.id
    
    # Create or update user in database
    async with get_db_session() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(
                id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                is_active=True
            )
            session.add(user)
            await session.commit()
            logger.info(f"New user registered: {user_id}")
        else:
            # Update user info if changed
            user.username = message.from_user.username
            user.first_name = message.from_user.first_name
            user.last_name = message.from_user.last_name
            user.is_active = True
            await session.commit()
    
    welcome_text = f"""
🎬 <b>Добро пожаловать в Video Bot!</b>

Привет, {message.from_user.first_name}! 👋

Я помогу вам автоматически обрабатывать видео и создавать короткие фрагменты в формате YouTube Shorts/TikTok.

<b>Что я умею:</b>
• 📥 Скачивать видео по ссылкам
• ✂️ Нарезать на фрагменты
• 🎨 Преобразовывать в формат 9:16
• 📝 Добавлять субтитры
• 💾 Сохранять в Google Drive
• 📊 Ведить статистику

<b>Поддерживаемые источники:</b>
YouTube, TikTok, Instagram, Vimeo и другие

Выберите действие в меню ниже:
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user.role),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Handle /help command.
    
    Args:
        message: Telegram message
    """
    help_text = f"""
{MENU_EMOJIS['help']} <b>Справка по боту</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка
/stats - Моя статистика

<b>Как обработать видео:</b>
1. Нажмите "🎬 Обработать видео"
2. Выберите способ ввода (ссылка или файл)
3. Настройте параметры обработки
4. Дождитесь завершения

<b>Поддерживаемые форматы:</b>
• MP4, AVI, MKV, MOV, WMV, FLV, WebM

<b>Ограничения:</b>
• Максимальная длительность: 3 часа
• Максимальный размер файла: 2GB
• Одновременно в обработке: 5 видео

<b>Нужна помощь?</b>
Свяжитесь с администратором: @admin
    """
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Handle /stats command.
    
    Args:
        message: Telegram message
    """
    user_id = message.from_user.id
    
    async with get_db_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
        
        # TODO: Implement actual statistics calculation
        stats_text = f"""
{MENU_EMOJIS['stats']} <b>Ваша статистика</b>

👤 <b>Пользователь:</b> {user.display_name}
📅 <b>Дата регистрации:</b> {user.created_at.strftime('%d.%m.%Y')}

📹 <b>Обработано видео:</b> 0
⏱️ <b>Общее время:</b> 0 мин
💾 <b>Общий размер:</b> 0 МБ
📊 <b>Создано фрагментов:</b> 0

<i>Начните обрабатывать видео, чтобы увидеть статистику!</i>
        """
        
        await message.answer(stats_text, parse_mode="HTML")


# Menu navigation handlers
@router.callback_query(MenuAction.filter(F.action == "main_menu"))
async def show_main_menu(callback: CallbackQuery, callback_data: MenuAction, bot: Bot) -> None:
    """
    Show main menu.
    
    Args:
        callback: Callback query
        callback_data: Menu action data
        bot: Bot instance
    """
    user_id = callback.from_user.id
    
    async with get_db_session() as session:
        user = await session.get(User, user_id)
        user_role = user.role if user else UserRole.USER
    
    text = f"""
🏠 <b>Главное меню</b>

Добро пожаловать в Video Bot!
Выберите нужное действие:
    """
    
    # Use .edit_text if it's a callback, otherwise .answer for a new message
    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(user_role),
            parse_mode="HTML"
        )
    else:
        await callback.answer()


@router.callback_query(MenuAction.filter(F.action == "video_menu"))
async def show_video_menu(callback: CallbackQuery, callback_data: MenuAction) -> None:
    """
    Show video processing menu.
    
    Args:
        callback: Callback query
        callback_data: Menu action data
    """
    text = f"""
{MENU_EMOJIS['video']} <b>Обработка видео</b>

Выберите способ добавления видео для обработки:

📎 <b>Ссылка</b> - Вставить ссылку на видео
📁 <b>Файл</b> - Загрузить видео файл
📋 <b>Пакет</b> - Обработать несколько видео
🔄 <b>Задачи</b> - Посмотреть статус обработки
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_video_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(MenuAction.filter(F.action == "settings_menu"))
async def show_settings_menu(callback: CallbackQuery, callback_data: MenuAction) -> None:
    """
    Show settings menu.
    
    Args:
        callback: Callback query
        callback_data: Menu action data
    """
    text = f"""
{MENU_EMOJIS['settings']} <b>Настройки</b>

Настройте бот под свои потребности:

🔤 <b>Шрифты</b> - Выбор шрифтов для заголовков
🎬 <b>Видео</b> - Качество, длительность фрагментов
💾 <b>Сохранение</b> - Google Drive, папки
🔔 <b>Уведомления</b> - Когда получать уведомления
👤 <b>Профиль</b> - Личная информация
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(MenuAction.filter(F.action == "stats_menu"))
async def show_stats_menu(callback: CallbackQuery, callback_data: MenuAction) -> None:
    """
    Show statistics menu.
    
    Args:
        callback: Callback query
        callback_data: Menu action data
    """
    user_id = callback.from_user.id
    
    async with get_db_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # TODO: Calculate real statistics
        stats_text = f"""
{MENU_EMOJIS['stats']} <b>Подробная статистика</b>

👤 <b>Профиль:</b>
• Имя: {user.display_name}
• Роль: {user.role.value.title()}
• Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}

📊 <b>Обработка видео:</b>
• Всего обработано: 0
• В процессе: 0
• Завершено успешно: 0
• Ошибок: 0

⏱️ <b>Время обработки:</b>
• Общее время: 0 мин
• Среднее время: 0 мин
• Самое быстрое: -
• Самое долгое: -

💾 <b>Данные:</b>
• Общий размер: 0 МБ
• Фрагментов создано: 0
• В Google Drive: 0

📈 <b>За последнюю неделю:</b>
• Видео: 0
• Фрагменты: 0
• Время: 0 мин
        """
        
        from app.bot.keyboards.main_menu import get_back_keyboard
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_keyboard("main_menu"),
            parse_mode="HTML"
        )
    

@router.callback_query(MenuAction.filter(F.action == "help"))
async def show_help(callback: CallbackQuery, callback_data: MenuAction) -> None:
    """
    Show help information.
    
    Args:
        callback: Callback query
        callback_data: Menu action data
    """
    help_text = f"""
{MENU_EMOJIS['help']} <b>Подробная справка</b>

<b>🎬 Обработка видео:</b>
1. Выберите "Обработать видео"
2. Укажите ссылку или загрузите файл
3. Настройте параметры:
   • Длительность фрагментов (15-60 сек)
   • Качество (720p, 1080p, 4K)
   • Субтитры (вкл/выкл)
4. Нажмите "Начать обработку"

<b>📎 Поддерживаемые ссылки:</b>
• YouTube (youtube.com, youtu.be)
• TikTok (tiktok.com)
• Instagram (instagram.com)
• Vimeo (vimeo.com)
• Twitter/X (twitter.com, x.com)

<b>📁 Поддерживаемые форматы:</b>
MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V

<b>⚠️ Ограничения:</b>
• Длительность видео: до 3 часов
• Размер файла: до 2GB
• Одновременно: до 5 задач

<b>🚀 Результат:</b>
• Формат: 1080x1920 (9:16)
• Качество: до 4K
• Субтитры: автоматические
• Сохранение: Google Drive

<b>❓ Нужна помощь?</b>
Обратитесь к администратору: @admin
    """
    
    from app.bot.keyboards.main_menu import get_back_keyboard
    
    await callback.message.edit_text(
        help_text,
        reply_markup=get_back_keyboard("main_menu"),
        parse_mode="HTML"
    )


# Handle reply keyboard buttons
@router.message(F.text == "🏠 Главное меню")
async def handle_main_menu_button(message: Message, bot: Bot) -> None:
    """Handle main menu button from reply keyboard."""
    user_id = message.from_user.id
    
    async with get_db_session() as session:
        user = await session.get(User, user_id)
        user_role = user.role if user else UserRole.USER
    
    text = "🏠 <b>Главное меню</b>\n\nВыберите действие:"
    
    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(user_role),
        parse_mode="HTML"
    )


@router.message(F.text == "❓ Помощь")
async def handle_help_button(message: Message) -> None:
    """Handle help button from reply keyboard."""
    await cmd_help(message)


@router.message(F.text == "🎬 Быстрая обработка")
async def handle_quick_processing_button(message: Message) -> None:
    """Handle quick processing button from reply keyboard."""
    text = f"""
🎬 <b>Быстрая обработка</b>

Отправьте ссылку на видео или видео файл для быстрой обработки со стандартными настройками:

• Длительность фрагментов: 30 сек
• Качество: 1080p
• Субтитры: включены

<i>Просто отправьте ссылку или файл следующим сообщением</i>
    """
    
    from app.bot.keyboards.main_menu import get_back_keyboard
    
    await message.answer(
        text,
        reply_markup=get_back_keyboard("main_menu"),
        parse_mode="HTML"
    )


@router.message(F.text == "📋 Мои задачи")
async def handle_my_tasks_button(message: Message) -> None:
    """Handle my tasks button from reply keyboard."""
    # TODO: Implement tasks list
    text = """
📋 <b>Мои задачи</b>

У вас пока нет активных задач обработки видео.

Начните обработку видео, чтобы увидеть задачи здесь.
    """
    
    from app.bot.keyboards.main_menu import get_back_keyboard
    
    await message.answer(
        text,
        reply_markup=get_back_keyboard("main_menu"),
        parse_mode="HTML"
    )


@router.callback_query(SettingsAction.filter(F.action == "font_settings"))
async def handle_font_settings(callback: CallbackQuery, callback_data: SettingsAction, state: FSMContext) -> None:
    """
    Handle font settings button.
    
    Args:
        callback: Callback query
        callback_data: Settings action data
        state: FSM context
    """
    # Redirect to font selection
    from app.bot.keyboards.font_keyboards import FontAction
    font_action = FontAction(action="select_font")
    
    # Import and call font handler
    from app.bot.handlers.font_handlers import show_font_selection
    await show_font_selection(callback, font_action, state)


@router.callback_query(MenuAction.filter(F.action == "cancel"))
async def handle_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle cancel action.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    current_state = await state.get_state()
    if current_state is None:
        await callback.answer()
        return

    logger.info(f"Cancelling state {current_state} for user {callback.from_user.id}")
    await state.clear()

    await callback.message.edit_text(
        "❌ <b>Действие отменено</b>",
        parse_mode="HTML"
    )
    # Go back to the main menu after cancellation
    await show_main_menu(callback, MenuAction(action="main_menu"), callback.bot)


