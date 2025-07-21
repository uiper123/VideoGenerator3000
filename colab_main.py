#!/usr/bin/env python3
"""
Main application file for Google Colab version
Упрощенная версия с адаптацией под ограничения Colab
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, '/content/videobot')
sys.path.insert(0, '/content/videobot/app')

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

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

async def main():
    """Main function to run the bot"""
    # Load environment variables
    load_dotenv('/content/videobot/.env')
    
    # Get bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ TELEGRAM_BOT_TOKEN not configured!")
        logger.error("📝 Please update /content/videobot/.env file")
        return
    
    # Create bot and dispatcher
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    try:
        # Import handlers (simplified version for Colab)
        from colab_handlers import setup_handlers
        setup_handlers(dp)
        
        # Initialize database
        from database.connection import init_db
        await init_db()
        
        logger.info("🚀 Starting VideoGenerator3000 (Colab Edition)...")
        
        # Start polling
        await dp.start_polling(bot)
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("📁 Make sure all required files are uploaded")
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")