"""
Font selection and preview handlers for the bot.
"""
import logging
import os
import tempfile
from typing import Any

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bot.keyboards.font_keyboards import (
    FontAction,
    get_font_selection_keyboard,
    get_preview_keyboard,
    get_back_keyboard
)
from app.video_processing.processor import VideoProcessor
from app.config.constants import UserRole
from app.services.user_settings import UserSettingsService

logger = logging.getLogger(__name__)
router = Router()


class FontStates(StatesGroup):
    """States for font selection flow."""
    selecting_font = State()
    preview_settings = State()


@router.callback_query(FontAction.filter(F.action == "select_font"))
async def show_font_selection(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Show available fonts for selection.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    try:
        # Get available fonts
        processor = VideoProcessor()
        fonts = processor.get_available_fonts()
        
        if not fonts:
            await callback.message.edit_text(
                "❌ <b>Шрифты не найдены</b>\n\nНе удалось найти доступные шрифты в системе.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("main_menu")
            )
            return
        
        # Store fonts in state
        await state.update_data(available_fonts=fonts)
        await state.set_state(FontStates.selecting_font)
        
        text = f"""
🔤 <b>Выбор шрифта</b>

Доступно шрифтов: {len(fonts)}

Выберите шрифт для заголовков видео:
        """
        
        await callback.message.edit_text(
            text,
            reply_markup=get_font_selection_keyboard(fonts),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error showing font selection: {e}")
        await callback.answer("❌ Ошибка при загрузке шрифтов", show_alert=True)


@router.callback_query(FontAction.filter(F.action == "choose_font"), FontStates.selecting_font)
async def choose_font(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Handle font selection.
    
    Args:
        callback: Callback query
        callback_data: Font action data with font_name
        state: FSM context
    """
    try:
        # Get state data
        data = await state.get_data()
        fonts = data.get('available_fonts', {})
        
        font_name = callback_data.font_name
        font_path = fonts.get(font_name)
        
        if not font_path or not os.path.exists(font_path):
            await callback.answer("❌ Шрифт не найден", show_alert=True)
            return
        
        # Store selected font
        await state.update_data(
            selected_font_name=font_name,
            selected_font_path=font_path
        )
        
        text = f"""
✅ <b>Шрифт выбран</b>

<b>Выбранный шрифт:</b> {font_name}
<b>Путь:</b> <code>{font_path}</code>

Теперь вы можете:
• 👁️ Создать предпросмотр с этим шрифтом
• 🎬 Использовать для обработки видео
• 🔄 Выбрать другой шрифт
        """
        
        await callback.message.edit_text(
            text,
            reply_markup=get_preview_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error choosing font: {e}")
        await callback.answer("❌ Ошибка при выборе шрифта", show_alert=True)


@router.callback_query(FontAction.filter(F.action == "create_preview"), FontStates.selecting_font)
async def create_preview(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Create preview image with selected font.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    try:
        # Get state data
        data = await state.get_data()
        font_name = data.get('selected_font_name')
        font_path = data.get('selected_font_path')
        
        if not font_path:
            await callback.answer("❌ Сначала выберите шрифт", show_alert=True)
            return
        
        await callback.message.edit_text(
            "🎨 <b>Создание предпросмотра...</b>\n\nПожалуйста, отправьте ссылку на видео или загрузите видеофайл для создания предпросмотра.",
            parse_mode="HTML"
        )
        
        await state.set_state(FontStates.preview_settings)
        
    except Exception as e:
        logger.error(f"Error creating preview: {e}")
        await callback.answer("❌ Ошибка при создании предпросмотра", show_alert=True)


@router.message(FontStates.preview_settings)
async def handle_preview_input(message: Message, state: FSMContext) -> None:
    """
    Handle video input for preview creation.
    
    Args:
        message: Message with video URL or file
        state: FSM context
    """
    try:
        # Get state data
        data = await state.get_data()
        font_name = data.get('selected_font_name')
        font_path = data.get('selected_font_path')
        
        if not font_path:
            await message.answer("❌ Ошибка: шрифт не выбран")
            return
        
        # Send processing message
        processing_msg = await message.answer(
            "🎨 <b>Создание предпросмотра...</b>\n\nЭто может занять несколько секунд.",
            parse_mode="HTML"
        )
        
        # For demo purposes, we'll create a simple preview
        # In real implementation, you would:
        # 1. Download/process the video
        # 2. Create preview image with selected font
        # 3. Send the preview image
        
        preview_text = f"""
🎨 <b>Предпросмотр готов!</b>

<b>Используемый шрифт:</b> {font_name}
<b>Заголовок:</b> "Пример заголовка"

<b>Макет видео:</b>
┌─────────────────┐
│  Пример заголовка  │  ← Ваш заголовок ({font_name})
├─────────────────┤
│                 │
│   Размытый фон  │
│                 │
│  ┌───────────┐  │
│  │           │  │
│  │  Основное │  │  ← Основное видео (по центру)
│  │   видео   │  │
│  │           │  │
│  └───────────┘  │
│                 │
│   Место для     │  ← Область для субтитров
│   субтитров     │
└─────────────────┘

Этот макет будет использован при обработке видео.
        """
        
        await processing_msg.edit_text(
            preview_text,
            reply_markup=get_preview_keyboard(),
            parse_mode="HTML"
        )
        
        # Clear preview state but keep font selection
        await state.set_state(FontStates.selecting_font)
        
    except Exception as e:
        logger.error(f"Error handling preview input: {e}")
        await message.answer("❌ Ошибка при создании предпросмотра")


@router.callback_query(FontAction.filter(F.action == "back_to_fonts"), FontStates.selecting_font)
async def back_to_fonts(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Go back to font selection.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    await show_font_selection(callback, callback_data, state)


@router.callback_query(FontAction.filter(F.action == "use_font"), FontStates.selecting_font)
async def use_selected_font(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Use selected font for video processing.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    try:
        user_id = callback.from_user.id
        logger.info(f"User {user_id} clicked 'Use font' button")
        
        # Get state data
        data = await state.get_data()
        font_name = data.get('selected_font_name')
        font_path = data.get('selected_font_path')
        
        logger.info(f"Font data from state: name={font_name}, path={font_path}")
        
        if not font_path:
            logger.warning(f"No font path in state for user {user_id}")
            await callback.answer("❌ Сначала выберите шрифт", show_alert=True)
            return
        
        # Save font to user settings for both title and subtitle
        logger.info(f"Saving font '{font_name}' to user {user_id} settings")
        title_success = await UserSettingsService.set_style_setting(user_id, 'title_style', 'font', font_name)
        logger.info(f"Title font save result: {title_success}")
        subtitle_success = await UserSettingsService.set_style_setting(user_id, 'subtitle_style', 'font', font_name)
        logger.info(f"Subtitle font save result: {subtitle_success}")
        
        if title_success and subtitle_success:
            text = f"""
✅ <b>Шрифт применен!</b>

<b>Активный шрифт:</b> {font_name}

Шрифт сохранен в ваших настройках и будет использоваться для:
• 📋 Заголовков видео
• 📝 Субтитров

Настройки автоматически применятся при следующей обработке видео.
            """
            
            await callback.answer("✅ Шрифт сохранен в настройках", show_alert=True)
        else:
            text = f"""
⚠️ <b>Частично применено</b>

<b>Выбранный шрифт:</b> {font_name}

Произошла ошибка при сохранении настроек. Попробуйте еще раз.
            """
            
            await callback.answer("⚠️ Ошибка сохранения настроек", show_alert=True)
        
        from app.bot.keyboards.main_menu import get_main_menu_keyboard
        from app.config.constants import UserRole
        
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(UserRole.USER),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error using selected font: {e}")
        await callback.answer("❌ Ошибка при применении шрифта", show_alert=True)


@router.callback_query(FontAction.filter(F.action == "refresh_fonts"), FontStates.selecting_font)
async def refresh_font_list(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Refresh and reload font list.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    await callback.answer("🔄 Обновляем список шрифтов...", show_alert=False)
    await show_font_selection(callback, callback_data, state)


@router.callback_query(FontAction.filter(F.action == "back_to_main"))
async def back_to_main_menu(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Go back to main menu.
    
    Args:
        callback: Callback query
        callback_data: Font action data  
        state: FSM context
    """
    try:
        from app.bot.keyboards.main_menu import get_main_menu_keyboard
        from app.config.constants import UserRole
        
        text = """
🏠 <b>Главное меню</b>

Добро пожаловать в VideoGenerator3000!
Выберите действие из меню ниже:
        """
        
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(UserRole.USER),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error returning to main menu: {e}")
        await callback.answer("❌ Ошибка перехода в главное меню", show_alert=True) 