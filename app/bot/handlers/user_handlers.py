"""
User handlers for basic bot commands and navigation.
"""
import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.main_menu import (
    MenuAction, 
    get_main_menu_keyboard,
    get_video_menu_keyboard,
    get_back_keyboard
)
from app.config.constants import MENU_EMOJIS


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
    welcome_text = f"""
🎬 <b>Добро пожаловать в Video Bot!</b>

Привет, {message.from_user.first_name}! 👋

Я помогу вам автоматически обрабатывать видео и создавать короткие фрагменты в формате YouTube Shorts/TikTok.

<b>Что я умею:</b>
• 📥 Скачивать видео по ссылкам
• ✂️ Нарезать на фрагменты
• 🎨 Преобразовывать в формат 9:16
• 📝 Добавлять субтитры

<b>Поддерживаемые источники:</b>
YouTube, TikTok, Instagram, Vimeo и другие

Выберите действие в меню ниже:
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
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

<b>Нужна помощь?</b>
Свяжитесь с администратором: @admin
    """
    
    await message.answer(help_text, parse_mode="HTML")


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
    text = f"""
🏠 <b>Главное меню</b>

Добро пожаловать в Video Bot!
Выберите нужное действие:
    """
    
    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(),
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
    """
    
    await callback.message.edit_text(
        text,
        reply_markup=get_video_menu_keyboard(),
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

<b>🚀 Результат:</b>
• Формат: 1080x1920 (9:16)
• Качество: до 4K
• Субтитры: автоматические

<b>❓ Нужна помощь?</b>
Обратитесь к администратору: @admin
    """
    
    await callback.message.edit_text(
        help_text,
        reply_markup=get_back_keyboard("main_menu"),
        parse_mode="HTML"
    )


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