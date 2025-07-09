#!/usr/bin/env python3
"""
Simple script to run the Video Bot for testing.
"""
import asyncio
import sys
import os
import base64

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.main import main

if __name__ == "__main__":
    print("🚀 Starting Video Bot...")
    print("Press Ctrl+C to stop the bot")
    
    try:
        # --- Автоматическое создание token.pickle из переменной окружения ---
        b64_token = os.getenv("GOOGLE_OAUTH_TOKEN_BASE64")
        if b64_token:
            with open("token.pickle", "wb") as f:
                f.write(base64.b64decode(b64_token))
            print("[INFO] token.pickle создан из переменной окружения GOOGLE_OAUTH_TOKEN_BASE64")
        # --- конец блока ---

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 