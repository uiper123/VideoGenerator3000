"""
Video downloader using PyTube for YouTube and other sources.
"""
import os
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from pytubefix import YouTube
from pytubefix.exceptions import VideoUnavailable, RegexMatchError

logger = logging.getLogger(__name__)

# Constants
MAX_DOWNLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
SUPPORTED_SOURCES = [
    'youtube.com', 'youtu.be'
]


class DownloadError(Exception):
    """Custom exception for download errors."""
    pass


class VideoDownloader:
    """Video downloader supporting multiple sources."""
    
    def __init__(self, download_dir: str = "/tmp/videos"):
        """
        Initialize video downloader.
        
        Args:
            download_dir: Directory to save downloaded videos
        """
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
    
    def download(self, url: str, quality: str = "720p") -> Dict[str, Any]:
        """
        Download video from URL.
        
        Args:
            url: Video URL
            quality: Preferred quality
            
        Returns:
            Dict with download information
            
        Raises:
            DownloadError: If download fails
        """
        logger.info(f"Starting download from: {url}")
        
        try:
            # Check if URL is YouTube
            if self._is_youtube_url(url):
                return self._download_youtube(url, quality)
            else:
                raise DownloadError(f"Unsupported URL: {url}. Only YouTube is currently supported.")
                
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            raise DownloadError(f"Download failed: {e}")
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is from YouTube."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain in ['youtube.com', 'youtu.be']
        except:
            return False
    
    def _download_youtube(self, url: str, quality: str) -> Dict[str, Any]:
        """
        Download video from YouTube using PyTubeFix.
        
        Args:
            url: YouTube URL
            quality: Preferred quality
            
        Returns:
            Dict with download information
        """
        try:
            logger.info(f"Extracting YouTube video info from: {url}")
            
            # Create YouTube object with better error handling
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
            
            logger.info(f"Video title: {yt.title}")
            logger.info(f"Video length: {yt.length} seconds")
            
            # Check video length (max 3 hours)
            if yt.length > 10800:  # 3 hours in seconds
                raise DownloadError(f"Video too long: {yt.length} seconds (max 3 hours)")
            
            # Get quality preference mapping
            quality_preferences = {
                '4k': ['2160p', '1440p', '1080p', '720p'],
                '1080p': ['1080p', '1440p', '720p', '480p'],
                '720p': ['720p', '1080p', '480p', '360p'],
                'best': ['2160p', '1440p', '1080p', '720p', '480p'],
                'worst': ['360p', '480p', '720p']
            }
            
            preferred_qualities = quality_preferences.get(quality, quality_preferences['best'])
            logger.info(f"Looking for quality: {quality}, preference order: {preferred_qualities}")
            
            stream = None
            
            # Method 1: Try adaptive video streams first (usually higher quality)
            logger.info("Trying adaptive video streams (higher quality)...")
            for target_quality in preferred_qualities:
                adaptive_streams = yt.streams.filter(
                    adaptive=True, 
                    only_video=True, 
                    file_extension='mp4',
                    resolution=target_quality
                )
                if adaptive_streams:
                    stream = adaptive_streams.first()
                    logger.info(f"Found adaptive video stream: {stream.resolution}")
                    break
            
            # Method 2: Try progressive streams with quality preference
            if not stream:
                logger.info("No adaptive streams found, trying progressive streams...")
                for target_quality in preferred_qualities:
                    progressive_streams = yt.streams.filter(
                        progressive=True, 
                        file_extension='mp4',
                        resolution=target_quality
                    )
                    if progressive_streams:
                        stream = progressive_streams.first()
                        logger.info(f"Found progressive stream: {stream.resolution}")
                        break
            
            # Method 3: Get best available progressive stream
            if not stream:
                logger.info("Trying best available progressive streams...")
                progressive_streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
                if progressive_streams:
                    stream = progressive_streams.first()
                    logger.info(f"Found best progressive stream: {stream.resolution}")
            
            # Method 4: Get best available adaptive video stream
            if not stream:
                logger.info("Trying best available adaptive video streams...")
                adaptive_streams = yt.streams.filter(adaptive=True, only_video=True, file_extension='mp4').order_by('resolution').desc()
                if adaptive_streams:
                    stream = adaptive_streams.first()
                    logger.info(f"Found best adaptive video stream: {stream.resolution}")
            
            # Method 5: Last resort - any stream
            if not stream:
                logger.info("Trying any available streams...")
                all_streams = yt.streams.filter(file_extension='mp4').order_by('resolution').desc()
                if all_streams:
                    stream = all_streams.first()
                    logger.info(f"Found fallback stream: {getattr(stream, 'resolution', 'unknown')}")
            
            if not stream:
                raise DownloadError("No suitable video streams found")
            
            logger.info(f"Selected stream: {getattr(stream, 'resolution', 'unknown')}, {getattr(stream, 'filesize', 'unknown')} bytes")
            
            # Check file size if available
            if hasattr(stream, 'filesize') and stream.filesize and stream.filesize > MAX_DOWNLOAD_SIZE:
                raise DownloadError(f"Video too large: {stream.filesize} bytes (max 2GB)")
            
            # Download the video
            logger.info("Starting download...")
            downloaded_file = stream.download(
                output_path=self.download_dir,
                filename_prefix="youtube_"
            )
            
            logger.info(f"Download completed: {downloaded_file}")
            
            return {
                'title': yt.title,
                'duration': yt.length,
                'url': url,
                'local_path': downloaded_file,
                'file_size': os.path.getsize(downloaded_file),
                'format': 'mp4',
                'resolution': getattr(stream, 'resolution', 'unknown'),
                'description': yt.description[:500] if yt.description else '',
                'author': yt.author or 'Unknown',
                'views': yt.views or 0
            }
            
        except VideoUnavailable as e:
            logger.error(f"YouTube video unavailable: {e}")
            raise DownloadError(f"Video unavailable: {e}")
        except RegexMatchError as e:
            logger.error(f"Invalid YouTube URL: {e}")
            raise DownloadError(f"Invalid YouTube URL: {e}")
        except Exception as e:
            logger.error(f"YouTube download failed: {e}")
            # Try to provide more specific error information
            if "400" in str(e):
                raise DownloadError(f"YouTube returned 400 error - video may be restricted or unavailable: {e}")
            elif "403" in str(e):
                raise DownloadError(f"YouTube returned 403 error - access forbidden: {e}")
            else:
                raise DownloadError(f"YouTube download failed: {e}")
    
    def _select_best_stream(self, streams, quality: str):
        """
        Select the best stream based on quality preference.
        
        Args:
            streams: Available streams
            quality: Preferred quality
            
        Returns:
            Selected stream or None
        """
        # Quality mapping
        quality_order = {
            '4k': ['2160p', '1440p', '1080p', '720p', '480p', '360p'],
            '1080p': ['1080p', '720p', '1440p', '480p', '360p'],
            '720p': ['720p', '480p', '1080p', '360p'],
            'best': ['2160p', '1440p', '1080p', '720p', '480p', '360p'],
            'worst': ['360p', '480p', '720p', '1080p', '1440p', '2160p']
        }
        
        preferred_qualities = quality_order.get(quality, quality_order['best'])
        
        # Try to find stream with preferred quality
        for pref_quality in preferred_qualities:
            for stream in streams:
                if stream.resolution == pref_quality:
                    return stream
        
        # If no exact match, return highest quality available
        return streams.order_by('resolution').desc().first()
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information without downloading.
        
        Args:
            url: Video URL
            
        Returns:
            Dict with video information
        """
        try:
            if self._is_youtube_url(url):
                yt = YouTube(url)
                return {
                    'title': yt.title,
                    'duration': yt.length,
                    'description': yt.description[:500] if yt.description else '',
                    'author': yt.author or 'Unknown',
                    'views': yt.views or 0,
                    'thumbnail': yt.thumbnail_url,
                    'url': url
                }
            else:
                raise DownloadError("Unsupported URL for info extraction")
                
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise DownloadError(f"Failed to get video info: {e}")
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up downloaded file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            bool: True if successful
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup {file_path}: {e}")
            return False 