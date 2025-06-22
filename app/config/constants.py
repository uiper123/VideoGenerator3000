"""
Application constants and enums.
"""
from enum import Enum


class VideoQuality(str, Enum):
    """Video quality options."""
    SD = "720p"
    HD = "1080p"
    UHD = "4k"


class VideoStatus(str, Enum):
    """Video processing status."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, Enum):
    """User roles."""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SubtitleStyle(str, Enum):
    """Subtitle styles."""
    CLASSIC = "classic"
    MODERN = "modern"
    COLORFUL = "colorful"


# Video processing constants
MAX_FRAGMENT_DURATION = 60  # seconds
MIN_FRAGMENT_DURATION = 15  # seconds
DEFAULT_FRAGMENT_DURATION = 30  # seconds

# Shorts format specifications
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_RESOLUTION = (SHORTS_WIDTH, SHORTS_HEIGHT)  # 9:16 aspect ratio
SHORTS_FPS = 30
SHORTS_BITRATE = "8M"

# Supported video formats
SUPPORTED_INPUT_FORMATS = [
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"
]

# Supported video sources
SUPPORTED_SOURCES = [
    "youtube.com",
    "youtu.be", 
    "tiktok.com",
    "instagram.com",
    "vimeo.com",
    "twitter.com",
    "x.com"
]

# Font settings for subtitles
SUBTITLE_FONTS = {
    SubtitleStyle.CLASSIC: {
        "font": "Arial Bold",
        "size": 48,
        "color": "white",
        "stroke": "black",
        "stroke_width": 2
    },
    SubtitleStyle.MODERN: {
        "font": "Roboto Bold", 
        "size": 52,
        "color": "white",
        "background": "rgba(0,0,0,0.7)",
        "padding": 10
    },
    SubtitleStyle.COLORFUL: {
        "font": "Impact",
        "size": 56,
        "color": "yellow",
        "stroke": "black",
        "stroke_width": 3
    }
}

# Default text styles for video processing
DEFAULT_TEXT_STYLES = {
    'title': {
        'color': 'white',
        'size_ratio': 0.06,  # 6% of video height
        'position_y_ratio': 0.05,  # 5% from top
        'border_color': 'black',
        'border_width': 3
    },
    'subtitle': {
        'color': 'white',
        'size_ratio': 0.045,  # 4.5% of video height
        'position_y_ratio': 0.8,  # 80% from top (bottom area)
        'border_color': 'black',
        'border_width': 2
    }
}

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 30
RATE_LIMIT_REQUESTS_PER_HOUR = 100

# File size limits  
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB for direct uploads
MAX_DOWNLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB for downloads

# API limits
GOOGLE_DRIVE_REQUESTS_PER_HOUR = 1000
GOOGLE_SHEETS_REQUESTS_PER_SECOND = 100
TELEGRAM_MESSAGES_PER_SECOND = 30

# Background task settings
CELERY_TASK_TIME_LIMIT = 3600  # 1 hour
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 55 minutes

# Error messages
ERROR_MESSAGES = {
    "video_too_long": "❌ Видео слишком длинное. Максимальная длительность: 3 часа",
    "file_too_large": "❌ Файл слишком большой. Максимальный размер: 2GB", 
    "unsupported_format": "❌ Неподдерживаемый формат видео",
    "invalid_url": "❌ Некорректная ссылка на видео",
    "download_failed": "❌ Ошибка скачивания видео",
    "processing_failed": "❌ Ошибка обработки видео",
    "upload_failed": "❌ Ошибка загрузки в облако",
    "rate_limit_exceeded": "❌ Превышен лимит запросов. Попробуйте позже",
    "server_error": "❌ Ошибка сервера. Попробуйте позже"
}

# Success messages
SUCCESS_MESSAGES = {
    "video_processing_started": "✅ Обработка видео началась",
    "video_processing_completed": "✅ Видео успешно обработано",
    "fragments_created": "✅ Создано фрагментов: {count}",
    "uploaded_to_drive": "✅ Загружено в Google Drive"
}

# Menu emojis
MENU_EMOJIS = {
    "video": "🎬",
    "settings": "⚙️", 
    "stats": "📊",
    "help": "❓",
    "admin": "👨‍💼",
    "back": "⬅️",
    "link": "📎",
    "file": "📁",
    "batch": "📋",
    "tasks": "🔄"
} 