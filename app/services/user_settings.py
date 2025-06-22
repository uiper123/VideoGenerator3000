"""
User settings service for managing style preferences.
"""
import logging
from typing import Dict, Any, Optional

from app.database.connection import get_db_session
from app.database.models import User

logger = logging.getLogger(__name__)


class UserSettingsService:
    """Service for managing user style settings."""
    
    DEFAULT_SETTINGS = {
        'title_style': {
            'color': 'white',
            'size': 'medium',
            'font': 'DejaVu Sans Bold'
        },
        'subtitle_style': {
            'color': 'white',
            'size': 'medium',
            'font': 'DejaVu Sans Bold'
        },
        'video_settings': {
            'quality': '1080p',
            'fragment_duration': 30,
            'enable_subtitles': True
        }
    }
    
    @staticmethod
    async def get_user_settings(user_id: int) -> Dict[str, Any]:
        """
        Get user settings with defaults.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict with user settings
        """
        try:
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                
                if not user:
                    logger.warning(f"User {user_id} not found, returning default settings")
                    return UserSettingsService.DEFAULT_SETTINGS.copy()
                
                # Merge user settings with defaults
                settings = UserSettingsService.DEFAULT_SETTINGS.copy()
                if user.settings:
                    settings.update(user.settings)
                
                return settings
                
        except Exception as e:
            logger.error(f"Failed to get user settings for {user_id}: {e}")
            return UserSettingsService.DEFAULT_SETTINGS.copy()
    
    @staticmethod
    async def update_user_setting(user_id: int, setting_path: str, value: Any) -> bool:
        """
        Update a specific user setting.
        
        Args:
            user_id: Telegram user ID
            setting_path: Dot notation path (e.g., 'title_style.color')
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                # Initialize settings if not exists
                if not user.settings:
                    user.settings = UserSettingsService.DEFAULT_SETTINGS.copy()
                else:
                    # Create a copy to avoid mutating the original
                    current_settings = UserSettingsService.DEFAULT_SETTINGS.copy()
                    current_settings.update(user.settings)
                    user.settings = current_settings
                
                # Update the specific setting using dot notation
                keys = setting_path.split('.')
                setting_dict = user.settings
                
                # Navigate to the parent dict
                for key in keys[:-1]:
                    if key not in setting_dict:
                        setting_dict[key] = {}
                    setting_dict = setting_dict[key]
                
                # Set the final value
                setting_dict[keys[-1]] = value
                
                # Mark the session as dirty to trigger update
                from sqlalchemy.orm import make_transient
                session.add(user)
                await session.commit()
                
                logger.info(f"Updated setting {setting_path} = {value} for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update setting {setting_path} for user {user_id}: {e}")
            return False
    
    @staticmethod
    async def get_style_setting(user_id: int, text_type: str, style_key: str) -> Any:
        """
        Get a specific style setting.
        
        Args:
            user_id: Telegram user ID
            text_type: 'title_style' or 'subtitle_style'
            style_key: 'color', 'size', or 'font'
            
        Returns:
            Setting value or default
        """
        settings = await UserSettingsService.get_user_settings(user_id)
        return settings.get(text_type, {}).get(style_key, 
                           UserSettingsService.DEFAULT_SETTINGS[text_type][style_key])
    
    @staticmethod
    async def set_style_setting(user_id: int, text_type: str, style_key: str, value: Any) -> bool:
        """
        Set a specific style setting.
        
        Args:
            user_id: Telegram user ID
            text_type: 'title_style' or 'subtitle_style'
            style_key: 'color', 'size', or 'font'
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        setting_path = f"{text_type}.{style_key}"
        return await UserSettingsService.update_user_setting(user_id, setting_path, value)
    
    @staticmethod
    async def reset_user_settings(user_id: int) -> bool:
        """
        Reset user settings to defaults.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                user.settings = UserSettingsService.DEFAULT_SETTINGS.copy()
                session.add(user)
                await session.commit()
                
                logger.info(f"Reset settings to defaults for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to reset settings for user {user_id}: {e}")
            return False
    
    @staticmethod
    def get_color_name(color_value: str) -> str:
        """Get human-readable color name."""
        color_names = {
            'white': '⚪ Белый',
            'red': '🔴 Красный',
            'blue': '🔵 Синий',
            'yellow': '🟡 Желтый',
            'green': '🟢 Зеленый',
            'orange': '🟠 Оранжевый',
            'purple': '🟣 Фиолетовый',
            'pink': '🌸 Розовый'
        }
        return color_names.get(color_value, color_value)
    
    @staticmethod
    def get_size_name(size_value: str) -> str:
        """Get human-readable size name."""
        size_names = {
            'small': '📏 Маленький',
            'medium': '📐 Средний',
            'large': '📊 Большой',
            'extra_large': '📈 Очень большой'
        }
        return size_names.get(size_value, size_value) 