#!/usr/bin/env python3
"""
Simplified handlers for Google Colab version
Основные обработчики с адаптацией под Colab
"""

import os
import logging
import tempfile
import subprocess
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import yt_dlp

logger = logging.getLogger(__name__)

# Create temp directory
TEMP_DIR = Path("/content/videobot/temp")
TEMP_DIR.mkdir(exist_ok=True)

def setup_handlers(dp):
    """Setup all handlers"""
    router = Router()
    
    @router.message(Command("start"))
    async def start_handler(message: Message):
        """Handle /start command"""
        await message.answer(
            "🎬 <b>VideoGenerator3000 - Colab Edition</b>\n\n"
            "Добро пожаловать! Этот бот работает в Google Colab.\n\n"
            "📋 <b>Возможности:</b>\n"
            "• Скачивание видео с YouTube\n"
            "• Конвертация в формат Shorts (9:16)\n"
            "• Обработка загруженных файлов\n\n"
            "📹 <b>Как использовать:</b>\n"
            "Отправьте ссылку на YouTube или загрузите видео файл\n\n"
            "⚠️ <b>Ограничения Colab:</b>\n"
            "• Сессия живет 12-24 часа\n"
            "• Ограниченные ресурсы\n"
            "• Временное хранилище"
        )
    
    @router.message(Command("status"))
    async def status_handler(message: Message):
        """Handle /status command"""
        # Check services
        pg_status = "✅" if os.system("pg_isready -h localhost -p 5432") == 0 else "❌"
        redis_status = "✅" if os.system("redis-cli ping > /dev/null 2>&1") == 0 else "❌"
        
        # Check disk space
        disk_usage = subprocess.run(["df", "-h", "/content"], capture_output=True, text=True)
        disk_info = disk_usage.stdout.split('\n')[1] if disk_usage.returncode == 0 else "Unknown"
        
        await message.answer(
            f"📊 <b>Статус системы</b>\n\n"
            f"🗄️ PostgreSQL: {pg_status}\n"
            f"🔴 Redis: {redis_status}\n"
            f"💾 Диск: {disk_info.split()[3] if disk_info != 'Unknown' else 'Unknown'} свободно\n"
            f"📁 Temp файлов: {len(list(TEMP_DIR.glob('*')))}\n\n"
            f"🚀 Бот работает в Google Colab"
        )
    
    @router.message(F.video)
    async def handle_video_file(message: Message):
        """Handle uploaded video files"""
        try:
            processing_msg = await message.answer("🔄 Обрабатываю видео...")
            
            # Get file info
            file_info = await message.bot.get_file(message.video.file_id)
            
            # Create unique filename
            input_filename = f"input_{message.message_id}.mp4"
            output_filename = f"output_{message.message_id}.mp4"
            
            input_path = TEMP_DIR / input_filename
            output_path = TEMP_DIR / output_filename
            
            # Download file
            await message.bot.download_file(file_info.file_path, input_path)
            
            # Convert to shorts format
            await processing_msg.edit_text("🎬 Конвертирую в формат Shorts...")
            
            success = convert_to_shorts(str(input_path), str(output_path))
            
            if success and output_path.exists():
                # Send processed video
                await processing_msg.edit_text("📤 Отправляю результат...")
                
                from aiogram.types import FSInputFile
                video_file = FSInputFile(str(output_path))
                await message.answer_video(
                    video_file,
                    caption="✅ <b>Видео готово!</b>\n\n"
                           "📐 Формат: 1080x1920 (9:16)\n"
                           "🎯 Оптимизировано для Shorts\n"
                           "🔧 Обработано в Google Colab"
                )
                
                await processing_msg.delete()
            else:
                await processing_msg.edit_text(
                    "❌ <b>Ошибка обработки</b>\n\n"
                    "Не удалось конвертировать видео.\n"
                    "Попробуйте другой файл."
                )
            
            # Cleanup
            cleanup_files([input_path, output_path])
            
        except Exception as e:
            logger.error(f"Error processing video file: {e}")
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Произошла ошибка при обработке видео.\n"
                "Попробуйте еще раз."
            )
    
    @router.message(F.text.contains("youtube.com") | F.text.contains("youtu.be"))
    async def handle_youtube_url(message: Message):
        """Handle YouTube URLs"""
        try:
            processing_msg = await message.answer("📥 Скачиваю видео с YouTube...")
            
            url = message.text.strip()
            
            # Create unique filenames
            download_filename = f"download_{message.message_id}.%(ext)s"
            output_filename = f"output_{message.message_id}.mp4"
            
            download_path = str(TEMP_DIR / download_filename)
            output_path = TEMP_DIR / output_filename
            
            # Download from YouTube
            success = download_youtube_video(url, download_path)
            
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
                
                from aiogram.types import FSInputFile
                video_file = FSInputFile(str(output_path))
                await message.answer_video(
                    video_file,
                    caption="✅ <b>Видео готово!</b>\n\n"
                           "📐 Формат: 1080x1920 (9:16)\n"
                           "🎯 Оптимизировано для Shorts\n"
                           "📥 Источник: YouTube\n"
                           "🔧 Обработано в Google Colab"
                )
                
                await processing_msg.delete()
            else:
                await processing_msg.edit_text(
                    "❌ <b>Ошибка обработки</b>\n\n"
                    "Не удалось конвертировать видео.\n"
                    "Попробуйте другую ссылку."
                )
            
            # Cleanup
            cleanup_files([input_path, output_path])
            
        except Exception as e:
            logger.error(f"Error processing YouTube URL: {e}")
            await message.answer(
                "❌ <b>Ошибка</b>\n\n"
                "Произошла ошибка при обработке YouTube ссылки.\n"
                "Попробуйте еще раз."
            )
    
    @router.message()
    async def handle_other_messages(message: Message):
        """Handle all other messages"""
        await message.answer(
            "🤖 <b>VideoGenerator3000 - Colab Edition</b>\n\n"
            "Отправьте мне:\n"
            "📹 Видео файл для обработки\n"
            "🔗 Ссылку на YouTube\n"
            "❓ /status для проверки системы\n\n"
            "⚠️ Работаю в Google Colab с ограничениями"
        )
    
    # Register router
    dp.include_router(router)

def convert_to_shorts(input_path: str, output_path: str, duration_limit: int = 60) -> bool:
    """Convert video to vertical format (9:16) for Shorts"""
    try:
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-c:v', 'libx264',
            '-crf', '23',
            '-preset', 'fast',  # Faster preset for Colab
            '-t', str(duration_limit),
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"Successfully converted video: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return False
    except Exception as e:
        logger.error(f"Error converting video: {e}")
        return False

def download_youtube_video(url: str, output_path: str) -> bool:
    """Download video from YouTube with Colab optimizations"""
    try:
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best[height<=720]/best[height<=480]/worst',
            'noplaylist': True,
            'extractaudio': False,
            'ignoreerrors': False,
            'no_warnings': False,
            'retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first
            info = ydl.extract_info(url, download=False)
            if not info:
                logger.error("Failed to extract video information")
                return False
            
            # Check duration (limit for Colab)
            duration = info.get('duration', 0)
            if duration > 1800:  # 30 minutes max for Colab
                logger.error(f"Video too long: {duration} seconds (max 30 minutes)")
                return False
            
            # Download
            ydl.download([url])
            
            # Verify download
            import glob
            base_path = output_path.replace('.%(ext)s', '')
            downloaded_files = glob.glob(f"{base_path}.*")
            
            if not downloaded_files:
                logger.error("No files found after download")
                return False
            
            downloaded_file = downloaded_files[0]
            if not os.path.exists(downloaded_file) or os.path.getsize(downloaded_file) == 0:
                logger.error(f"Downloaded file is empty: {downloaded_file}")
                return False
            
        logger.info(f"Successfully downloaded video: {downloaded_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return False

def cleanup_files(file_paths):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if isinstance(file_path, (str, Path)) and Path(file_path).exists():
                Path(file_path).unlink()
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")