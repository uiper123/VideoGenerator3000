"""
Configuration settings for the Video Bot application.
Uses Pydantic Settings for validation and environment variable management.
"""
import os
from typing import Optional, List
from pydantic import Field, field_validator, SecretStr
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
    telegram_bot_token: SecretStr = Field(..., env="TELEGRAM_BOT_TOKEN")
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
    
    # Google API settings
    google_credentials_path: str = "google-credentials.json"
    google_spreadsheet_id: Optional[str] = Field(default=None, env="GOOGLE_SPREADSHEET_ID")
    
    # OAuth 2.0 settings for personal Google Drive
    google_oauth_client_id: Optional[str] = Field(default=None, env="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: Optional[str] = Field(default=None, env="GOOGLE_OAUTH_CLIENT_SECRET")

    # YouTube Download
    youtube_cookies_file_path: Optional[str] = Field(None, env="YOUTUBE_COOKIES_FILE_PATH")
    youtube_cookies_content: Optional[str] = Field(None, env="YOUTUBE_COOKIES_CONTENT")

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

def ensure_cookies_file():
    """Создаёт cookies-файл по пути 'app/youtube_cookies.txt' (жёстко), чтобы избежать ошибок с директориями."""
    cookies_content = settings.youtube_cookies_content or '''# Netscape HTTP Cookie File
# This file is generated by yt-dlp.  Do not edit.

.youtube.com	TRUE	/	TRUE	1785477094	LOGIN_INFO	AFmmF2swRQIhAMuQMpHKUaalEdFk9qh7-fuxzb4QzMtfnsssVh5yf13uAiBzeTdMS4FEgpXituPzqFF_9fFIBnOnAI18L26Ccl3Uvg:QUQ3MjNmeHdzRk1PMnIzR2lkTkRDdndvc2RhOFRPQm1aZkhGbGZyb3JmaDVsendkQ1ZfM1hFLUhpNmFqOVI4M3hJdXBONVFxbzhRQ3d1b2NielVZZndyWEhTNk5HckxPSWlPYmRyTXBTZnZOV1dERTM3anFtZFZuelBEZ1BPZGJWbDhrcWRtcHVkY09acFE2NFl2Q2V1SWY2QmExTU51WGtB
.youtube.com	TRUE	/	FALSE	1786015076	HSID	APDA7JIdS3yEAFtvg
.youtube.com	TRUE	/	TRUE	1786015076	SSID	Ahg_EIpAXnv60efVB
.youtube.com	TRUE	/	FALSE	1786015076	APISID	W9DLiDyNDutbedhD/AIPWk-OQM0hJSBJ3B
.youtube.com	TRUE	/	TRUE	1786015076	SAPISID	_0fmFVTUn0L867qR/AiEfKw_VI9I7wbjWS
.youtube.com	TRUE	/	TRUE	1786015076	__Secure-1PAPISID	_0fmFVTUn0L867qR/AiEfKw_VI9I7wbjWS
.youtube.com	TRUE	/	TRUE	1786015076	__Secure-3PAPISID	_0fmFVTUn0L867qR/AiEfKw_VI9I7wbjWS
.youtube.com	TRUE	/	FALSE	1786015076	SID	g.a000ywiwmJnA8stOzLJxp3XC5z3wXYZfwz9GmzG00-Wzjcmn_oHDKKCO9IgwtA0qi_pC3X2AuwACgYKAeESARASFQHGX2Mi1Cc4vDe4hSTEZMhW50KAbRoVAUF8yKqV52QsEdeANmBR3aKMEjba0076
.youtube.com	TRUE	/	TRUE	1786015076	__Secure-1PSID	g.a000ywiwmJnA8stOzLJxp3XC5z3wXYZfwz9GmzG00-Wzjcmn_oHDias_SA8h0TUk-ui3xyBv0gACgYKAdYSARASFQHGX2MiY49fnfARrcQQgUBYNL2LRBoVAUF8yKq0PopeSz-eSrt_e3_tc_P-0076
.youtube.com	TRUE	/	TRUE	1786015076	__Secure-3PSID	g.a000ywiwmJnA8stOzLJxp3XC5z3wXYZfwz9GmzG00-Wzjcmn_oHDmtkMPsTQoZNulYC0lYDBuQACgYKAbwSARASFQHGX2MiOSKEHRSVw5YHFWGAeXPh1RoVAUF8yKoBefDTmfPSs5ldZVzFHJKf0076
.youtube.com	TRUE	/	FALSE	0	PREF	tz=UTC&f6=40000000&f7=100&f5=30000&f4=4000000&hl=en
.youtube.com	TRUE	/	TRUE	1779025338	__Secure-YEC	CgttV2c0dk1RVEZmRSi0xanDBjIKCgJSVRIEGgAgDQ%3D%3D
.youtube.com	TRUE	/	TRUE	1783525316	__Secure-1PSIDTS	sidts-CjIB5H03P1L0UFp2LRa0uZWkjscR7SNvq3SijGsAb2CeBdaWAbHDN7O_RrKiu_jbXQAREBAA
.youtube.com	TRUE	/	TRUE	1783525316	__Secure-3PSIDTS	sidts-CjIB5H03P1L0UFp2LRa0uZWkjscR7SNvq3SijGsAb2CeBdaWAbHDN7O_RrKiu_jbXQAREBAA
.youtube.com	TRUE	/	FALSE	1783525881	SIDCC	AKEyXzVO6aO3All-T0Nmuihh8SoDObCbzloQBtAzYqt0QJn7ryarB0P3hvfjP3U23S6soIGi6Q
.youtube.com	TRUE	/	TRUE	1783525881	__Secure-1PSIDCC	AKEyXzWQwlAry0jvWs0UZPCrdmXFW-_zEzrS3Ss0-T8KF6FRYWGIHFiQm_S9CcUi2ccT66d2Tw
.youtube.com	TRUE	/	TRUE	1783525881	__Secure-3PSIDCC	AKEyXzXQXTr4gZQJmcia4AlXrd9RQwSRMtQ-xHFPB-RH0o6EJBHVE5_gCpoaI0zjNbphTn3GRJ0
.youtube.com	TRUE	/	TRUE	1753199287	hideBrowserUpgradeBox	true
.youtube.com	TRUE	/	TRUE	0	YSC	s2u2cm4sCPc
.youtube.com	TRUE	/	TRUE	1767541761	__Secure-ROLLOUT_TOKEN	CLi7ofeLmtX_GhCP7uyXzq2OAxiWupu7zq2OAw%3D%3D
.youtube.com	TRUE	/	TRUE	1767541879	VISITOR_INFO1_LIVE	PAqcjn52fmY
.youtube.com	TRUE	/	TRUE	1767541879	VISITOR_PRIVACY_METADATA	CgJSVRIEGgAgGQ%3D%3D
.youtube.com	TRUE	/	TRUE	1815061879	__Secure-YT_TVFAS	t=486663&s=2
.youtube.com	TRUE	/	TRUE	1767541879	DEVICE_INFO	ChxOelV5TkRjek9USXpORGN6TlRVeU5EY3hOUT09EPf8tMMGGPf8tMMG
.youtube.com	TRUE	/tv	TRUE	1784821879	__Secure-YT_DERP	CKKun84K
'''
    path = "app/youtube_cookies.txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cookies_content)
    os.chmod(path, 0o600)
    print(f"Cookies file created at {path}")

# Ensure cookies file exists if content is provided
ensure_cookies_file()