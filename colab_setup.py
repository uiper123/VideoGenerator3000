#!/usr/bin/env python3
"""
Google Colab setup script for VideoGenerator3000
Полная версия бота с базой данных, очередями и всеми возможностями
"""

import os
import subprocess
import sys
import time
import asyncio
from pathlib import Path

def run_command(cmd, description=""):
    """Execute shell command with error handling"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return True
        else:
            print(f"❌ {description} - Failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - Timeout")
        return False
    except Exception as e:
        print(f"💥 {description} - Error: {e}")
        return False

def setup_system_dependencies():
    """Install system dependencies"""
    print("🚀 Setting up system dependencies...")
    
    commands = [
        ("apt update", "Updating package list"),
        ("apt install -y ffmpeg", "Installing FFmpeg"),
        ("apt install -y postgresql postgresql-contrib", "Installing PostgreSQL"),
        ("apt install -y redis-server", "Installing Redis"),
        ("apt install -y fonts-dejavu-core fonts-liberation", "Installing fonts"),
        ("apt install -y imagemagick", "Installing ImageMagick"),
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            print(f"⚠️ Warning: {desc} failed, continuing...")

def setup_postgresql():
    """Setup PostgreSQL database"""
    print("🗄️ Setting up PostgreSQL...")
    
    commands = [
        ("service postgresql start", "Starting PostgreSQL"),
        ("sudo -u postgres createuser -s root", "Creating root user"),
        ("sudo -u postgres createdb videobot", "Creating database"),
        ("sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'videobot_password';\"", "Setting password"),
    ]
    
    for cmd, desc in commands:
        run_command(cmd, desc)

def setup_redis():
    """Setup Redis server"""
    print("🔴 Setting up Redis...")
    
    commands = [
        ("service redis-server start", "Starting Redis server"),
        ("redis-cli ping", "Testing Redis connection"),
    ]
    
    for cmd, desc in commands:
        run_command(cmd, desc)

def install_python_dependencies():
    """Install Python packages"""
    print("🐍 Installing Python dependencies...")
    
    # Core dependencies
    packages = [
        "aiogram==3.4.1",
        "asyncpg",
        "sqlalchemy[asyncio]",
        "alembic",
        "celery[redis]",
        "redis",
        "yt-dlp",
        "pytubefix",
        "ffmpeg-python",
        "pillow",
        "opencv-python",
        "numpy",
        "requests",
        "aiohttp",
        "aiofiles",
        "python-dotenv",
        "pydantic",
        "pydantic-settings",
        "fastapi",
        "uvicorn",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "gspread",
        "oauth2client",
    ]
    
    for package in packages:
        run_command(f"pip install {package}", f"Installing {package}")

def create_directory_structure():
    """Create necessary directories"""
    print("📁 Creating directory structure...")
    
    directories = [
        "/content/videobot/app",
        "/content/videobot/app/bot",
        "/content/videobot/app/bot/handlers",
        "/content/videobot/app/bot/keyboards",
        "/content/videobot/app/config",
        "/content/videobot/app/database",
        "/content/videobot/app/services",
        "/content/videobot/app/video_processing",
        "/content/videobot/app/workers",
        "/content/videobot/fonts",
        "/content/videobot/temp",
        "/content/videobot/logs",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")

def create_env_file():
    """Create environment configuration"""
    print("⚙️ Creating environment configuration...")
    
    env_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_ADMIN_IDS=YOUR_ADMIN_ID_HERE

# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:videobot_password@localhost:5432/videobot

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Application Configuration
DEBUG=true
LOG_LEVEL=INFO
TEMP_DIR=/content/videobot/temp
FONTS_DIR=/content/videobot/fonts

# Google Drive Configuration (optional)
GOOGLE_CREDENTIALS_PATH=/content/videobot/google-credentials.json
GOOGLE_DRIVE_FOLDER_ID=YOUR_DRIVE_FOLDER_ID

# Video Processing Configuration
MAX_VIDEO_DURATION=3600
MAX_FILE_SIZE=2147483648
FFMPEG_TIMEOUT=1800
"""
    
    with open("/content/videobot/.env", "w") as f:
        f.write(env_content)
    
    print("✅ Environment file created at /content/videobot/.env")
    print("⚠️ Don't forget to update TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_IDS!")

def download_fonts():
    """Download necessary fonts"""
    print("🔤 Downloading fonts...")
    
    font_urls = [
        ("https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf", "Roboto-Bold.ttf"),
        ("https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf", "Roboto-Regular.ttf"),
    ]
    
    for url, filename in font_urls:
        run_command(f"wget -O /content/videobot/fonts/{filename} {url}", f"Downloading {filename}")

def create_startup_script():
    """Create startup script for services"""
    print("🚀 Creating startup script...")
    
    startup_script = """#!/bin/bash
# VideoGenerator3000 Startup Script for Google Colab

echo "🚀 Starting VideoGenerator3000 services..."

# Start PostgreSQL
echo "🗄️ Starting PostgreSQL..."
service postgresql start
sleep 2

# Start Redis
echo "🔴 Starting Redis..."
service redis-server start
sleep 2

# Check services
echo "🔍 Checking services..."
pg_isready -h localhost -p 5432 && echo "✅ PostgreSQL is ready" || echo "❌ PostgreSQL failed"
redis-cli ping && echo "✅ Redis is ready" || echo "❌ Redis failed"

echo "✅ All services started!"
"""
    
    with open("/content/videobot/start_services.sh", "w") as f:
        f.write(startup_script)
    
    run_command("chmod +x /content/videobot/start_services.sh", "Making startup script executable")

def main():
    """Main setup function"""
    print("🎬 VideoGenerator3000 - Google Colab Setup")
    print("=" * 50)
    
    # Change to content directory
    os.chdir("/content")
    
    # Setup system
    setup_system_dependencies()
    setup_postgresql()
    setup_redis()
    
    # Setup Python environment
    install_python_dependencies()
    
    # Create project structure
    create_directory_structure()
    create_env_file()
    download_fonts()
    create_startup_script()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Update /content/videobot/.env with your bot token")
    print("2. Upload your project files to /content/videobot/")
    print("3. Run: !bash /content/videobot/start_services.sh")
    print("4. Run your bot!")
    print("\n⚠️ Remember: Colab sessions are temporary!")
    print("💡 Consider using Google Drive to backup your data")

if __name__ == "__main__":
    main()