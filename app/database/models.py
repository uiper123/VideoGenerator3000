"""
SQLAlchemy models for the Video Bot application.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime, 
    Text, JSON, Numeric, ForeignKey, Enum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.config.constants import VideoStatus, UserRole


Base = declarative_base()


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    video_tasks = relationship("VideoTask", back_populates="user")
    statistics = relationship("UserStatistic", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(part for part in parts if part)

    @property
    def display_name(self) -> str:
        """Get user's display name."""
        return self.full_name or self.username or f"User {self.id}"


class VideoTask(Base):
    """Video processing task model."""
    __tablename__ = "video_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    source_url = Column(Text, nullable=True)
    original_filename = Column(String(500), nullable=True)
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)
    settings = Column(JSON, default=dict)
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    video_metadata = Column(JSON, default=dict)  # Video metadata (duration, resolution, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="video_tasks")
    fragments = relationship("VideoFragment", back_populates="task", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_video_tasks_user_id", "user_id"),
        Index("ix_video_tasks_status", "status"),
        Index("ix_video_tasks_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<VideoTask(id={self.id}, status={self.status})>"

    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status in [VideoStatus.COMPLETED, VideoStatus.FAILED]

    @property
    def duration_seconds(self) -> Optional[int]:
        """Get video duration in seconds."""
        return self.video_metadata.get("duration") if self.video_metadata else None

    @property
    def total_fragments(self) -> int:
        """Get total number of fragments."""
        return len(self.fragments)


class VideoFragment(Base):
    """Video fragment model."""
    __tablename__ = "video_fragments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("video_tasks.id"), nullable=False)
    fragment_number = Column(Integer, nullable=False)
    filename = Column(String(500), nullable=False)
    local_path = Column(String(1000), nullable=True)
    drive_url = Column(Text, nullable=True)
    preview_url = Column(Text, nullable=True)
    duration = Column(Numeric(8, 3), nullable=True)  # Duration in seconds
    size_bytes = Column(BigInteger, nullable=True)
    start_time = Column(Numeric(8, 3), nullable=True)  # Start time in original video
    end_time = Column(Numeric(8, 3), nullable=True)  # End time in original video
    has_subtitles = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    task = relationship("VideoTask", back_populates="fragments")

    # Indexes
    __table_args__ = (
        Index("ix_video_fragments_task_id", "task_id"),
        Index("ix_video_fragments_fragment_number", "fragment_number"),
    )

    def __repr__(self):
        return f"<VideoFragment(id={self.id}, fragment_number={self.fragment_number})>"

    @property
    def size_mb(self) -> Optional[float]:
        """Get file size in MB."""
        return round(self.size_bytes / (1024 * 1024), 2) if self.size_bytes else None


class UserStatistic(Base):
    """User statistics model."""
    __tablename__ = "user_statistics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    videos_processed = Column(Integer, default=0)
    total_duration = Column(Numeric(10, 3), default=0)  # Total duration in seconds
    total_size_bytes = Column(BigInteger, default=0)
    fragments_created = Column(Integer, default=0)

    # Relationship
    user = relationship("User", back_populates="statistics")

    # Indexes
    __table_args__ = (
        Index("ix_user_statistics_user_id_date", "user_id", "date", unique=True),
        Index("ix_user_statistics_date", "date"),
    )

    def __repr__(self):
        return f"<UserStatistic(user_id={self.user_id}, date={self.date})>"

    @property
    def total_size_mb(self) -> float:
        """Get total size in MB."""
        return round(self.total_size_bytes / (1024 * 1024), 2)

    @property
    def avg_video_duration(self) -> Optional[float]:
        """Get average video duration."""
        if self.videos_processed > 0:
            return round(float(self.total_duration) / self.videos_processed, 2)
        return None


class SystemSetting(Base):
    """System settings model."""
    __tablename__ = "system_settings"

    key_name = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemSetting(key={self.key_name})>"


class ProcessingLog(Base):
    """Processing log model for debugging and monitoring."""
    __tablename__ = "processing_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("video_tasks.id"), nullable=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("ix_processing_logs_task_id", "task_id"),
        Index("ix_processing_logs_level", "level"),
        Index("ix_processing_logs_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ProcessingLog(id={self.id}, level={self.level})>"


class CeleryTaskResult(Base):
    """Custom Celery task result storage."""
    __tablename__ = "celery_task_results"

    id = Column(String(255), primary_key=True)  # Celery task ID
    status = Column(String(50), nullable=False)
    result = Column(JSON, nullable=True)
    date_done = Column(DateTime, nullable=True)
    traceback = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    # Index
    __table_args__ = (
        Index("ix_celery_task_results_status", "status"),
    )

    def __repr__(self):
        return f"<CeleryTaskResult(id={self.id}, status={self.status})>" 