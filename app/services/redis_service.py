"""
Redis service for caching and locking.
"""
import redis.asyncio as redis
from app.config.settings import settings

# Create an asynchronous Redis client instance
redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True
)

async def check_redis_connection():
    """
    Check if the connection to Redis is successful.
    """
    try:
        await redis_client.ping()
        print("Successfully connected to Redis.")
        return True
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return False 