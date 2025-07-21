#!/usr/bin/env python3
"""
Video Bot with basic video processing functionality.
"""
import asyncio
import logging
import os
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
import yt_dlp

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

# Create temp directory for video processing
TEMP_DIR = Path(tempfile.gettempdir()) / "videobot"
TEMP_DIR.mkdir(exist_ok=True)


def convert_to_shorts(input_path: str, output_path: str, duration_limit: int = 60) -> bool:
    """
    Convert video to vertical format (9:16) for Shorts.
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        duration_limit: Maximum duration in seconds (default 60 for Shorts)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # FFmpeg command to convert to 9:16 format with duration limit
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
            '-c:a', 'aac',  # Re-encode audio for better compatibility
            '-b:a', '128k',  # Audio bitrate
            '-c:v', 'libx264',  # Video codec
            '-crf', '23',  # Quality setting (lower = better quality)
            '-preset', 'medium',  # Encoding speed vs compression
            '-t', str(duration_limit),  # Limit duration
            '-y',  # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Successfully converted video: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error converting video: {e}")
        return False


def get_video_info(input_path: str) -> dict:
    """
    Get video information using FFprobe.
    
    Args:
        input_path: Path to input video
        
    Returns:
        dict: Video information
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            input_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        else:
            return {}
            
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {}


def download_youtube_video(url: str, output_path: str) -> bool:
    """
    Download video from YouTube with multiple fallback strategies.
    
    Args:
        url: YouTube URL
        output_path: Path to save video
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Try multiple format strategies
    format_strategies = [
        'best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]',
        'best[height<=720]/best[height<=480]/best[height<=360]',
        'worst[height>=360]/worst',
        'best/worst'
    ]
    
    for i, format_selector in enumerate(format_strategies):
        try:
            logger.info(f"Trying format strategy {i+1}: {format_selector}")
            
            ydl_opts = {
                'outtmpl': output_path,
                'format': format_selector,
                'noplaylist': True,
                'extractaudio': False,
                'ignoreerrors': False,
                'no_warnings': False,
                'retries': 3,
                'fragment_retries': 3,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to check if video is available
                info = ydl.extract_info(url, download=False)
                if not info:
                    logger.error("Failed to extract video information")
                    continue
                
                logger.info(f"Video title: {info.get('title', 'Unknown')}")
                logger.info(f"Video duration: {info.get('duration', 0)} seconds")
                
                # Check available formats
                formats = info.get('formats', [])
                if not formats:
                    logger.error("No formats available for this video")
                    continue
                
                logger.info(f"Available formats: {len(formats)}")
                
                # Now download
                ydl.download([url])
                
                # Check if file actually exists after download
                import glob
                base_path = output_path.replace('.%(ext)s', '')
                downloaded_files = glob.glob(f"{base_path}.*")
                
                if not downloaded_files:
                    logger.error("No files found after download")
                    continue
                
                # Check if the downloaded file has content
                downloaded_file = downloaded_files[0]
                if not os.path.exists(downloaded_file) or os.path.getsize(downloaded_file) == 0:
                    logger.error(f"Downloaded file is empty or doesn't exist: {downloaded_file}")
                    continue
                
                logger.info(f"Successfully downloaded video: {downloaded_file}")
                return True
                
        except Exception as e:
            logger.warning(f"Format strategy {i+1} failed: {e}")
            continue
    
    # If all strategies failed, try one more time with very basic options
    try:
        logger.info("Trying final fallback with basic options...")
        
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best',
            'noplaylist': True,
            'ignoreerrors': True,  # Allow errors for final attempt
            'no_warnings': True,
            'retries': 1,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            import glob
            base_path = output_path.replace('.%(ext)s', '')
            downloaded_files = glob.glob(f"{base_path}.*")
            
            if downloaded_files and os.path.exists(downloaded_files[0]) and os.path.getsize(downloaded_files[0]) > 0:
                logger.info(f"Final fallback succeeded: {downloaded_files[0]}")
                return True
                
    except Exception as e:
        logger.error(f"Final fallback also failed: {e}")
    
    logger.error("All download strategies failed")
    return False


@dp.message(Command("start"))
async def start_handler(message: Message):
    """Handle /start command."""
    await message.answer(
        "🎬 <b>Добро пожаловать в VideoGenerator3000!</b>\n\n"
        "Этот бот поможет вам обрабатывать видео для Shorts.\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Справка\n"
        "/status - Статус бота\n\n"
        "📹 <b>Что я умею:</b>\n"
        "• Конвертировать видео в формат 9:16 (Shorts)\n"
        "• Скачивать видео с YouTube\n"
        "• Обрезать и масштабировать видео\n\n"
        "Отправьте мне видео или ссылку на YouTube!"
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    """Handle /help command."""
    await message.answer(
        "❓ <b>Справка по использованию бота</b>\n\n"
        "🎥 <b>Как использовать:</b>\n"
        "1. Отправьте видео файл или ссылку на YouTube\n"
        "2. Бот автоматически конвертирует в формат 9:16\n"
        "3. Получите готовый результат для Shorts\n\n"
        "⚙️ <b>Поддерживаемые форматы:</b>\n"
        "• MP4, AVI, MOV, MKV\n"
        "• YouTube ссылки\n\n"
        "📐 <b>Выходной формат:</b>\n"
        "• Разрешение: 1080x1920 (9:16)\n"
        "• Формат: MP4\n"
        "• Качество: Оптимизировано для Shorts"
    )


@dp.message(Command("status"))
async def status_handler(message: Message):
    """Handle /status command."""
    await message.answer(
        "✅ <b>Статус бота</b>\n\n"
        "🟢 Бот работает\n"
        "🔧 Режим: Базовая обработка видео\n"
        "📊 Версия: 1.0.0-basic\n"
        "🎬 FFmpeg: Установлен\n"
        "📥 YouTube: Поддерживается\n\n"
        "Готов к обработке видео!"
    )


@dp.message()
async def message_handler(message: Message):
    """Handle all other messages."""
    if message.video:
        await process_video_file(message)
    elif message.text and ("youtube.com" in message.text or "youtu.be" in message.text):
        await process_youtube_url(message)
    else:
        await message.answer(
            "🤖 Привет! Я VideoGenerator3000.\n\n"
            "Отправьте мне:\n"
            "📹 Видео файл\n"
            "🔗 Ссылку на YouTube\n"
            "❓ /help для справки"
        )


async def process_video_file(message: Message):
    """Process uploaded video file."""
    try:
        # Send processing message
        processing_msg = await message.answer("🔄 Обрабатываю видео...")
        
        # Get file info
        file_info = await bot.get_file(message.video.file_id)
        
        # Create unique filenames
        input_filename = f"input_{message.message_id}.mp4"
        output_filename = f"output_{message.message_id}.mp4"
        
        input_path = TEMP_DIR / input_filename
        output_path = TEMP_DIR / output_filename
        
        # Download file
        await bot.download_file(file_info.file_path, input_path)
        
        # Convert to shorts format
        await processing_msg.edit_text("🎬 Конвертирую в формат Shorts...")
        
        success = convert_to_shorts(str(input_path), str(output_path))
        
        if success and output_path.exists():
            # Send processed video
            await processing_msg.edit_text("📤 Отправляю результат...")
            
            video_file = FSInputFile(str(output_path))
            await message.answer_video(
                video_file,
                caption="✅ <b>Видео готово!</b>\n\n"
                       "📐 Формат: 1080x1920 (9:16)\n"
                       "🎯 Оптимизировано для Shorts"
            )
            
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(
                "❌ <b>Ошибка обработки</b>\n\n"
                "Не удалось конвертировать видео.\n"
                "Попробуйте другой файл."
            )
        
        # Cleanup
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()
            
    except Exception as e:
        logger.error(f"Error processing video file: {e}")
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Произошла ошибка при обработке видео.\n"
            "Попробуйте еще раз."
        )


async def process_youtube_url(message: Message):
    """Process YouTube URL."""
    try:
        # Send processing message
        processing_msg = await message.answer("📥 Скачиваю видео с YouTube...")
        
        # Create unique filenames
        download_filename = f"download_{message.message_id}.%(ext)s"
        output_filename = f"output_{message.message_id}.mp4"
        
        download_path = str(TEMP_DIR / download_filename)
        output_path = TEMP_DIR / output_filename
        
        # Download from YouTube
        success = download_youtube_video(message.text, download_path)
        
        if not success:
            await processing_msg.edit_text(
                "❌ <b>Ошибка скачивания</b>\n\n"
                "Не удалось скачать видео с YouTube.\n"
                "Проверьте ссылку и попробуйте еще раз."
            )
            return
        
        # Find downloaded file
        downloaded_files = list(TEMP_DIR.glob(f"download_{message.message_id}.*"))
        if not downloaded_files:
            await processing_msg.edit_text("❌ Файл не найден после скачивания")
            return
            
        input_path = downloaded_files[0]
        
        # Convert to shorts format
        await processing_msg.edit_text("🎬 Конвертирую в формат Shorts...")
        
        success = convert_to_shorts(str(input_path), str(output_path))
        
        if success and output_path.exists():
            # Send processed video
            await processing_msg.edit_text("📤 Отправляю результат...")
            
            video_file = FSInputFile(str(output_path))
            await message.answer_video(
                video_file,
                caption="✅ <b>Видео готово!</b>\n\n"
                       "📐 Формат: 1080x1920 (9:16)\n"
                       "🎯 Оптимизировано для Shorts\n"
                       "📥 Источник: YouTube"
            )
            
            await processing_msg.delete()
        else:
            await processing_msg.edit_text(
                "❌ <b>Ошибка обработки</b>\n\n"
                "Не удалось конвертировать видео.\n"
                "Попробуйте другую ссылку."
            )
        
        # Cleanup
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()
            
    except Exception as e:
        logger.error(f"Error processing YouTube URL: {e}")
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Произошла ошибка при обработке YouTube ссылки.\n"
            "Попробуйте еще раз."
        )


async def main():
    """Main function."""
    logger.info("🚀 Starting VideoGenerator3000 (Video Processing Mode)...")
    
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