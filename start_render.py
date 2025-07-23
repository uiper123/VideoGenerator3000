#!/usr/bin/env python3
"""
Render startup script for VideoGenerator3000
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add app to Python path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

# Configure logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def setup_render_environment():
    """Setup environment for Render deployment"""
    logger.info("🚀 Setting up Render environment...")
    
    # Create necessary directories
    directories = ['/tmp/videos', '/tmp/processed', '/app/logs', '/app/temp']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created directory: {directory}")
    
    # Setup Google credentials from environment
    google_creds = os.getenv('GOOGLE_CREDENTIALS_JSON_CONTENT')
    if google_creds:
        creds_path = '/app/google-credentials.json'
        try:
            with open(creds_path, 'w') as f:
                f.write(google_creds)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
            logger.info("✅ Google credentials configured")
        except Exception as e:
            logger.error(f"❌ Failed to setup Google credentials: {e}")
    else:
        logger.warning("⚠️ GOOGLE_CREDENTIALS_JSON_CONTENT not set")
    
    # Verify required environment variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL',
        'REDIS_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ Environment setup completed")
    return True

async def init_database():
    """Initialize database for Render"""
    try:
        from app.database.connection import init_database
        await init_database()
        logger.info("✅ Database initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

async def main():
    """Main function for Render deployment"""
    logger.info("🎬 Starting VideoGenerator3000 on Render...")
    
    # Setup environment
    if not setup_render_environment():
        logger.error("❌ Environment setup failed")
        sys.exit(1)
    
    # Initialize database
    if not await init_database():
        logger.error("❌ Database initialization failed")
        sys.exit(1)
    
    # Import and start the main application
    try:
        from app.main import main as app_main
        logger.info("✅ Starting main application...")
        await app_main()
    except Exception as e:
        logger.error(f"❌ Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Application stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)