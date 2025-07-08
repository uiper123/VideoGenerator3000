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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.workers.celery_app import VideoTask
from app.config.constants import VideoStatus, DEFAULT_TEXT_STYLES, get_subtitle_font_path
from app.config.settings import settings
from app.database.models import VideoTask as VideoTaskModel, VideoFragment, User
from app.video_processing.downloader import VideoDownloader
from app.video_processing.processor import VideoProcessor

logger = logging.getLogger(__name__)

# Create synchronous database session for Celery tasks
engine = create_engine(settings.database_url.replace('+asyncpg', '+psycopg2'))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_sync_db_session():
    """Get synchronous database session for Celery tasks."""
    return SessionLocal()


@shared_task(base=VideoTask, bind=True)
def download_video(self, task_id: str, url: str, quality: str = "best") -> Dict[str, Any]:
    """
    Download video from URL.
    
    Args:
        task_id: Video task ID
        url: Video URL to download
        quality: Video quality preference
        
    Returns:
        Dict with download results
    """
    logger.info(f"Starting video download for task {task_id}: {url}")
    
    # Add delay between retries to avoid rapid requests
    if self.request.retries > 0:
        import time
        delay = min(30 * (2 ** self.request.retries), 300)  # Max 5 minute delay
        logger.info(f"Retry attempt {self.request.retries}, waiting {delay} seconds to avoid rate limiting...")
        time.sleep(delay)
    
    try:
        # Update task status
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.DOWNLOADING
                task.progress = 0
                session.commit()
        
        # Create download directory
        download_dir = f"/tmp/videos/{task_id}"
        os.makedirs(download_dir, exist_ok=True)
        
        # Get user's individual proxy (if available)
        user_proxy = None
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task and task.user_id:
                user = session.get(User, task.user_id)
                if user and user.settings and 'download_proxy' in user.settings:
                    user_proxy = user.settings['download_proxy']
        
        # Initialize downloader
        downloader = VideoDownloader(download_dir)
        
        # Download video with enhanced error handling
        logger.info(f"Attempting to download video from {url} (attempt {self.request.retries + 1})")
        download_result = downloader.download(url, quality, user_proxy=user_proxy)
        logger.info(f"Download successful for task {task_id}")
        
        # Update task with metadata
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                # Update video_metadata (not metadata)
                if task.video_metadata is None:
                    task.video_metadata = {}
                task.video_metadata.update({
                    "title": download_result["title"],
                    "duration": download_result["duration"],
                    "size_bytes": download_result["file_size"],
                    "format": download_result.get("format", "mp4"),
                    "resolution": download_result.get("resolution", "720p"),
                    "fps": download_result.get("fps", 30),  # Get FPS from download result or default to 30
                    "thumbnail": download_result.get("thumbnail"),
                    "description": download_result.get("description", ""),
                    "uploader": download_result.get("author", "")
                })
                task.progress = 100
                session.commit()
        
        logger.info(f"Video download completed for task {task_id}")
        return download_result
        
    except Exception as exc:
        logger.error(f"Video download failed for task {task_id}: {exc}")
        
        # Enhanced error handling for different types of download failures
        error_msg = str(exc)
        
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
        
        # Update task status to failed if not already updated
        try:
            with get_sync_db_session() as session:
                task = session.get(VideoTaskModel, task_id)
                if task and task.status != VideoStatus.FAILED:
                    task.status = VideoStatus.FAILED
                    if not task.error_message:  # Only set if not already set above
                        task.error_message = user_friendly_error
                    session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update task status: {db_error}")
        
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
        # Update task status
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.PROCESSING
                task.progress = 0
                session.commit()
        
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
            fragments_data = processor.create_fragments(
                video_path=local_path,
                fragment_duration=fragment_duration,
                quality=quality,
                title=title,
                subtitle_style="modern"
            )
        
        fragments = []
        total_fragments = len(fragments_data)
        
        for i, fragment_data in enumerate(fragments_data):
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
            
            # Save fragment to database
            with get_sync_db_session() as session:
                fragment = VideoFragment(
                    id=fragment_id,
                    task_id=task_id,
                    fragment_number=fragment_data["fragment_number"],
                    filename=fragment_data["filename"],
                    local_path=fragment_data["local_path"],
                    duration=fragment_data["duration"],
                    start_time=fragment_data["start_time"],
                    end_time=fragment_data["end_time"],
                    size_bytes=fragment_data["size_bytes"],
                    has_subtitles=enable_subtitles
                )
                session.add(fragment)
                session.commit()
            
            # Update progress
            progress = int((i + 1) / total_fragments * 100)
            with get_sync_db_session() as session:
                task = session.get(VideoTaskModel, task_id)
                if task:
                    task.progress = progress
                    session.commit()
        
        # Clean up original downloaded file
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Cleaned up original file: {local_path}")
        
        logger.info(f"Video processing completed for task {task_id}, created {len(fragments)} fragments")
        return fragments
        
    except Exception as exc:
        logger.error(f"Video processing failed for task {task_id}: {exc}")
        
        # Update task status to failed
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.FAILED
                task.error_message = str(exc)
                session.commit()
        
        raise self.retry(exc=exc, countdown=120, max_retries=2)


@shared_task(base=VideoTask, bind=True)
def process_uploaded_file_chain(self, task_id: str, file_id: str, file_name: str, file_size: int, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process uploaded file chain: download from Telegram -> process -> fragment -> upload.
    """
    logger.info(f"Starting uploaded file processing chain for task {task_id}")
    
    # Check for duplicate tasks
    with get_sync_db_session() as session:
        task = session.get(VideoTaskModel, task_id)
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return {"error": "Task not found"}
        
        # If task is already completed or failed, don't process again
        if task.status in [VideoStatus.COMPLETED, VideoStatus.FAILED]:
            logger.info(f"Task {task_id} already {task.status.value}, skipping duplicate execution")
            return {"error": f"Task already {task.status.value}"}
        
        # Check if task is already being processed by another worker
        if task.status in [VideoStatus.PROCESSING, VideoStatus.UPLOADING] and self.request.retries == 0:
            logger.warning(f"Task {task_id} is already being processed by another worker")
            return {"error": "Task already being processed"}
    
    try:
        # Step 1: Download file from Telegram
        logger.info(f"Step 1/7: Downloading file from Telegram for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.DOWNLOADING
                task.progress = 10
                session.commit()
        
        # We need to get the bot instance - this will need to be passed or accessed differently
        # For now, we'll create a sync version of the download
        download_result = download_telegram_file_sync(task_id, file_id, file_name, file_size)
        
        # Step 2: Split video into chunks if it's long
        logger.info(f"Step 2/7: Checking if video needs to be split for task {task_id}")
        
        output_dir = f"/tmp/processed/{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        processor = VideoProcessor(output_dir)
        
        # Split video into chunks if longer than 5 minutes
        chunk_duration = 300  # 5 minutes per chunk
        video_chunks = processor.split_video(download_result["local_path"], chunk_duration)
        
        logger.info(f"Video split into {len(video_chunks)} chunks for processing")
        
        # Step 3: Process each chunk separately
        logger.info(f"Step 3/7: Processing video chunks for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.PROCESSING
                task.progress = 30
                session.commit()

        # Get user style settings
        user_settings = get_user_settings(task_id)
        
        # Combine user settings with task settings
        processing_settings = settings_dict.copy()
        processing_settings.update(user_settings)

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
                
                # Process chunk with title including part number only if enabled and multiple chunks
                chunk_title = settings_dict.get("title", "")
                add_part_numbers = settings_dict.get("add_part_numbers", False)
                if len(video_chunks) > 1 and chunk_title and add_part_numbers:
                    chunk_title = f"{chunk_title} - Часть {i+1}"
                
                chunk_settings = processing_settings.copy()
                chunk_settings['title'] = chunk_title
                
                # Use shorter timeout for chunks
                chunk_settings['ffmpeg_timeout'] = min(processing_settings.get('ffmpeg_timeout', 3600), 3600)
                
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
                
                # Update progress
                chunk_progress = 30 + int((i + 1) / total_chunks * 30)  # 30-60%
                with get_sync_db_session() as session:
                    task = session.get(VideoTaskModel, task_id)
                    if task:
                        task.progress = chunk_progress
                        session.commit()
                        
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
        
        # Step 4: Create fragments from all processed chunks
        logger.info(f"Step 4/7: Creating fragments from processed chunks for task {task_id}")
        
        all_fragments = []
        fragment_counter = 1
        
        for chunk_info in processed_chunks:
            chunk_processor = chunk_info['processor']
            processed_path = chunk_info['processed_path']
            
            # Create fragments from this chunk
            chunk_title = settings_dict.get('title', '')
            add_part_numbers = settings_dict.get("add_part_numbers", False)
            
            # Only add part number if explicitly enabled and multiple chunks exist
            if len(processed_chunks) > 1 and chunk_title and add_part_numbers:
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
        
        # Step 5: Save fragments to database
        for fragment_data in fragments:
            with get_sync_db_session() as session:
                fragment_model = VideoFragment(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    fragment_number=fragment_data['fragment_number'],
                    filename=fragment_data['filename'],
                    local_path=fragment_data['local_path'],
                    duration=fragment_data['duration'],
                    start_time=fragment_data['start_time'],
                    end_time=fragment_data.get('start_time', 0) + fragment_data['duration'],
                    size_bytes=fragment_data['size_bytes'],
                    has_subtitles=settings_dict.get('enable_subtitles', True)
                )
                session.add(fragment_model)
                session.commit()
                fragment_data['id'] = fragment_model.id

        # Step 6: Upload to Google Drive
        logger.info(f"Step 6/7: Uploading to Google Drive for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.UPLOADING
                task.progress = 70
                session.commit()
        
        from app.services.google_drive import GoogleDriveService
        drive_service = GoogleDriveService()
        upload_results = drive_service.upload_multiple_files(
            file_paths=[f["local_path"] for f in fragments],
            task_id=task_id
        )
        successful_uploads = [r for r in upload_results if r.get("success")]
        logger.info(f"Successfully uploaded {len(successful_uploads)}/{len(fragments)} files to Google Drive.")

        # Update fragments with Google Drive URLs
        for i, upload_result in enumerate(upload_results):
            if upload_result.get("success") and i < len(fragments):
                fragment_data = fragments[i]
                
                drive_url = upload_result.get("direct_url", "")
                
                with get_sync_db_session() as session:
                    fragment_model = session.get(VideoFragment, fragment_data['id'])
                    if fragment_model:
                        fragment_model.drive_url = drive_url
                        fragment_model.drive_file_id = upload_result.get("file_id", "")
                        session.commit()

        # Step 7: Log to Google Sheets
        logger.info(f"Step 7/7: Logging to Google Sheets for task {task_id}")
        
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            user_id = task.user_id if task else 0
        
        sheet_result = log_to_sheets(
            task_id=task_id,
            download_result=download_result,
            fragments=fragments,
            upload_results=upload_results,
            settings_dict=settings_dict,
            user_id=user_id
        )

        # Step 8: Mark task as completed
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.COMPLETED
                task.progress = 100
                # Update video_metadata (not metadata)
                if task.video_metadata is None:
                    task.video_metadata = {}
                task.video_metadata.update({
                    'fragments_count': len(fragments),
                    'successful_uploads': len(successful_uploads),
                    'sheet_url': sheet_result.get('sheet_url', ''),
                    'drive_folder_url': upload_results[0].get('folder_url', '') if upload_results else ''
                })
                session.commit()

        # Step 9: Clean up temporary files
        logger.info(f"Step 9/9: Cleaning up temporary files for task {task_id}")
        cleanup_temp_files([download_result["local_path"]] + [chunk for chunk in video_chunks])
        
        # Step 10: Send completion notification
        send_completion_notification(user_id, task_id, len(fragments))

        logger.info(f"Uploaded file processing completed successfully for task {task_id}")
        return {
            "success": True,
            "task_id": task_id,
            "fragments_count": len(fragments),
            "successful_uploads": len(successful_uploads)
        }

    except Exception as exc:
        logger.error(f"Uploaded file processing failed for task {task_id}: {exc}")
        
        # Update task status to failed
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.FAILED
                task.error_message = str(exc)[:500]
                session.commit()
        
        # Retry with exponential backoff
        max_retries = 2
        countdown = 120 * (2 ** self.request.retries)
        
        logger.info(f"Scheduling retry {self.request.retries + 1}/{max_retries} for task {task_id} in {countdown} seconds")
        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)


def download_telegram_file_sync(task_id: str, file_id: str, file_name: str, file_size: int) -> Dict[str, Any]:
    """
    Synchronous wrapper for downloading Telegram files.
    This is needed because Celery tasks can't easily handle async operations.
    """
    import asyncio
    from aiogram import Bot
    from app.config.settings import settings
    
    async def _download():
        bot = Bot(token=settings.telegram_bot_token.get_secret_value())
        try:
            # Create download directory
            download_dir = f"/tmp/videos/{task_id}"
            os.makedirs(download_dir, exist_ok=True)
            
            # Initialize downloader
            from app.video_processing.downloader import VideoDownloader
            downloader = VideoDownloader(download_dir)
            
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
    Optimized video processing chain: download -> full processing with FFmpeg -> fragment -> upload.
    This version avoids using MoviePy for processing, relying on FFmpeg for performance.
    """
    logger.info(f"Starting FFmpeg-optimized video processing chain for task {task_id}")
    
    # Check for duplicate tasks - prevent multiple executions of the same task
    with get_sync_db_session() as session:
        task = session.get(VideoTaskModel, task_id)
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return {"error": "Task not found"}
        
        # If task is already completed or failed, don't process again
        if task.status in [VideoStatus.COMPLETED, VideoStatus.FAILED]:
            logger.info(f"Task {task_id} already {task.status.value}, skipping duplicate execution")
            return {"error": f"Task already {task.status.value}"}
        
        # Check if task is already being processed by another worker
        if task.status in [VideoStatus.PROCESSING, VideoStatus.UPLOADING] and self.request.retries == 0:
            logger.warning(f"Task {task_id} is already being processed by another worker")
            return {"error": "Task already being processed"}
    
    try:
        # Step 1: Download video
        logger.info(f"Step 1/7: Downloading video for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.DOWNLOADING
                task.progress = 10
                session.commit()
        
        quality = settings_dict.get("quality", "1080p")
        download_result = download_video(task_id, url, quality)
        
        # Step 2: Split video into chunks if it's long (to avoid timeouts)
        logger.info(f"Step 2/7: Checking if video needs to be split for task {task_id}")
        
        # Initialize the processor
        output_dir = f"/tmp/processed/{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        processor = VideoProcessor(output_dir)
        
        # Split video into chunks if longer than 5 minutes (300 seconds)
        chunk_duration = 300  # 5 minutes per chunk (было 600, но это слишком долго для faster-whisper)
        video_chunks = processor.split_video(download_result["local_path"], chunk_duration)
        
        logger.info(f"Video split into {len(video_chunks)} chunks for processing")
        
        # Step 3: Process each chunk separately
        logger.info(f"Step 3/7: Processing video chunks for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.PROCESSING
                task.progress = 30
                session.commit()

        # Get user style settings to pass to the processor
        user_settings = get_user_settings(task_id)
        
        # Combine user settings with task settings
        processing_settings = settings_dict.copy()
        processing_settings.update(user_settings)

        # Process each chunk using the new FFmpeg-native method
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
                
                # Process chunk with title including part number only if enabled and multiple chunks
                chunk_title = settings_dict.get("title", "")
                add_part_numbers = settings_dict.get("add_part_numbers", False)  # Default: disabled
                if len(video_chunks) > 1 and chunk_title and add_part_numbers:
                    chunk_title = f"{chunk_title} - Часть {i+1}"
                
                chunk_settings = processing_settings.copy()
                chunk_settings['title'] = chunk_title
                
                # Use shorter timeout for chunks (увеличено для больших видео)
                chunk_settings['ffmpeg_timeout'] = min(processing_settings.get('ffmpeg_timeout', 3600), 3600)
                
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
                
                # Update progress
                chunk_progress = 30 + int((i + 1) / total_chunks * 30)  # 30-60%
                with get_sync_db_session() as session:
                    task = session.get(VideoTaskModel, task_id)
                    if task:
                        task.progress = chunk_progress
                        session.commit()
                        
                logger.info(f"Chunk {i+1}/{total_chunks} processed successfully")
                
            except Exception as e:
                logger.error(f"Failed to process chunk {i+1}: {e}")
                failed_chunks.append(i + 1)
                # Continue with other chunks instead of failing the entire task
                continue
        
        # Check if we have enough successful chunks to continue
        if len(processed_chunks) == 0:
            raise RuntimeError(f"All chunks failed to process. Failed chunks: {failed_chunks}")
        elif len(failed_chunks) > 0:
            logger.warning(f"Some chunks failed ({failed_chunks}), but continuing with {len(processed_chunks)} successful chunks")
        
        logger.info(f"Processed {len(processed_chunks)}/{total_chunks} chunks successfully")
        
        # Step 4: Create fragments from all processed chunks
        logger.info(f"Step 4/7: Creating fragments from processed chunks for task {task_id}")
        
        all_fragments = []
        fragment_counter = 1
        
        for chunk_info in processed_chunks:
            chunk_processor = chunk_info['processor']
            processed_path = chunk_info['processed_path']
            
            # Create fragments from this chunk
            chunk_title = settings_dict.get('title', '')
            add_part_numbers = settings_dict.get("add_part_numbers", False)
            
            # Only add part number if explicitly enabled and multiple chunks exist
            if len(processed_chunks) > 1 and chunk_title and add_part_numbers:
                fragment_title = f"{chunk_title} - Часть {chunk_info['chunk_number']}"
            else:
                fragment_title = chunk_title
            
            chunk_fragments = chunk_processor.create_fragments(
                video_path=processed_path,
                fragment_duration=settings_dict.get("duration", 30),
                title=fragment_title
            )
            
            # Renumber fragments globally and update paths
            for fragment_data in chunk_fragments:
                fragment_data['fragment_number'] = fragment_counter
                fragment_data['chunk_number'] = chunk_info['chunk_number']
                all_fragments.append(fragment_data)
                fragment_counter += 1
        
        fragments = all_fragments
        
        # Step 5: Save fragments to database
        for fragment_data in fragments:
            with get_sync_db_session() as session:
                fragment_model = VideoFragment(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    fragment_number=fragment_data['fragment_number'],
                    filename=fragment_data['filename'],
                    local_path=fragment_data['local_path'],
                    duration=fragment_data['duration'],
                    start_time=fragment_data['start_time'],
                    end_time=fragment_data.get('start_time', 0) + fragment_data['duration'],
                    size_bytes=fragment_data['size_bytes'],
                    has_subtitles=settings_dict.get('enable_subtitles', True)
                )
                session.add(fragment_model)
                session.commit()
                fragment_data['id'] = fragment_model.id

        # Step 6: Upload to Google Drive
        logger.info(f"Step 6/7: Uploading to Google Drive for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.UPLOADING
                task.progress = 70
                session.commit()
        
        from app.services.google_drive import GoogleDriveService
        drive_service = GoogleDriveService()
        upload_results = drive_service.upload_multiple_files(
            file_paths=[f["local_path"] for f in fragments],
            task_id=task_id
        )
        successful_uploads = [r for r in upload_results if r.get("success")]
        logger.info(f"Successfully uploaded {len(successful_uploads)}/{len(fragments)} files to Google Drive.")

        # Update fragments with Google Drive URLs
        for i, upload_result in enumerate(upload_results):
            if upload_result.get("success") and i < len(fragments):
                fragment_data = fragments[i]
                
                # Используем прямую ссылку для скачивания вместо view ссылки
                drive_url = upload_result.get("direct_url", "")  # Изменено с file_url на direct_url
                view_url = upload_result.get("file_url", "")     # Ссылка для просмотра
                
                # Update fragment in database with drive URL
                with get_sync_db_session() as session:
                    fragment = session.get(VideoFragment, fragment_data['id'])
                    if fragment and drive_url:
                        # КРИТИЧЕСКИ ВАЖНО: Сохраняем URL в поле drive_url!
                        fragment.drive_url = drive_url
                        
                        # Correctly handle JSON metadata field
                        current_metadata = fragment.metadata
                        if isinstance(current_metadata, dict):
                            updated_metadata = current_metadata.copy()
                        else:
                            # If metadata is corrupted or not a dict, reset it.
                            logger.warning(f"Fragment {fragment.id} metadata was corrupted. Type: {type(current_metadata)}. Resetting.")
                            updated_metadata = {}
                        
                        updated_metadata['view_url'] = view_url
                        updated_metadata['public'] = upload_result.get('public', False)
                        
                        # Assign the updated dictionary back
                        fragment.metadata = updated_metadata
                        
                        session.commit()
                        fragment_data['drive_url'] = drive_url
                        fragment_data['view_url'] = view_url
                        fragment_data['public'] = upload_result.get('public', False)
                        logger.info(f"Updated fragment {fragment.fragment_number} with direct download URL: {drive_url}")
                    elif not drive_url:
                        logger.warning(f"No direct URL available for fragment {fragment_data.get('fragment_number', i+1)}")
                        # Используем view URL как fallback если нет прямой ссылки
                        fallback_url = view_url
                        if fallback_url:
                            fragment.drive_url = fallback_url
                            session.commit()
                            fragment_data['drive_url'] = fallback_url
                            logger.warning(f"Using view URL as fallback for fragment {fragment.fragment_number}: {fallback_url}")

        # Step 7: Log to Google Sheets
        logger.info(f"Step 7/7: Logging results to Google Sheets for task {task_id}")
        
        # Get user ID from task
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            user_id_for_sheets = task.user_id if task else 0
        
        log_to_sheets(
            task_id=task_id,
            download_result=download_result,
            fragments=fragments,
            upload_results=upload_results,
            settings_dict=settings_dict,
            user_id=user_id_for_sheets
        )
        
        # Step 8: Finalize and Cleanup
        logger.info(f"Finalizing and cleaning up task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.COMPLETED
                task.progress = 100
                session.commit()
                
                # Send completion notification
                send_completion_notification.apply_async(args=[task.user_id, task_id, len(fragments)])
        
        # Collect all paths for cleanup
        cleanup_paths = [download_result["local_path"]]
        
        # Add chunk paths
        for chunk_info in processed_chunks:
            cleanup_paths.append(chunk_info['chunk_path'])
            cleanup_paths.append(chunk_info['processed_path'])
        
        # Add fragment paths
        cleanup_paths.extend([f["local_path"] for f in fragments])
        
        cleanup_temp_files(cleanup_paths)
        
        result = {
            "task_id": task_id,
            "status": "completed",
            "fragments_count": len(fragments),
            "total_duration": sum(f.get("duration", 0) for f in fragments if isinstance(f, dict) and "duration" in f),
            "total_size_bytes": sum(f.get("size_bytes", 0) for f in fragments if isinstance(f, dict) and "size_bytes" in f),
            "drive_uploads": len(successful_uploads),
            "fragments": fragments,
            "failed_chunks": failed_chunks if failed_chunks else None
        }
        
        logger.info(f"FFmpeg-optimized video processing chain completed for task {task_id}")
        return result
        
    except Exception as exc:
        task_logger = get_task_logger(__name__)
        task_logger.error(f"Optimized video processing chain failed for task {task_id}: {exc}", exc_info=True)
        
        # Update task status to failed
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.FAILED
                task.error_message = str(exc)
                session.commit()
        
        # More conservative retry logic - only retry on certain types of errors
        # and with fewer retries
        if self.request.retries < 2:  # Reduced from 5 to 2
            # Only retry on temporary errors
            if any(keyword in str(exc).lower() for keyword in ['timeout', 'connection', 'network', 'temporary']):
                countdown = 120 * (self.request.retries + 1)  # Linear backoff instead of exponential
                logger.info(f"Retrying task {task_id} (attempt {self.request.retries + 1}/2) in {countdown} seconds")
                raise self.retry(exc=exc, countdown=countdown, max_retries=2)
            else:
                logger.error(f"Permanent error for task {task_id}, not retrying: {exc}")
                raise exc
        else:
            logger.error(f"Max retries reached for task {task_id}")
            raise exc


def get_user_settings(task_id: str) -> Dict[str, Any]:
    """
    Retrieves user-specific settings and style preferences from the database.
    """
    with get_sync_db_session() as session:
        task = session.get(VideoTaskModel, task_id)
        if not task or not task.user_id:
            logger.info("No user found for task, using default styles.")
            return {
                "title_style": DEFAULT_TEXT_STYLES['title'],
                "subtitle_font_path": get_subtitle_font_path()
            }
        
        user = session.get(User, task.user_id)
        if not user or not user.settings:
            logger.info(f"No custom settings for user {task.user_id}, using defaults.")
            return {
                "title_style": DEFAULT_TEXT_STYLES['title'],
                "subtitle_font_path": get_subtitle_font_path()
            }

        settings = user.settings
        title_style = settings.get('title_style', DEFAULT_TEXT_STYLES['title'])
        
        # Get font path from settings if available
        font_name = title_style.get('font', 'Obelix Pro')
        font_path = f"/app/fonts/{font_name.replace(' ', '/')}/static/{font_name}-Regular.ttf"
        if not os.path.exists(font_path):
             font_path = f"/app/fonts/Obelix Pro.ttf" # Default fallback
        
        logger.info(f"Loaded settings for user {task.user_id}: {title_style}")
        return {
            "title_style": title_style,
            "font_path": font_path,
            "subtitle_font_path": get_subtitle_font_path()
        }


def cut_into_fragments(task_id: str, processed_video_path: str, settings_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Cut processed video into fragments. This now correctly uses the FFmpeg processor.
    """
    output_dir = f"/tmp/processed/{task_id}/fragments"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize processor
    processor = VideoProcessor(output_dir)
    
    fragments = processor.create_fragments(
        video_path=processed_video_path,
        fragment_duration=settings_dict.get("duration", 30),
        title=settings_dict.get("title", "")
    )
    return fragments


def upload_to_drive(task_id: str, fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Upload fragments to Google Drive.
    
    Args:
        task_id: Task ID
        fragments: List of fragments to upload
        
    Returns:
        List of upload results
    """
    from app.services.google_drive import GoogleDriveService
    
    drive_service = GoogleDriveService()
    
    # Upload all fragments to target folder (no longer creates individual task folders)
    file_paths = [fragment['local_path'] for fragment in fragments]
    upload_results = drive_service.upload_multiple_files(file_paths, task_id=task_id)
    
    logger.info(f"Uploaded {len(upload_results)} fragments to Google Drive for task {task_id}")
    return upload_results


def log_to_sheets(
    task_id: str,
    download_result: Dict[str, Any],
    fragments: List[Dict[str, Any]],
    upload_results: List[Dict[str, Any]],
    settings_dict: Dict[str, Any],
    user_id: int
) -> Dict[str, Any]:
    """
    Log processing data to Google Sheets.
    
    Args:
        task_id: Task ID
        download_result: Download result data
        fragments: Fragment data
        upload_results: Upload results
        settings_dict: Processing settings
        user_id: User ID for logging
        
    Returns:
        Logging result
    """
    from app.services.google_sheets import GoogleSheetsService
    
    sheets_service = GoogleSheetsService()
    
    # Get successful upload links (use direct download URLs)
    drive_links = [r.get('direct_url', r.get('file_url', '')) for r in upload_results if r.get('success')]
    
    # Log to sheets
    result = sheets_service.log_video_processing(
        task_id=task_id,
        user_id=user_id,
        video_title=download_result.get('title', 'Unknown'),
        source_url=download_result.get('url', ''),
        fragments_count=len(fragments),
        total_duration=sum(f.get('duration', 0) for f in fragments if isinstance(f, dict) and 'duration' in f),
        settings=settings_dict,
        drive_links=drive_links
    )
    
    logger.info(f"Logged processing data to Google Sheets for task {task_id}")
    return result


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files.
    
    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")


@shared_task(base=VideoTask)
def cleanup_stale_tasks() -> Dict[str, Any]:
    """
    Cleanup stale/hanging tasks that are stuck in processing state.
    
    Returns:
        Dict with cleanup results
    """
    logger.info("Starting cleanup of stale tasks")
    
    try:
        from datetime import datetime, timedelta
        
        # Consider tasks stuck in processing for more than 4 hours as stale (увеличено для больших видео)
        cutoff_time = datetime.utcnow() - timedelta(hours=4)
        
        tasks_cleaned = 0
        
        with get_sync_db_session() as session:
            # Find stale tasks
            from sqlalchemy import select, update
            
            result = session.execute(
                select(VideoTaskModel).where(
                    VideoTaskModel.status.in_([
                        VideoStatus.PENDING, 
                        VideoStatus.DOWNLOADING, 
                        VideoStatus.PROCESSING, 
                        VideoStatus.UPLOADING
                    ]),
                    VideoTaskModel.created_at <= cutoff_time
                )
            )
            
            stale_tasks = result.scalars().all()
            
            for task in stale_tasks:
                # Update task status to failed
                task.status = VideoStatus.FAILED
                task.error_message = "Задача отменена из-за превышения времени выполнения (автоочистка)"
                tasks_cleaned += 1
                logger.info(f"Cleaned up stale task {task.id} (created at {task.created_at})")
            
            session.commit()
        
        cleanup_result = {
            "tasks_cleaned": tasks_cleaned,
            "cleanup_time": datetime.utcnow().isoformat()
        }
        
        if tasks_cleaned > 0:
            logger.info(f"Stale tasks cleanup completed: {cleanup_result}")
        
        return cleanup_result
        
    except Exception as exc:
        logger.error(f"Stale tasks cleanup failed: {exc}")
        raise


@shared_task(base=VideoTask)
def cleanup_old_files() -> Dict[str, Any]:
    """
    Cleanup old temporary files.
    
    Returns:
        Dict with cleanup results
    """
    logger.info("Starting cleanup of old files")
    
    try:
        import shutil
        from datetime import datetime, timedelta
        
        # Cleanup directories
        cleanup_dirs = ["/tmp/videos", "/tmp/processed"]
        files_deleted = 0
        space_freed_mb = 0
        
        cutoff_time = datetime.now() - timedelta(hours=24)  # Delete files older than 24 hours
        
        for cleanup_dir in cleanup_dirs:
            if os.path.exists(cleanup_dir):
                for root, dirs, files in os.walk(cleanup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_time < cutoff_time:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                files_deleted += 1
                                space_freed_mb += file_size / (1024 * 1024)
                        except Exception as e:
                            logger.warning(f"Failed to delete {file_path}: {e}")
        
        cleanup_result = {
            "files_deleted": files_deleted,
            "space_freed_mb": round(space_freed_mb, 2),
            "cleanup_time": datetime.now().isoformat()
        }
        
        logger.info(f"Cleanup completed: {cleanup_result}")
        return cleanup_result
        
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        raise


@shared_task(base=VideoTask)
def update_statistics() -> Dict[str, Any]:
    """
    Update user statistics.
    
    Returns:
        Dict with statistics update results
    """
    logger.info("Updating user statistics")
    
    try:
        from datetime import datetime
        
        # TODO: Implement actual statistics calculation
        # For now, return mock statistics data
        stats_result = {
            "users_updated": 0,
            "tasks_processed": 0,
            "update_time": datetime.now().isoformat()
        }
        
        logger.info(f"Statistics updated: {stats_result}")
        return stats_result
        
    except Exception as exc:
        logger.error(f"Statistics update failed: {exc}")
        raise 


@shared_task(base=VideoTask)
def send_completion_notification(user_id: int, task_id: str, fragments_count: int) -> Dict[str, Any]:
    """
    Send completion notification to user with Drive links file.
    
    Args:
        user_id: User ID to send notification to
        task_id: Completed task ID
        fragments_count: Number of fragments created
        
    Returns:
        Dict with notification results
    """
    logger.info(f"Sending completion notification for task {task_id} to user {user_id}")
    
    try:
        import asyncio
        import tempfile
        from aiogram import Bot
        from aiogram.types import FSInputFile
        from app.config.settings import settings
        from app.bot.keyboards.main_menu import get_back_keyboard
        
        # Get actual fragments count and drive links from database
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return {"error": "Task not found"}
            
            fragments = session.query(VideoFragment).filter_by(task_id=task_id).all()
            actual_fragments_count = len(fragments)
            
            # Calculate total duration and size for short video detection
            total_duration = sum(float(f.duration or 0) for f in fragments)
            total_size_mb = sum((f.size_bytes or 0) for f in fragments) / (1024 * 1024)
            logger.info(f"Task {task_id}: {actual_fragments_count} fragments, {total_duration:.1f}s total, {total_size_mb:.1f}MB")
            
            # Check if we should send videos directly to chat
            should_send_files = (
                actual_fragments_count <= 3 and 
                total_duration <= 20 and  # 20 seconds total
                total_size_mb <= 40 and   # 40MB total (Telegram limit is 50MB)
                all(os.path.exists(f.local_path) for f in fragments if f.local_path)
            )
            
            logger.info(f"Short video check for task {task_id}: send_files={should_send_files}")
            
            # Get drive links
            drive_links = []
            logger.info(f"Processing {len(fragments)} fragments for task {task_id}")
            
            for fragment in fragments:
                # Получаем drive_url из базы данных или из metadata как fallback
                drive_url = fragment.drive_url
                view_url = None
                
                # Fallback: если drive_url пустой, пытаемся получить из metadata
                if not drive_url and fragment.metadata and isinstance(fragment.metadata, dict):
                    view_url = fragment.metadata.get('view_url')
                    if view_url:
                        drive_url = view_url
                        logger.info(f"Using view_url from metadata for fragment {fragment.fragment_number}")
                
                if drive_url:
                    # Проверяем, является ли ссылка прямой ссылкой для скачивания
                    if "drive.google.com/uc?id=" in drive_url:
                        link_type = "📥 Прямая ссылка"
                    else:
                        link_type = "👁️ Ссылка для просмотра"
                    
                    drive_links.append(f"Фрагмент {fragment.fragment_number}: {drive_url}")
                    logger.info(f"Added link for fragment {fragment.fragment_number}: {link_type}")
                    
                    # Добавляем view URL если есть в метаданных и отличается от основной ссылки
                    if (fragment.metadata and isinstance(fragment.metadata, dict) and 
                        fragment.metadata.get('view_url') and 
                        fragment.metadata.get('view_url') != drive_url):
                        view_url = fragment.metadata.get('view_url')
                        drive_links.append(f"  └ Просмотр: {view_url}")
                else:
                    logger.warning(f"No drive URL found for fragment {fragment.fragment_number} (ID: {fragment.id})")
            
            logger.info(f"Collected {len(drive_links)} drive links for notification")
        
        async def send_notification():
            bot = Bot(token=settings.telegram_bot_token.get_secret_value())
            
            # Create links file if we have drive links
            links_file_path = None
            if drive_links:
                logger.info(f"Creating links file with {len(drive_links)} links")
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                        f.write(f"🎬 Ссылки на обработанные видео\n")
                        f.write(f"📋 ID задачи: {task_id}\n")
                        f.write(f"📊 Всего фрагментов: {actual_fragments_count}\n")
                        f.write(f"📅 Дата создания: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        
                        f.write("💡 ИНФОРМАЦИЯ О ССЫЛКАХ:\n")
                        f.write("• Прямые ссылки (📥) - для автоматического скачивания ботами\n")
                        f.write("• Ссылки просмотра (👁️) - для открытия в браузере\n\n")
                        
                        for link in drive_links:
                            # Определяем тип ссылки и добавляем эмодзи
                            if "drive.google.com/uc?id=" in link:
                                f.write(f"📥 {link}\n")
                            elif "drive.google.com/file/d/" in link:
                                f.write(f"👁️ {link}\n")
                            else:
                                f.write(f"{link}\n")
                        
                        f.write(f"\n✅ Все файлы готовы к использованию!")
                        f.write(f"\n🤖 Прямые ссылки совместимы с ботами для автоматического скачивания")
                        links_file_path = f.name
                    
                    logger.info(f"Links file created successfully at: {links_file_path}")
                except Exception as e:
                    logger.error(f"Failed to create links file: {e}")
            else:
                logger.warning(f"No drive links found for task {task_id}, file will not be created")
            
            text = f"""
✅ <b>Обработка завершена!</b>

📋 ID задачи: <code>{task_id}</code>
📊 Создано фрагментов: {actual_fragments_count}
⏱️ Общая длительность: {total_duration:.1f} сек

<b>Результаты:</b>
• {actual_fragments_count} фрагментов в формате 9:16
• Качественная обработка видео
• Готово к использованию
• 🤖 Прямые ссылки для ботов (общедоступные)

{f"📱 Короткие видео отправлены прямо в чат!" if should_send_files else "📁 Файлы загружены на Google Drive с публичным доступом"}
{f"📁 + дополнительно ссылки на Google Drive" if should_send_files and drive_links else ""}
            """
            
            try:
                # Send main notification
                logger.info(f"Sending main notification to user {user_id}")
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=get_back_keyboard("main_menu"),
                    parse_mode="HTML"
                )
                logger.info(f"Main notification sent successfully to user {user_id}")
                
                # Send links file if available
                if links_file_path and drive_links:
                    logger.info(f"Sending links file to user {user_id}: {links_file_path}")
                    try:
                        document = FSInputFile(links_file_path, filename=f"video_links_{task_id[:8]}.txt")
                        await bot.send_document(
                            chat_id=user_id,
                            document=document,
                            caption="📎 Файл со ссылками на все фрагменты"
                        )
                        logger.info(f"Links file sent successfully to user {user_id}")
                    except Exception as doc_error:
                        logger.error(f"Failed to send links file to user {user_id}: {doc_error}")
                    
                    # Clean up temp file
                    try:
                        import os
                        os.unlink(links_file_path)
                        logger.info(f"Cleaned up temp file: {links_file_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp file {links_file_path}: {cleanup_error}")
                else:
                    if not links_file_path:
                        logger.warning(f"No links file to send to user {user_id}")
                    if not drive_links:
                        logger.warning(f"No drive links to send to user {user_id}")
                
                # Send short videos directly to chat if applicable
                if should_send_files:
                    logger.info(f"Sending {actual_fragments_count} short video files directly to user {user_id}")
                    files_sent = 0
                    
                    for fragment in fragments:
                        if fragment.local_path and os.path.exists(fragment.local_path):
                            try:
                                # Prepare video file for sending
                                video_file = FSInputFile(
                                    fragment.local_path, 
                                    filename=f"shorts_{fragment.fragment_number}_{task_id[:8]}.mp4"
                                )
                                
                                # Create caption with fragment info
                                duration_text = f"{fragment.duration:.1f}s" if fragment.duration else "~"
                                size_text = f"{(fragment.size_bytes / (1024*1024)):.1f}MB" if fragment.size_bytes else "~"
                                
                                caption = f"🎬 Фрагмент {fragment.fragment_number}/{actual_fragments_count}\n"
                                caption += f"⏱️ Длительность: {duration_text}\n"
                                caption += f"📊 Размер: {size_text}\n"
                                caption += f"🎯 Готов к публикации в Shorts!"
                                
                                # Send video file
                                await bot.send_video(
                                    chat_id=user_id,
                                    video=video_file,
                                    caption=caption,
                                    supports_streaming=True,
                                    width=1080,  # Shorts width
                                    height=1920  # Shorts height
                                )
                                
                                files_sent += 1
                                logger.info(f"Sent video file {fragment.fragment_number} to user {user_id}")
                                
                            except Exception as video_error:
                                logger.error(f"Failed to send video file {fragment.fragment_number} to user {user_id}: {video_error}")
                    
                    if files_sent > 0:
                        # Send summary message
                        summary_text = f"📱 <b>Готово!</b>\n\n"
                        summary_text += f"Отправлено {files_sent} видео прямо в чат.\n"
                        summary_text += f"Также доступны ссылки на Google Drive выше.\n\n"
                        summary_text += f"💡 <i>Короткие видео (до 20 сек) отправляются прямо в чат для удобства!</i>"
                        
                        await bot.send_message(
                            chat_id=user_id,
                            text=summary_text,
                            parse_mode="HTML"
                        )
                        logger.info(f"Sent summary message to user {user_id} for {files_sent} files")
                    else:
                        logger.warning(f"No video files were sent to user {user_id} despite should_send_files=True")
                else:
                    logger.info(f"Video files not sent to user {user_id} - criteria not met (should_send_files=False)")
                
                logger.info(f"Completion notification sent to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
                if links_file_path:
                    try:
                        import os
                        os.unlink(links_file_path)
                    except:
                        pass
            finally:
                await bot.session.close()
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_notification())
        loop.close()
        
        return {
            "user_id": user_id,
            "task_id": task_id,
            "notification_sent": True,
            "fragments_count": actual_fragments_count
        }
        
    except Exception as exc:
        logger.error(f"Failed to send completion notification: {exc}")
        return {
            "user_id": user_id,
            "task_id": task_id,
            "notification_sent": False,
            "error": str(exc)
        } 