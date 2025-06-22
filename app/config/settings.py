"""
Configuration settings for the Video Bot application.
Uses Pydantic Settings for validation and environment variable management.
"""
import os
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/videobot",
        env="DATABASE_URL",
        description="Database connection URL"
    )
    echo: bool = Field(
        default=False,
        env="DATABASE_ECHO",
        description="Enable SQLAlchemy query logging"
    )
    pool_size: int = Field(
        default=20,
        env="DATABASE_POOL_SIZE",
        description="Database connection pool size"
    )
    max_overflow: int = Field(
        default=30,
        env="DATABASE_MAX_OVERFLOW",
        description="Database connection pool max overflow"
    )

    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL"
    )
    max_connections: int = Field(
        default=20,
        env="REDIS_MAX_CONNECTIONS",
        description="Redis connection pool size"
    )

    class Config:
        env_prefix = "REDIS_"


class TelegramSettings(BaseSettings):
    """Telegram Bot configuration settings."""
    
    token: str = Field(
        ...,
        env="TELEGRAM_BOT_TOKEN",
        description="Telegram Bot API token"
    )
    webhook_url: Optional[str] = Field(
        default=None,
        env="TELEGRAM_WEBHOOK_URL",
        description="Telegram webhook URL"
    )
    webhook_secret: Optional[str] = Field(
        default=None,
        env="TELEGRAM_WEBHOOK_SECRET",
        description="Telegram webhook secret"
    )
    admin_ids: str = Field(
        default="",
        env="TELEGRAM_ADMIN_IDS",
        description="Comma-separated list of admin user IDs"
    )

    def get_admin_ids_list(self) -> List[int]:
        """Parse admin IDs string into list of integers."""
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(',') if x.strip()]

    class Config:
        env_prefix = ""


class GoogleSettings(BaseSettings):
    """Google Services configuration settings."""
    
    credentials_file: Optional[str] = Field(
        default=None,
        env="GOOGLE_CREDENTIALS_FILE",
        description="Path to Google credentials JSON file"
    )
    drive_folder_id: Optional[str] = Field(
        default=None,
        env="GOOGLE_DRIVE_FOLDER_ID",
        description="Google Drive folder ID for uploads"
    )
    sheets_id: Optional[str] = Field(
        default=None,
        env="GOOGLE_SHEETS_ID",
        description="Google Sheets ID for logging"
    )

    class Config:
        env_prefix = "GOOGLE_"


class VideoProcessingSettings(BaseSettings):
    """Video processing configuration settings."""
    
    temp_dir: str = Field(
        default="/tmp/videos",
        env="VIDEO_TEMP_DIR",
        description="Temporary directory for video processing"
    )
    max_video_duration: int = Field(
        default=10800,  # 3 hours
        env="VIDEO_MAX_DURATION",
        description="Maximum video duration in seconds"
    )
    max_file_size: int = Field(
        default=2 * 1024 * 1024 * 1024,  # 2GB
        env="VIDEO_MAX_FILE_SIZE",
        description="Maximum file size in bytes"
    )
    output_quality: str = Field(
        default="1080p",
        env="VIDEO_OUTPUT_QUALITY",
        description="Default output quality (720p, 1080p, 4k)"
    )
    max_concurrent_tasks: int = Field(
        default=5,
        env="VIDEO_MAX_CONCURRENT_TASKS",
        description="Maximum concurrent video processing tasks"
    )

    class Config:
        env_prefix = "VIDEO_"


class CelerySettings(BaseSettings):
    """Celery configuration settings."""
    
    broker_url: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL",
        description="Celery broker URL"
    )
    result_backend: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND",
        description="Celery result backend URL"
    )
    task_serializer: str = Field(
        default="json",
        env="CELERY_TASK_SERIALIZER",
        description="Celery task serializer"
    )
    result_serializer: str = Field(
        default="json",
        env="CELERY_RESULT_SERIALIZER",
        description="Celery result serializer"
    )
    accept_content: List[str] = Field(
        default=["json"],
        env="CELERY_ACCEPT_CONTENT",
        description="Celery accepted content types"
    )
    timezone: str = Field(
        default="UTC",
        env="CELERY_TIMEZONE",
        description="Celery timezone"
    )

    class Config:
        env_prefix = "CELERY_"


class AppSettings(BaseSettings):
    """Main application settings."""
    
    # App settings
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    
    # Telegram settings
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_admin_ids: str = Field(default="", env="TELEGRAM_ADMIN_IDS")
    
    # Database settings
    database_url: str = Field(default="postgresql+asyncpg://user:password@localhost/videobot", env="DATABASE_URL")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Celery settings
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # Video processing settings
    video_temp_dir: str = Field(default="/tmp/videos", env="VIDEO_TEMP_DIR")
    video_max_duration: int = Field(default=10800, env="VIDEO_MAX_DURATION")
    video_max_file_size: int = Field(default=2147483648, env="VIDEO_MAX_FILE_SIZE")
    video_output_quality: str = Field(default="1080p", env="VIDEO_OUTPUT_QUALITY")
    video_max_concurrent_tasks: int = Field(default=3, env="VIDEO_MAX_CONCURRENT_TASKS")
    
    def get_admin_ids_list(self) -> List[int]:
        """Parse admin IDs string into list of integers."""
        if not self.telegram_admin_ids:
            return []
        return [int(x.strip()) for x in self.telegram_admin_ids.split(',') if x.strip()]

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        valid_envs = ['development', 'testing', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = AppSettings()

# Ensure temp directory exists
os.makedirs(settings.video_temp_dir, exist_ok=True)