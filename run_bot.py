#!/usr/bin/env python3
"""
Simple script to run the Video Bot for testing.
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.main import main

if __name__ == "__main__":
    print("🚀 Starting Video Bot...")
    print("Press Ctrl+C to stop the bot")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 