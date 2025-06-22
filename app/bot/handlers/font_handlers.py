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
from app.bot.handlers.settings_handlers import show_style_settings

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
    Save the selected font to user settings.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    try:
        data = await state.get_data()
        font_name = data.get('selected_font_name')
        
        if not font_name:
            await callback.answer("❌ Шрифт не выбран.", show_alert=True)
            return
            
        user_id = callback.from_user.id
        
        # Persist the selected font in user settings
        # For now, we assume this sets the title font.
        # This could be extended to ask the user whether to set for title or subtitle.
        settings_key = "title_style"
        success = await UserSettingsService.set_style_setting(user_id, settings_key, 'font', font_name)
        
        if success:
            await callback.answer(f"✅ Шрифт '{font_name}' сохранен для заголовков.", show_alert=True)
            
            # Now, we want to return to the style settings menu.
            # To do this, we can call the handler from settings_handlers.
            # We need to make sure the state is correctly managed.
            await show_style_settings(callback, state)
            
        else:
            await callback.answer("❌ Не удалось сохранить шрифт. Попробуйте снова.", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error using selected font: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при сохранении шрифта.", show_alert=True)


@router.callback_query(FontAction.filter(F.action == "refresh_fonts"), FontStates.selecting_font)
async def refresh_font_list(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Refresh the list of available fonts.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    await show_font_selection(callback, callback_data, state)


@router.callback_query(FontAction.filter(F.action == "back_to_main"))
async def back_to_main_menu(callback: CallbackQuery, callback_data: FontAction, state: FSMContext) -> None:
    """
    Return to the main menu.
    
    Args:
        callback: Callback query
        callback_data: Font action data
        state: FSM context
    """
    from app.bot.handlers.main_handlers import main_menu
    await main_menu(callback.message, state) 