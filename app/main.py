"""
Main application entry point for Video Bot.
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
import os
import json

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiohttp.web_app import Application
from aiogram.types import CallbackQuery

from app.config.settings import settings
from app.database.connection import db_manager
from app.bot.handlers import user_handlers


def setup_google_credentials():
    """Create Google credentials file from environment variable."""
    credentials_content = os.getenv("GOOGLE_CREDENTIALS_JSON_CONTENT")
    if credentials_content:
        credentials_path = "/app/google-credentials.json"
        try:
            with open(credentials_path, "w") as f:
                f.write(credentials_content)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            logger.info("Google credentials file created successfully from environment variable.")
        except Exception as e:
            logger.error(f"Failed to create Google credentials file: {e}")
    else:
        logger.warning("GOOGLE_CREDENTIALS_JSON_CONTENT environment variable not set. Google services may not work.")


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log") if not settings.debug else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    """
    Set up bot commands in the menu.
    
    Args:
        bot: Bot instance
    """
    from aiogram.types import BotCommand
    
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="❓ Справка и помощь"),
        BotCommand(command="stats", description="📊 Моя статистика"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("Bot commands set up successfully")


async def on_startup(bot: Bot) -> None:
    """
    Execute on bot startup.
    
    Args:
        bot: Bot instance
    """
    logger.info("Starting Video Bot...")
    
    # Initialize database
    try:
        await db_manager.init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Set up bot commands
    await setup_bot_commands(bot)
    
    # Set webhook if configured
    # Webhook setup would go here if needed
    # For now, using polling mode
    logger.info("Bot configured for polling mode")
    
    logger.info("Video Bot started successfully!")


async def on_shutdown(bot: Bot) -> None:
    """
    Execute on bot shutdown.
    
    Args:
        bot: Bot instance
    """
    logger.info("Shutting down Video Bot...")
    
    # Remove webhook (disabled for now)
    # if settings.telegram_webhook_url:
    #     await bot.delete_webhook()
    #     logger.info("Webhook removed")
    
    # Close database connections
    await db_manager.close()
    logger.info("Database connections closed")
    
    logger.info("Video Bot shut down successfully!")


def create_app() -> tuple[Bot, Dispatcher]:
    """
    Create bot and dispatcher instances.
    
    Returns:
        tuple[Bot, Dispatcher]: Bot and dispatcher instances
    """
    # Create bot with default properties
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        )
    )
    
    # Create dispatcher
    dp = Dispatcher()
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Import and include specific handlers first
    from app.bot.handlers import font_handlers, settings_handlers
    dp.include_router(font_handlers.router)
    dp.include_router(settings_handlers.router)
    
    # Include other routers
    dp.include_router(user_handlers.router)
    
    # Import and include video handlers
    from app.bot.handlers import video_handlers
    dp.include_router(video_handlers.router)
    
    # Register a handler for unknown callbacks LAST
    # This handler should be more specific to avoid catching handled callbacks
    @dp.callback_query(lambda c: c.data and not any([
        c.data.startswith("menu:"),
        c.data.startswith("video:"),
        c.data.startswith("vtask:"),
        c.data.startswith("settings:"),
        c.data.startswith("setval:"),
        c.data.startswith("font:"),
        c.data.startswith("style:")
    ]))
    async def handle_unknown_callback(callback: CallbackQuery) -> None:
        """
        Handle unknown callback queries globally.
        
        Args:
            callback: Callback query
        """
        logger.warning(f"Unknown callback caught in dispatcher: {callback.data}")
        await callback.answer("❌ Неизвестная команда", show_alert=True)

    return bot, dp


async def main_polling() -> None:
    """
    Run bot in polling mode.
    """
    logger.info("Starting bot in polling mode...")
    
    bot, dp = create_app()
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


def create_webhook_app() -> Application:
    """
    Create aiohttp application for webhook mode.
    
    Returns:
        Application: aiohttp application
    """
    bot, dp = create_app()
    
    # Create aiohttp application
    app = web.Application()
    
    # Create request handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        # secret_token=settings.telegram_webhook_secret,
    )
    
    # Register webhook handler
    webhook_requests_handler.register(app, path="/webhook")
    
    # Setup application
    setup_application(app, dp, bot=bot)
    
    return app


async def main_webhook() -> None:
    """
    Run bot in webhook mode.
    """
    logger.info("Starting bot in webhook mode...")
    
    app = create_webhook_app()
    
    # Run aiohttp server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    
    logger.info("Webhook server started on port 8000")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    finally:
        await runner.cleanup()


async def main() -> None:
    """
    Main application entry point.
    """
    # Create Google credentials file at startup
    setup_google_credentials()
    
    # For now, always use polling mode
    await main_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1) 