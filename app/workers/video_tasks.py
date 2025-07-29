"""
Celery tasks for video processing operations.
"""
import os
import uuid
import tempfile
import logging
from typing import Dict, Any, List

from celery import shared_task
from celery.utils.log import get_task_logger

from app.workers.celery_app import VideoTask
from app.config.constants import DEFAULT_TEXT_STYLES, get_subtitle_font_path
from app.config.settings import settings
from app.video_processing.downloader import VideoDownloader
from app.video_processing.processor import VideoProcessor

logger = logging.getLogger(__name__)


@shared_task(base=VideoTask, bind=True)
def download_video(self, task_id: str, url: str, quality: str = "best", settings_dict: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Download video from URL.
    
    Args:
        task_id: Video task ID
        url: Video URL to download
        quality: Video quality preference
        settings_dict: Processing settings including user cookies
        
    Returns:
        Dict with download results
    """
    logger.info(f"Starting video download for task {task_id}: {url}")
    
    if settings_dict is None:
        settings_dict = {}
    
    # Add delay between retries to avoid rapid requests
    if self.request.retries > 0:
        import time
        delay = min(30 * (2 ** self.request.retries), 300)  # Max 5 minute delay
        logger.info(f"Retry attempt {self.request.retries}, waiting {delay} seconds to avoid rate limiting...")
        time.sleep(delay)
    
    try:
        # Create download directory
        download_dir = f"/tmp/videos/{task_id}"
        os.makedirs(download_dir, exist_ok=True)
        
        # Get user cookies from settings
        user_cookies = settings_dict.get('cookies', '')
        logger.info(f"[DEBUG] User cookies present: {bool(user_cookies)}")
        
        # Initialize downloader with user cookies
        downloader = VideoDownloader(download_dir, None, user_cookies)
        
        try:
            # Download video with enhanced error handling
            logger.info(f"Attempting to download video from {url} (attempt {self.request.retries + 1})")
            download_result = downloader.download(url, quality)
            logger.info(f"Download successful for task {task_id}")
            
        except Exception as download_error:
            # Enhanced error handling for different types of download failures
            error_msg = str(download_error)
            logger.error(f"Download error for task {task_id}: {error_msg}")
            
            # Categorize the error for better user feedback
            if "Sign in to confirm you're not a bot" in error_msg or "bot detection" in error_msg.lower():
                user_friendly_error = "YouTube требует подтверждения. Попробуйте другое видео или повторите позже."
            elif "Video unavailable" in error_msg:
                user_friendly_error = "Видео недоступно. Проверьте ссылку или попробуйте другое видео."
            elif "Video is private" in error_msg:
                user_friendly_error = "Видео является приватным и недоступно для скачивания."
            elif "removed by the uploader" in error_msg:
                user_friendly_error = "Видео было удалено автором."
            elif "Video too long" in error_msg:
                user_friendly_error = "Видео слишком длинное (максимум 3 часа)."
            elif "Video too large" in error_msg:
                user_friendly_error = "Видео слишком большое (максимум 2GB)."
            elif "Invalid YouTube URL" in error_msg:
                user_friendly_error = "Некорректная ссылка на YouTube."
            elif "timeout" in error_msg.lower():
                user_friendly_error = "Превышено время ожидания при скачивании."
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                user_friendly_error = "Доступ к видео ограничен."
            elif "All download strategies failed" in error_msg:
                user_friendly_error = "YouTube блокирует автоматическое скачивание этого видео. Попробуйте другое видео."
            else:
                user_friendly_error = f"Ошибка скачивания: {error_msg[:100]}"
            
            # Re-raise with original error for retry logic
            raise download_error
        
        logger.info(f"Video download completed for task {task_id}")
        return download_result
        
    except Exception as exc:
        logger.error(f"Video download failed for task {task_id}: {exc}")
        
        # Don't retry if it's a permanent error
        if any(keyword in str(exc).lower() for keyword in ['unavailable', 'private', 'removed', 'invalid url']):
            logger.info(f"Permanent error detected for task {task_id}, not retrying: {exc}")
            raise exc  # Don't retry
        
        # Retry with exponential backoff, but limited retries for bot detection
        max_retries = 1 if "bot detection" in str(exc).lower() else 3
        countdown = 90 * (2 ** self.request.retries)  # Start with 90 seconds
        
        logger.info(f"Scheduling retry {self.request.retries + 1}/{max_retries} for task {task_id} in {countdown} seconds")
        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)


@shared_task(base=VideoTask, bind=True)
def process_video(self, task_id: str, local_path: str, settings_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process video by cutting into fragments and converting to shorts format.
    
    Args:
        task_id: Video task ID
        local_path: Path to downloaded video
        settings_dict: Processing settings
        
    Returns:
        List of processed video fragments
    """
    logger.info(f"Starting video processing for task {task_id}")
    
    try:
        # Extract settings
        fragment_duration = settings_dict.get("fragment_duration", 30)
        quality = settings_dict.get("quality", "1080p")
        enable_subtitles = settings_dict.get("enable_subtitles", True)
        title = settings_dict.get("title", "")
        
        # Create output directory
        output_dir = f"/tmp/processed/{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize processor
        processor = VideoProcessor(output_dir)
        
        # Process video into fragments with professional layout
        if enable_subtitles:
            fragments_data = processor.create_fragments_with_subtitles(
                video_path=local_path,
                fragment_duration=fragment_duration,
                quality=quality,
                title=title,
                subtitle_style="modern"
            )
        else:
            fragments_data = processor.create_fragments_precise(
                video_path=local_path,
                fragment_duration=fragment_duration,
                quality=quality,
                title=title,
                subtitle_style="modern"
            )
        
        fragments = []
        
        for fragment_data in fragments_data:
            fragment_id = str(uuid.uuid4())
            
            # Prepare fragment info
            fragment_info = {
                "id": fragment_id,
                "task_id": task_id,
                "fragment_number": fragment_data["fragment_number"],
                "filename": fragment_data["filename"],
                "local_path": fragment_data["local_path"],
                "duration": fragment_data["duration"],
                "start_time": fragment_data["start_time"],
                "end_time": fragment_data["end_time"],
                "size_bytes": fragment_data["size_bytes"],
                "resolution": fragment_data["resolution"],
                "fps": fragment_data["fps"],
                "has_subtitles": enable_subtitles
            }
            fragments.append(fragment_info)
        
        # Clean up original downloaded file
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Cleaned up original file: {local_path}")
        
        logger.info(f"Video processing completed for task {task_id}, created {len(fragments)} fragments")
        return fragments
        
    except Exception as exc:
        logger.error(f"Video processing failed for task {task_id}: {exc}")
        raise self.retry(exc=exc, countdown=120, max_retries=2)


@shared_task(base=VideoTask, bind=True)
def process_uploaded_file_chain(self, task_id: str, file_id: str, file_name: str, file_size: int, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process uploaded file chain: download from Telegram -> process -> fragment.
    """
    logger.info(f"Starting uploaded file processing chain for task {task_id}")
    
    try:
        # Step 1: Download file from Telegram
        logger.info(f"Step 1/3: Downloading file from Telegram for task {task_id}")
        
        download_result = download_telegram_file_sync(task_id, file_id, file_name, file_size, settings_dict)
        
        # Step 2: Process video
        logger.info(f"Step 2/3: Processing video for task {task_id}")
        
        output_dir = f"/tmp/processed/{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        processor = VideoProcessor(output_dir)
        
        # Split video into chunks if longer than 5 minutes
        chunk_duration = 300  # 5 minutes per chunk
        video_chunks = processor.split_video(download_result["local_path"], chunk_duration)
        
        logger.info(f"Video split into {len(video_chunks)} chunks for processing")
        
        # Process each chunk
        processed_chunks = []
        total_chunks = len(video_chunks)
        failed_chunks = []
        
        for i, chunk_path in enumerate(video_chunks):
            try:
                logger.info(f"Processing chunk {i+1}/{total_chunks}: {os.path.basename(chunk_path)}")
                
                # Create chunk-specific output directory
                chunk_output_dir = os.path.join(output_dir, f"chunk_{i+1}")
                os.makedirs(chunk_output_dir, exist_ok=True)
                chunk_processor = VideoProcessor(chunk_output_dir)
                
                # Process chunk with title including part number if multiple chunks
                chunk_title = settings_dict.get("title", "")
                if len(video_chunks) > 1 and chunk_title:
                    chunk_title = f"{chunk_title} - Часть {i+1}"
                
                chunk_settings = settings_dict.copy()
                chunk_settings['title'] = chunk_title
                chunk_settings['ffmpeg_timeout'] = min(settings_dict.get('ffmpeg_timeout', 3600), 3600)
                
                chunk_result = chunk_processor.process_video_ffmpeg(
                    video_path=chunk_path,
                    settings=chunk_settings
                )
                
                processed_chunks.append({
                    'chunk_number': i + 1,
                    'chunk_path': chunk_path,
                    'processed_path': chunk_result['processed_video_path'],
                    'processor': chunk_processor
                })
                        
                logger.info(f"Chunk {i+1}/{total_chunks} processed successfully")
                
            except Exception as e:
                logger.error(f"Failed to process chunk {i+1}: {e}")
                failed_chunks.append(i + 1)
                continue
        
        # Check if we have enough successful chunks to continue
        if len(processed_chunks) == 0:
            raise RuntimeError(f"All chunks failed to process. Failed chunks: {failed_chunks}")
        elif len(failed_chunks) > 0:
            logger.warning(f"Some chunks failed ({failed_chunks}), but continuing with {len(processed_chunks)} successful chunks")
        
        logger.info(f"Processed {len(processed_chunks)}/{total_chunks} chunks successfully")
        
        # Step 3: Create fragments from all processed chunks
        logger.info(f"Step 3/3: Creating fragments from processed chunks for task {task_id}")
        
        all_fragments = []
        fragment_counter = 1
        
        for chunk_info in processed_chunks:
            chunk_processor = chunk_info['processor']
            processed_path = chunk_info['processed_path']
            
            # Create fragments from this chunk
            chunk_title = settings_dict.get('title', '')
            
            # Only add part number if multiple chunks exist
            if len(processed_chunks) > 1 and chunk_title:
                fragment_title = f"{chunk_title} - Часть {chunk_info['chunk_number']}"
            else:
                fragment_title = chunk_title
            
            chunk_fragments = chunk_processor.create_fragments(
                video_path=processed_path,
                fragment_duration=settings_dict.get("fragment_duration", 30),
                title=fragment_title
            )
            
            # Renumber fragments globally and update paths
            for fragment_data in chunk_fragments:
                fragment_data['fragment_number'] = fragment_counter
                fragment_data['chunk_number'] = chunk_info['chunk_number']
                all_fragments.append(fragment_data)
                fragment_counter += 1
        
        fragments = all_fragments
        
        # Clean up temporary files
        logger.info(f"Cleaning up temporary files for task {task_id}")
        cleanup_temp_files([download_result["local_path"]] + [chunk for chunk in video_chunks])
        
        logger.info(f"Uploaded file processing completed successfully for task {task_id}")
        return {
            "success": True,
            "task_id": task_id,
            "fragments_count": len(fragments),
            "fragments": fragments
        }

    except Exception as exc:
        logger.error(f"Uploaded file processing failed for task {task_id}: {exc}")
        
        # Retry with exponential backoff
        max_retries = 2
        countdown = 120 * (2 ** self.request.retries)
        
        logger.info(f"Scheduling retry {self.request.retries + 1}/{max_retries} for task {task_id} in {countdown} seconds")
        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)


def download_telegram_file_sync(task_id: str, file_id: str, file_name: str, file_size: int, settings_dict: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Synchronous wrapper for downloading Telegram files.
    This is needed because Celery tasks can't easily handle async operations.
    """
    import asyncio
    from aiogram import Bot
    from app.config.settings import settings
    
    if settings_dict is None:
        settings_dict = {}
    
    async def _download():
        bot = Bot(token=settings.telegram_bot_token.get_secret_value())
        try:
            # Create download directory
            download_dir = f"/tmp/videos/{task_id}"
            os.makedirs(download_dir, exist_ok=True)
            
            # Initialize downloader (no cookies needed for Telegram files)
            from app.video_processing.downloader import VideoDownloader
            downloader = VideoDownloader(download_dir, None, "")
            
            # Download file
            result = await downloader.download_telegram_file(bot, file_id, file_name, file_size)
            return result
        finally:
            await bot.session.close()
    
    # Run the async function in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_download())
    finally:
        loop.close()


@shared_task(base=VideoTask, bind=True)
def process_video_chain_optimized(self, task_id: str, url: str, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimized video processing chain: download -> full processing with FFmpeg -> fragment.
    This version avoids using MoviePy for processing, relying on FFmpeg for performance.
    """
    logger.info(f"Starting FFmpeg-optimized video processing chain for task {task_id}")
    
    try:
        # Step 1: Download video
        logger.info(f"Step 1/3: Downloading video for task {task_id}")
        
        quality = settings_dict.get("quality", "1080p")
        download_result = download_video(task_id, url, quality, settings_dict)
        
        # Step 2: Split video into chunks if it's long
        logger.info(f"Step 2/3: Checking if video needs to be split for task {task_id}")
        
        output_dir = f"/tmp/processed/{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        processor = VideoProcessor(output_dir)
        
        # Split video into chunks if longer than 5 minutes
        chunk_duration = 300  # 5 minutes per chunk
        video_chunks = processor.split_video(download_result["local_path"], chunk_duration)
        
        logger.info(f"Video split into {len(video_chunks)} chunks for processing")
        
        # Process each chunk separately
        processed_chunks = []
        total_chunks = len(video_chunks)
        failed_chunks = []
        
        for i, chunk_path in enumerate(video_chunks):
            try:
                logger.info(f"Processing chunk {i+1}/{total_chunks}: {os.path.basename(chunk_path)}")
                
                # Create chunk-specific output directory
                chunk_output_dir = os.path.join(output_dir, f"chunk_{i+1}")
                os.makedirs(chunk_output_dir, exist_ok=True)
                chunk_processor = VideoProcessor(chunk_output_dir)
                
                # Process chunk with title including part number if multiple chunks
                chunk_title = settings_dict.get("title", "")
                if len(video_chunks) > 1 and chunk_title:
                    chunk_title = f"{chunk_title} - Часть {i+1}"
                
                chunk_settings = settings_dict.copy()
                chunk_settings['title'] = chunk_title
                chunk_settings['ffmpeg_timeout'] = min(settings_dict.get('ffmpeg_timeout', 28800), 28800)
                
                chunk_result = chunk_processor.process_video_ffmpeg(
                    video_path=chunk_path,
                    settings=chunk_settings
                )
                
                processed_chunks.append({
                    'chunk_number': i + 1,
                    'chunk_path': chunk_path,
                    'processed_path': chunk_result['processed_video_path'],
                    'processor': chunk_processor
                })
                        
                logger.info(f"Chunk {i+1}/{total_chunks} processed successfully")
                
            except Exception as e:
                logger.error(f"Failed to process chunk {i+1}: {e}")
                failed_chunks.append(i + 1)
                continue
        
        # Check if we have enough successful chunks to continue
        if len(processed_chunks) == 0:
            raise RuntimeError(f"All chunks failed to process. Failed chunks: {failed_chunks}")
        elif len(failed_chunks) > 0:
            logger.warning(f"Some chunks failed ({failed_chunks}), but continuing with {len(processed_chunks)} successful chunks")
        
        logger.info(f"Processed {len(processed_chunks)}/{total_chunks} chunks successfully")
        
        # Step 3: Create fragments from all processed chunks
        logger.info(f"Step 3/3: Creating fragments from processed chunks for task {task_id}")
        
        all_fragments = []
        fragment_counter = 1
        
        for chunk_info in processed_chunks:
            chunk_processor = chunk_info['processor']
            processed_path = chunk_info['processed_path']
            
            # Create fragments from this chunk
            chunk_title = settings_dict.get('title', '')
            
            # Only add part number if multiple chunks exist
            if len(processed_chunks) > 1 and chunk_title:
                fragment_title = f"{chunk_title} - Часть {chunk_info['chunk_number']}"
            else:
                fragment_title = chunk_title
            
            chunk_fragments = chunk_processor.create_fragments(
                video_path=processed_path,
                fragment_duration=settings_dict.get("fragment_duration", 30),
                title=fragment_title
            )
            
            # Renumber fragments globally and update paths
            for fragment_data in chunk_fragments:
                fragment_data['fragment_number'] = fragment_counter
                fragment_data['chunk_number'] = chunk_info['chunk_number']
                all_fragments.append(fragment_data)
                fragment_counter += 1
        
        fragments = all_fragments
        
        # Clean up temporary files
        logger.info(f"Cleaning up temporary files for task {task_id}")
        cleanup_temp_files([download_result["local_path"]] + [chunk for chunk in video_chunks])
        
        logger.info(f"Video processing completed successfully for task {task_id}")
        return {
            "success": True,
            "task_id": task_id,
            "fragments_count": len(fragments),
            "fragments": fragments
        }

    except Exception as exc:
        logger.error(f"Video processing failed for task {task_id}: {exc}")
        
        # Retry with exponential backoff
        max_retries = 2
        countdown = 120 * (2 ** self.request.retries)
        
        logger.info(f"Scheduling retry {self.request.retries + 1}/{max_retries} for task {task_id} in {countdown} seconds")
        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files.
    
    Args:
        file_paths: List of file paths to clean up
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up file {file_path}: {e}")


def send_completion_notification(user_id: int, task_id: str, fragments_count: int) -> None:
    """
    Send completion notification to user.
    
    Args:
        user_id: User ID
        task_id: Task ID
        fragments_count: Number of fragments created
    """
    try:
        import asyncio
        from aiogram import Bot
        from app.config.settings import settings
        
        async def _send_notification():
            bot = Bot(token=settings.telegram_bot_token.get_secret_value())
            try:
                message = f"""
✅ <b>Обработка завершена!</b>

📋 ID задачи: <code>{task_id}</code>
📊 Создано фрагментов: {fragments_count}

Ваше видео успешно обработано и готово к использованию!
                """
                
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML"
                )
                logger.info(f"Completion notification sent to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send completion notification to user {user_id}: {e}")
            finally:
                await bot.session.close()
        
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send_notification())
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to send completion notification: {e}")