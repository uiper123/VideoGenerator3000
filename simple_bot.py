#!/usr/bin/env python3
"""
Simplified Video Bot for testing without database.
"""
import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
    exit(1)

# Create bot and dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_handler(message: Message):
    """Handle /start command."""
    await message.answer(
        "🎬 <b>Добро пожаловать в VideoGenerator3000!</b>\n\n"
        "Этот бот поможет вам обрабатывать видео.\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Справка\n"
        "/status - Статус бота\n\n"
        "📹 Отправьте мне видео или ссылку на YouTube для обработки!"
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    """Handle /help command."""
    await message.answer(
        "❓ <b>Справка по использованию бота</b>\n\n"
        "🎥 <b>Как использовать:</b>\n"
        "1. Отправьте видео файл или ссылку на YouTube\n"
        "2. Бот автоматически обработает видео\n"
        "3. Получите готовый результат\n\n"
        "⚙️ <b>Возможности:</b>\n"
        "• Конвертация в формат Shorts (9:16)\n"
        "• Автоматические субтитры\n"
        "• Оптимизация для социальных сетей\n\n"
        "❗ <b>Примечание:</b> Это упрощенная версия для тестирования."
    )


@dp.message(Command("status"))
async def status_handler(message: Message):
    """Handle /status command."""
    await message.answer(
        "✅ <b>Статус бота</b>\n\n"
        "🟢 Бот работает\n"
        "🔧 Режим: Упрощенный (без базы данных)\n"
        "📊 Версия: 1.0.0-simple\n\n"
        "Для полной функциональности установите Docker и запустите полную версию."
    )


@dp.message()
async def message_handler(message: Message):
    """Handle all other messages."""
    if message.video:
        await message.answer(
            "🎬 Получено видео!\n\n"
            "⚠️ <b>Внимание:</b> Это упрощенная версия бота.\n"
            "Обработка видео пока недоступна.\n\n"
            "Для полной функциональности:\n"
            "1. Установите Docker\n"
            "2. Запустите: <code>docker-compose up -d</code>"
        )
    elif message.text and ("youtube.com" in message.text or "youtu.be" in message.text):
        await message.answer(
            "🔗 Получена ссылка на YouTube!\n\n"
            "⚠️ <b>Внимание:</b> Это упрощенная версия бота.\n"
            "Скачивание с YouTube пока недоступно.\n\n"
            "Для полной функциональности:\n"
            "1. Установите Docker\n"
            "2. Запустите: <code>docker-compose up -d</code>"
        )
    else:
        await message.answer(
            "🤖 Привет! Я VideoGenerator3000.\n\n"
            "Отправьте мне:\n"
            "📹 Видео файл\n"
            "🔗 Ссылку на YouTube\n"
            "❓ /help для справки"
        )


async def main():
    """Main function."""
    logger.info("🚀 Starting VideoGenerator3000 (Simple Mode)...")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())