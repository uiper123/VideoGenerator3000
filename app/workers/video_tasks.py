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
from app.config.constants import VideoStatus
from app.config.settings import settings
from app.database.models import VideoTask as VideoTaskModel, VideoFragment
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
        
        # Initialize downloader
        downloader = VideoDownloader(download_dir)
        
        # Download video
        download_result = downloader.download(url, quality)
        
        # Update task with metadata
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.metadata = {
                    "title": download_result["title"],
                    "duration": download_result["duration"],
                    "size_bytes": download_result["file_size"],
                    "format": download_result["format"],
                    "resolution": download_result["resolution"],
                    "fps": 30,  # Default FPS for PyTube
                    "thumbnail": download_result.get("thumbnail"),
                    "description": download_result.get("description", ""),
                    "uploader": download_result.get("author", "")
                }
                task.progress = 100
                session.commit()
        
        logger.info(f"Video download completed for task {task_id}")
        return download_result
        
    except Exception as exc:
        logger.error(f"Video download failed for task {task_id}: {exc}")
        
        # Update task status to failed
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.FAILED
                task.error_message = str(exc)
                session.commit()
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)


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
def process_video_chain_optimized(self, task_id: str, url: str, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimized video processing chain: download -> full processing -> fragment cutting -> upload -> logging.
    
    Args:
        task_id: Video task ID
        url: Video URL to process
        settings_dict: Processing settings
        
    Returns:
        Dict with processing results
    """
    logger.info(f"Starting optimized video processing chain for task {task_id}")
    
    try:
        # Step 1: Download video
        logger.info(f"Step 1/5: Downloading video for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.DOWNLOADING
                task.progress = 10
                session.commit()
        
        quality = settings_dict.get("quality", "1080p")
        download_result = download_video(task_id, url, quality)
        
        # Step 2: Full video processing and fragmentation (new unified approach)
        logger.info(f"Step 2/5: Processing full video and fragmenting for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.PROCESSING
                task.progress = 30
                session.commit()
        
        processing_result = process_full_video(
            task_id=task_id,
            video_path=download_result["local_path"],
            settings_dict=settings_dict
        )
        
        # Extract fragments from the result
        fragments = processing_result.get('fragments', [])
        processed_video_path = processing_result.get('processed_video_path', '')
        
        # Save fragments to database
        for fragment in fragments:
            with get_sync_db_session() as session:
                fragment_model = VideoFragment(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    fragment_number=fragment['fragment_number'],
                    filename=fragment['filename'],
                    local_path=fragment['local_path'],
                    duration=fragment['duration'],
                    start_time=fragment['start_time'],
                    end_time=fragment.get('start_time', 0) + fragment['duration'],
                    size_bytes=fragment['size_bytes'],
                    has_subtitles=settings_dict.get('enable_subtitles', True)
                )
                session.add(fragment_model)
                session.commit()
                
                # Add ID to fragment dict for later use
                fragment['id'] = fragment_model.id
        
        # Step 3: Upload to Google Drive
        logger.info(f"Step 3/5: Uploading to Google Drive for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.UPLOADING
                task.progress = 60
                session.commit()
        
        upload_results = upload_to_drive(task_id, fragments)
        
        # Step 4: Log to Google Sheets (non-critical)
        logger.info(f"Step 4/5: Logging to Google Sheets for task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.progress = 80
                session.commit()
        
        sheets_result = {"success": False, "error": "Not attempted"}
        try:
            sheets_result = log_to_sheets(
                task_id=task_id,
                download_result=download_result,
                fragments=fragments,
                upload_results=upload_results,
                settings_dict=settings_dict
            )
            logger.info(f"Google Sheets logging completed for task {task_id}")
        except Exception as sheets_error:
            logger.warning(f"Google Sheets logging failed for task {task_id}: {sheets_error}")
            # Continue execution even if Google Sheets fails
            sheets_result = {"success": False, "error": str(sheets_error)}
        
        # Step 5: Finalize and cleanup
        logger.info(f"Step 5/5: Finalizing task {task_id}")
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.COMPLETED
                task.progress = 100
                session.commit()
                
                # Send completion notification
                send_completion_notification.apply_async(args=[task.user_id, task_id, len(fragments)])
        
        # Cleanup temporary files
        cleanup_temp_files([download_result["local_path"], processed_video_path])
        
        result = {
            "task_id": task_id,
            "status": "completed",
            "fragments_count": len(fragments),
            "total_duration": sum(f["duration"] for f in fragments),
            "total_size_bytes": sum(f["size_bytes"] for f in fragments),
            "drive_uploads": len([r for r in upload_results if r.get("success")]),
            "sheets_logged": sheets_result.get("success", False),
            "fragments": fragments
        }
        
        logger.info(f"Optimized video processing chain completed for task {task_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Optimized video processing chain failed for task {task_id}: {exc}")
        
        # Update task status to failed
        with get_sync_db_session() as session:
            task = session.get(VideoTaskModel, task_id)
            if task:
                task.status = VideoStatus.FAILED
                task.error_message = str(exc)
                session.commit()
        
        raise


def process_full_video(task_id: str, video_path: str, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process full video into professional shorts format and cut into fragments.
    This uses MoviePy for better reliability and audio/subtitle handling.
    
    Args:
        task_id: Task ID
        video_path: Path to downloaded video
        settings_dict: Processing settings
        
    Returns:
        Dict with processing results including fragments
    """
    from app.video_processing.moviepy_processor import VideoProcessorMoviePy
    import asyncio
    from app.services.user_settings import UserSettingsService
    from app.database.models import VideoTask as VideoTaskModel
    
    # Create output directory
    output_dir = f"/tmp/processed/{task_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize MoviePy processor
    processor = VideoProcessorMoviePy(output_dir)
    
    # Get user ID from task
    user_id = None
    with get_sync_db_session() as session:
        task = session.get(VideoTaskModel, task_id)
        if task:
            user_id = task.user_id
    
    # Get user style settings if user_id is available
    title_color = "white"
    title_size = "medium"
    subtitle_color = "white"
    subtitle_size = "medium"
    font_name = "DejaVu Sans Bold"
    
    if user_id:
        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            title_color = loop.run_until_complete(
                UserSettingsService.get_style_setting(user_id, 'title_style', 'color')
            )
            title_size = loop.run_until_complete(
                UserSettingsService.get_style_setting(user_id, 'title_style', 'size')
            )
            subtitle_color = loop.run_until_complete(
                UserSettingsService.get_style_setting(user_id, 'subtitle_style', 'color')
            )
            subtitle_size = loop.run_until_complete(
                UserSettingsService.get_style_setting(user_id, 'subtitle_style', 'size')
            )
            font_name = loop.run_until_complete(
                UserSettingsService.get_style_setting(user_id, 'title_style', 'font')
            )
            loop.close()
        except Exception as e:
            logger.warning(f"Failed to get user settings for {user_id}: {e}")
    
    # Get font path
    fonts = processor.get_available_fonts()
    font_path = fonts.get(font_name)
    
    # Get settings
    quality = settings_dict.get("quality", "1080p")
    title = settings_dict.get("title", "")
    fragment_duration = settings_dict.get("fragment_duration", 30)
    enable_subtitles = settings_dict.get("enable_subtitles", True)
    
    # Process full video and cut into fragments with MoviePy
    logger.info(f"Processing full video with MoviePy for task {task_id}")
    
    result = processor.process_video_with_moviepy(
        video_path=video_path,
        fragment_duration=fragment_duration,
        quality=quality,
        title=title,
        title_color=title_color,
        title_size=title_size,
        subtitle_color=subtitle_color,
        subtitle_size=subtitle_size,
        font_path=font_path,
        enable_subtitles=enable_subtitles
    )
    
    logger.info(f"Full video processed and fragmented for task {task_id}")
    return result


def cut_into_fragments(task_id: str, processed_video_path: str, settings_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Cut processed video into fragments.
    
    Args:
        task_id: Task ID
        processed_video_path: Path to processed full video
        settings_dict: Processing settings
        
    Returns:
        List of fragment information
    """
    from app.video_processing.processor import VideoProcessor
    import subprocess
    
    # Create output directory for fragments
    output_dir = f"/tmp/processed/{task_id}/fragments"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize processor
    processor = VideoProcessor(output_dir)
    
    # Get video info
    video_info = processor.get_video_info(processed_video_path)
    total_duration = video_info['duration']
    fragment_duration = settings_dict.get("fragment_duration", 30)
    
    # Calculate fragments
    if total_duration < fragment_duration:
        num_fragments = 1
        fragment_duration = int(total_duration)
    else:
        num_fragments = int(total_duration // fragment_duration)
        if total_duration % fragment_duration > 10:
            num_fragments += 1
    
    fragments = []
    
    for i in range(num_fragments):
        start_time = i * fragment_duration
        
        if i == num_fragments - 1:
            end_time = total_duration
            actual_duration = total_duration - start_time
        else:
            end_time = start_time + fragment_duration
            actual_duration = fragment_duration
        
        if actual_duration < 5:
            continue
        
        fragment_filename = f"fragment_{i+1:03d}.mp4"
        fragment_path = os.path.join(output_dir, fragment_filename)
        
        # Simple cut from processed video (no additional processing needed)
        cmd = [
            'ffmpeg',
            '-i', processed_video_path,
            '-ss', str(start_time),
            '-t', str(actual_duration),
            '-c', 'copy',  # Copy streams without re-encoding
            '-y',
            fragment_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to cut fragment {i+1}: {e}")
            continue
        
        if os.path.exists(fragment_path):
            file_size = os.path.getsize(fragment_path)
            fragment_id = str(uuid.uuid4())
            
            fragment_info = {
                'id': fragment_id,
                'task_id': task_id,
                'fragment_number': i + 1,
                'filename': fragment_filename,
                'local_path': fragment_path,
                'duration': actual_duration,
                'start_time': start_time,
                'end_time': end_time,
                'size_bytes': file_size,
                'title': settings_dict.get('title', ''),
                'subtitle_style': 'modern'
            }
            fragments.append(fragment_info)
            
            # Save fragment to database
            with get_sync_db_session() as session:
                fragment = VideoFragment(
                    id=fragment_id,
                    task_id=task_id,
                    fragment_number=i + 1,
                    filename=fragment_filename,
                    local_path=fragment_path,
                    duration=actual_duration,
                    start_time=start_time,
                    end_time=end_time,
                    size_bytes=file_size,
                    has_subtitles=settings_dict.get('enable_subtitles', True)
                )
                session.add(fragment)
                session.commit()
            
            logger.info(f"Fragment {i+1}/{num_fragments} created for task {task_id}")
    
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
    folder_name = f"VideoBot_Task_{task_id}"
    
    # Create folder for this task
    folder_result = drive_service.create_folder(folder_name)
    
    # Upload all fragments
    file_paths = [fragment['local_path'] for fragment in fragments]
    upload_results = drive_service.upload_multiple_files(file_paths, folder_name)
    
    logger.info(f"Uploaded {len(upload_results)} fragments to Google Drive for task {task_id}")
    return upload_results


def log_to_sheets(
    task_id: str,
    download_result: Dict[str, Any],
    fragments: List[Dict[str, Any]],
    upload_results: List[Dict[str, Any]],
    settings_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Log processing data to Google Sheets.
    
    Args:
        task_id: Task ID
        download_result: Download result data
        fragments: Fragment data
        upload_results: Upload results
        settings_dict: Processing settings
        
    Returns:
        Logging result
    """
    from app.services.google_sheets import GoogleSheetsService
    
    sheets_service = GoogleSheetsService()
    
    # Get successful upload links
    drive_links = [r.get('file_url', '') for r in upload_results if r.get('success')]
    
    # Log to sheets
    result = sheets_service.log_video_processing(
        task_id=task_id,
        user_id=0,  # Will be updated with actual user ID
        video_title=download_result.get('title', 'Unknown'),
        source_url=download_result.get('url', ''),
        fragments_count=len(fragments),
        total_duration=sum(f['duration'] for f in fragments),
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
    Send completion notification to user.
    
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
        from aiogram import Bot
        from app.config.settings import settings
        from app.bot.keyboards.main_menu import get_back_keyboard
        
        async def send_notification():
            bot = Bot(token=settings.telegram_bot_token)
            
            text = f"""
✅ <b>Обработка завершена!</b>

📋 ID задачи: <code>{task_id}</code>
📊 Создано фрагментов: {fragments_count}

<b>Результаты:</b>
• {fragments_count} фрагментов в формате 9:16
• Качественная обработка видео
• Готово к использованию

Файлы сохранены на сервере и готовы к скачиванию.
            """
            
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=get_back_keyboard("main_menu"),
                    parse_mode="HTML"
                )
                logger.info(f"Completion notification sent to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
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
            "notification_sent": True
        }
        
    except Exception as exc:
        logger.error(f"Failed to send completion notification: {exc}")
        return {
            "user_id": user_id,
            "task_id": task_id,
            "notification_sent": False,
            "error": str(exc)
        } 