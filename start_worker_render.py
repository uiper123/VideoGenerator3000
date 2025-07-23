#!/usr/bin/env python3
"""
Render Celery Worker startup script
"""
import os
import sys
import logging
import subprocess
from pathlib import Path

# Add app to Python path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def setup_worker_environment():
    """Setup environment for Celery Worker"""
    logger.info("🔧 Setting up Celery Worker environment...")
    
    # Create necessary directories
    directories = ['/tmp/videos', '/tmp/processed', '/app/logs', '/app/temp']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Setup Google credentials
    google_creds = os.getenv('GOOGLE_CREDENTIALS_JSON_CONTENT')
    if google_creds:
        creds_path = '/app/google-credentials.json'
        try:
            with open(creds_path, 'w') as f:
                f.write(google_creds)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
            logger.info("✅ Google credentials configured for worker")
        except Exception as e:
            logger.error(f"❌ Failed to setup Google credentials: {e}")
    
    # Verify required environment variables
    required_vars = ['DATABASE_URL', 'REDIS_URL', 'CELERY_BROKER_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    logger.info("✅ Worker environment setup completed")
    return True

def main():
    """Main function for Celery Worker"""
    logger.info("🔧 Starting Celery Worker on Render...")
    
    # Setup environment
    if not setup_worker_environment():
        logger.error("❌ Worker environment setup failed")
        sys.exit(1)
    
    # Start Celery Worker
    try:
        cmd = [
            sys.executable, '-m', 'celery',
            '-A', 'app.workers.celery_app',
            'worker',
            '--loglevel=info',
            '--concurrency=1',
            '--max-tasks-per-child=10',
            '--time-limit=3600',
            '--soft-time-limit=3000'
        ]
        
        logger.info(f"🚀 Starting Celery Worker: {' '.join(cmd)}")
        
        # Run Celery Worker
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        logger.info("👋 Celery Worker stopped by user")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Celery Worker failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()