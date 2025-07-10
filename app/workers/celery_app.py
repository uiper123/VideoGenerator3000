"""
Celery application configuration for Video Bot.
"""
import os
from celery import Celery
from kombu import Exchange, Queue

from app.config.settings import settings

# Create Celery application instance
celery_app = Celery(
    "video_bot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.video_tasks",
        "app.workers.upload_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task execution - Updated for safer task handling
    task_acks_late=False,  # Changed from True to prevent duplicate execution
    task_reject_on_worker_lost=False,  # Changed from True to prevent auto-retry
    task_track_started=True,
    
    # Results
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    worker_prefetch_multiplier=1,
    
    # Task routing
    task_routes={
        'app.workers.video_tasks.download_video': {'queue': 'video_download'},
        'app.workers.video_tasks.process_video': {'queue': 'video_processing'},
        'app.workers.video_tasks.process_video_chain_optimized': {'queue': 'video_processing'},
        'app.workers.upload_tasks.upload_to_drive': {'queue': 'uploads'},
        'app.workers.upload_tasks.update_spreadsheet': {'queue': 'default'},
    },
    
    # Task queues
    task_queues=[
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('video_download', Exchange('video'), routing_key='video.download'),
        Queue('video_processing', Exchange('video'), routing_key='video.process'),
        Queue('uploads', Exchange('uploads'), routing_key='uploads.drive'),
    ],
    
    # Default queue settings
    task_default_queue='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    
    # Task annotations for rate limiting
    task_annotations={
        'app.workers.video_tasks.download_video': {'rate_limit': '5/m'},
        'app.workers.upload_tasks.upload_to_drive': {'rate_limit': '10/m'},
        'app.workers.upload_tasks.update_spreadsheet': {'rate_limit': '60/m'},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup_old_files': {
            'task': 'app.workers.video_tasks.cleanup_old_files',
            'schedule': 3600.0,  # Every hour
            'args': (),
        },
        'update_user_statistics': {
            'task': 'app.workers.video_tasks.update_statistics',
            'schedule': 1800.0,  # Every 30 minutes
            'args': (),
        },
        # Add task for cleaning up stale tasks
        'cleanup_stale_tasks': {
            'task': 'app.workers.video_tasks.cleanup_stale_tasks',
            'schedule': 300.0,  # Every 5 minutes
            'args': (),
        },
    },
    
    # Error handling - More conservative settings
    task_soft_time_limit=28800,  # 8 часов
    task_time_limit=28800,       # 8 часов
    task_max_retries=2,         # Reduced from 3 to 2
    task_default_retry_delay=120,  # Increased from 60 to 120 seconds
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Autodiscover tasks in modules
celery_app.autodiscover_tasks()


# Custom task base class for shared functionality
from celery import Task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class VideoTask(Task):
    """Base task class for video processing tasks."""
    
    abstract = True
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2, "countdown": 120}  # Reduced retries and increased delay
    retry_backoff = False  # Disabled exponential backoff
    retry_backoff_max = 300  # Reduced max backoff
    retry_jitter = False

    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        logger.info(f"Task {task_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        logger.error(f"Task {task_id} failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry."""
        logger.warning(f"Task {task_id} retry: {exc}")

    def retry(self, args=None, kwargs=None, exc=None, throw=True, 
              eta=None, countdown=None, max_retries=None, **options):
        """Override retry method to add additional safety checks."""
        
        # Don't retry if we've exceeded our custom max retries
        if self.request.retries >= 2:
            logger.info(f"Task {self.request.id} max retries reached, not retrying")
            if throw:
                raise exc
            return
        
        # Only retry on specific errors that are likely temporary
        if exc and not any(keyword in str(exc).lower() for keyword in 
                          ['timeout', 'connection', 'network', 'temporary', 'busy']):
            logger.info(f"Task {self.request.id} permanent error, not retrying: {exc}")
            if throw:
                raise exc
            return
        
        return super().retry(args, kwargs, exc, throw, eta, countdown, max_retries, **options)


# Set the custom task class as default
celery_app.Task = VideoTask 