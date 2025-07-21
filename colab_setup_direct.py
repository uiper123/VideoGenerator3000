#!/usr/bin/env python3
"""
Google Colab setup script for VideoGenerator3000 - Direct Version
Создается напрямую в Colab без скачивания
"""

import os
import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description="", timeout=300):
    """Execute shell command with error handling"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()[:200]}")
            return True
        else:
            print(f"❌ {description} - Failed")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - Timeout ({timeout}s)")
        return False
    except Exception as e:
        print(f"💥 {description} - Error: {e}")
        return False

def main():
    """Main setup function"""
    print("🎬 VideoGenerator3000 - Google Colab Setup (Direct)")
    print("=" * 60)
    
    # Change to content directory
    os.chdir("/content")
    
    # 1. Update system packages
    print("\n📦 Step 1: Updating system packages...")
    run_command("apt update", "Updating package list")
    
    # 2. Install system dependencies
    print("\n🔧 Step 2: Installing system dependencies...")
    dependencies = [
        ("apt install -y ffmpeg", "Installing FFmpeg"),
        ("apt install -y postgresql postgresql-contrib", "Installing PostgreSQL"),
        ("apt install -y redis-server", "Installing Redis"),
        ("apt install -y fonts-dejavu-core fonts-liberation", "Installing fonts"),
        ("apt install -y imagemagick", "Installing ImageMagick"),
        ("apt install -y wget curl git", "Installing utilities"),
    ]
    
    for cmd, desc in dependencies:
        run_command(cmd, desc)
    
    # 3. Setup PostgreSQL
    print("\n🗄️ Step 3: Setting up PostgreSQL...")
    pg_commands = [
        ("service postgresql start", "Starting PostgreSQL service"),
        ("sudo -u postgres createuser -s root", "Creating root user"),
        ("sudo -u postgres createdb videobot", "Creating videobot database"),
        ("sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'videobot_password';\"", "Setting postgres password"),
    ]
    
    for cmd, desc in pg_commands:
        run_command(cmd, desc)
    
    # 4. Setup Redis
    print("\n🔴 Step 4: Setting up Redis...")
    redis_commands = [
        ("service redis-server start", "Starting Redis service"),
        ("redis-cli ping", "Testing Redis connection"),
    ]
    
    for cmd, desc in redis_commands:
        run_command(cmd, desc)
    
    # 5. Install Python packages
    print("\n🐍 Step 5: Installing Python packages...")
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
    ]
    
    for package in packages:
        run_command(f"pip install {package}", f"Installing {package}", timeout=120)
    
    # 6. Create directory structure
    print("\n📁 Step 6: Creating directories...")
    directories = [
        "/content/videobot",
        "/content/videobot/app",
        "/content/videobot/temp",
        "/content/videobot/logs",
        "/content/videobot/fonts",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # 7. Create .env file
    print("\n⚙️ Step 7: Creating environment file...")
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

# Video Processing Configuration
MAX_VIDEO_DURATION=3600
MAX_FILE_SIZE=1073741824
FFMPEG_TIMEOUT=1800
"""
    
    with open("/content/videobot/.env", "w") as f:
        f.write(env_content)
    print("✅ Environment file created")
    
    # 8. Download fonts
    print("\n🔤 Step 8: Downloading fonts...")
    font_commands = [
        ("wget -O /content/videobot/fonts/Roboto-Bold.ttf https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf", "Downloading Roboto Bold"),
        ("wget -O /content/videobot/fonts/Roboto-Regular.ttf https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf", "Downloading Roboto Regular"),
    ]
    
    for cmd, desc in font_commands:
        run_command(cmd, desc)
    
    # 9. Create startup script
    print("\n🚀 Step 9: Creating startup script...")
    startup_script = """#!/bin/bash
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
pg_isready -h localhost -p 5432 && echo "✅ PostgreSQL ready" || echo "❌ PostgreSQL failed"
redis-cli ping && echo "✅ Redis ready" || echo "❌ Redis failed"

echo "✅ Services started!"
"""
    
    with open("/content/videobot/start_services.sh", "w") as f:
        f.write(startup_script)
    
    run_command("chmod +x /content/videobot/start_services.sh", "Making startup script executable")
    
    # 10. Final checks
    print("\n🔍 Step 10: Final system checks...")
    checks = [
        ("ffmpeg -version | head -1", "FFmpeg version"),
        ("pg_isready -h localhost -p 5432", "PostgreSQL status"),
        ("redis-cli ping", "Redis status"),
        ("python3 --version", "Python version"),
        ("pip list | grep aiogram", "Aiogram installation"),
    ]
    
    for cmd, desc in checks:
        run_command(cmd, desc)
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETED!")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("1. Update bot token in /content/videobot/.env")
    print("2. Copy your bot code to /content/videobot/")
    print("3. Run: !bash /content/videobot/start_services.sh")
    print("4. Start your bot!")
    print("\n⚠️ Important:")
    print("- Colab sessions are temporary (12-24 hours)")
    print("- All data will be lost when session restarts")
    print("- Consider backing up important data")
    print("\n🔗 Useful paths:")
    print("- Project: /content/videobot/")
    print("- Logs: /content/videobot/logs/")
    print("- Temp: /content/videobot/temp/")
    print("- Config: /content/videobot/.env")

if __name__ == "__main__":
    main()