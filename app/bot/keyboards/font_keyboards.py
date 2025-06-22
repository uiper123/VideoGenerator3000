"""
Keyboards for font selection and preview functionality.
"""
from typing import Dict, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class FontAction(CallbackData, prefix="font"):
    """Callback data for font actions."""
    action: str
    font_name: str = ""


def get_font_selection_keyboard(fonts: Dict[str, str]) -> InlineKeyboardMarkup:
    """
    Create keyboard for font selection.
    
    Args:
        fonts: Dictionary of font names to paths
        
    Returns:
        InlineKeyboardMarkup with font options
    """
    buttons = []
    
    # Add font buttons (max 10 fonts per page for better UX)
    font_items = list(fonts.items())[:10]
    
    for font_name, font_path in font_items:
        # Truncate long font names for better display
        display_name = font_name if len(font_name) <= 30 else font_name[:27] + "..."
        
        buttons.append([
            InlineKeyboardButton(
                text=f"🔤 {display_name}",
                callback_data=FontAction(action="choose_font", font_name=font_name).pack()
            )
        ])
    
    # Add navigation buttons
    buttons.append([
        InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data=FontAction(action="refresh_fonts").pack()
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=FontAction(action="back_to_main").pack()
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_preview_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for preview actions.
    
    Returns:
        InlineKeyboardMarkup with preview options
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👁️ Создать предпросмотр",
                callback_data=FontAction(action="create_preview").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Использовать шрифт",
                callback_data=FontAction(action="use_font").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Выбрать другой шрифт",
                callback_data=FontAction(action="back_to_fonts").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Главное меню",
                callback_data=FontAction(action="back_to_main").pack()
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(target: str) -> InlineKeyboardMarkup:
    """
    Create simple back keyboard.
    
    Args:
        target: Target to go back to
        
    Returns:
        InlineKeyboardMarkup with back button
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=FontAction(action=f"back_to_{target}").pack()
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons) 