#!/usr/bin/env python3
"""
VideoGenerator3000 - Google Colab Version
Полная версия бота с базой данных, Celery и всеми возможностями
"""

import os
import sys
import asyncio
import logging
import subprocess
import threading
import time
from pathlib import Path

# Add current directory to Python path
sys.path.append('/content/videobot')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/content/videobot/logs/bot.log')
    ]
)
logger = logging.getLogger(__name__)

def start_services():
    """Start required services"""
    print("🚀 Starting services...")
    
    # Start PostgreSQL
    subprocess.run(["service", "postgresql", "start"], check=False)
    time.sleep(2)
    
    # Start Redis
    subprocess.run(["service", "redis-server", "start"], check=False)
    time.sleep(2)
    
    # Check services
    try:
        subprocess.run(["pg_isready", "-h", "localhost", "-p", "5432"], check=True)
        print("✅ PostgreSQL is ready")
    except subprocess.CalledProcessError:
        print("❌ PostgreSQL failed to start")
    
    try:
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True)
        if result.stdout.strip() == "PONG":
            print("✅ Redis is ready")
        else:
            print("❌ Redis failed to start")
    except:
        print("❌ Redis failed to start")

def start_celery_worker():
    """Start Celery worker in background"""
    def run_worker():
        os.chdir('/content/videobot')
        os.system('celery -A app.workers.celery_app worker --loglevel=info --concurrency=1')
    
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()
    print("🔄 Celery worker started in background")

def setup_database():
    """Initialize database"""
    print("🗄️ Setting up database...")
    
    try:
        # Import after path is set
        from app.database.connection import init_db
        asyncio.run(init_db())
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database setup failed: {e}")

async def main():
    """Main function to run the bot"""
    print("🎬 Starting VideoGenerator3000...")
    
    # Start services
    start_services()
    
    # Setup database
    setup_database()
    
    # Start Celery worker
    start_celery_worker()
    
    # Wait a bit for services to stabilize
    await asyncio.sleep(3)
    
    # Import and start bot
    try:
        from app.main import main as bot_main
        await bot_main()
    except ImportError as e:
        print(f"❌ Failed to import bot: {e}")
        print("📁 Make sure all app files are uploaded to /content/videobot/app/")
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")
        logger.exception("Bot startup error")

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment...")
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_ADMIN_IDS',
        'DATABASE_URL',
        'REDIS_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f'YOUR_{var}_HERE':
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please update /content/videobot/.env file")
        return False
    
    print("✅ Environment variables configured")
    return True

def show_instructions():
    """Show usage instructions"""
    print("\n" + "=" * 60)
    print("🎬 VideoGenerator3000 - Google Colab Edition")
    print("=" * 60)
    print("\n📋 Instructions:")
    print("1. Run setup: !python /content/videobot/colab_setup.py")
    print("2. Upload your app/ folder to /content/videobot/")
    print("3. Update .env file with your bot token")
    print("4. Run this script: !python /content/videobot/colab_videobot.py")
    print("\n⚠️ Important notes:")
    print("- Colab sessions are temporary (12-24 hours)")
    print("- All data will be lost when session ends")
    print("- Consider backing up to Google Drive")
    print("\n🔗 Useful commands:")
    print("- Check logs: !tail -f /content/videobot/logs/bot.log")
    print("- Restart services: !bash /content/videobot/start_services.sh")
    print("- Check processes: !ps aux | grep -E '(celery|python)'")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('/content/videobot/.env')
    
    # Check if this is first run
    if not Path('/content/videobot').exists():
        print("❌ VideoBot not found!")
        print("🔧 Run setup first: !python colab_setup.py")
        show_instructions()
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        show_instructions()
        sys.exit(1)
    
    # Run bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        logger.exception("Fatal error")