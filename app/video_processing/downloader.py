"""
Video downloader using PyTube for YouTube and other sources.
"""
import os
import logging
import subprocess
import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import ffmpeg
import uuid

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
                try:
                    return self._download_youtube(url, quality)
                except Exception as e:
                    logger.warning(f"PyTubeFix download failed: {e}")
                    logger.info("Attempting fallback with yt-dlp...")
                    return self._download_youtube_ytdlp(url, quality)
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
    
    def _merge_audio_video(self, video_path: str, audio_path: str, output_path: str):
        """Merge video and audio files using ffmpeg-python."""
        try:
            logger.info(f"Merging video {video_path} and audio {audio_path}")
            
            input_video = ffmpeg.input(video_path)
            input_audio = ffmpeg.input(audio_path)
            
            (
                ffmpeg
                .output(input_video.video, input_audio.audio, output_path, vcodec='copy', acodec='aac')
                .run(overwrite_output=True, quiet=True)
            )
            
            logger.info(f"Merged file saved to {output_path}")
            
            # Clean up temporary files
            os.remove(video_path)
            os.remove(audio_path)
            
        except ffmpeg.Error as e:
            logger.error(f"ffmpeg error during merge: {e.stderr.decode() if e.stderr else str(e)}")
            raise DownloadError(f"Failed to merge video and audio: {e}")
    
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
            
            # First try without PO token (more reliable for most cases)
            yt = None
            try:
                logger.info("Attempting download without PO token...")
                yt = YouTube(url, use_oauth=False, allow_oauth_cache=False, use_po_token=False)
                # Test if we can access basic video info
                _ = yt.title
                logger.info("Successfully initialized YouTube object without PO token")
            except Exception as e:
                logger.warning(f"Failed without PO token: {e}")
                try:
                    logger.info("Attempting download with PO token...")
                    yt = YouTube(url, use_oauth=False, allow_oauth_cache=False, use_po_token=True)
                    _ = yt.title
                    logger.info("Successfully initialized YouTube object with PO token")
                except Exception as e2:
                    logger.error(f"Failed with PO token: {e2}")
                    raise DownloadError(f"Could not initialize YouTube downloader: {e2}")
            
            if not yt:
                raise DownloadError("Failed to initialize YouTube downloader")
            
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
            
            # Check if selected stream is adaptive (video only)
            is_adaptive = stream.is_adaptive
            
            # Check file size if available
            if hasattr(stream, 'filesize') and stream.filesize and stream.filesize > MAX_DOWNLOAD_SIZE:
                raise DownloadError(f"Video too large: {stream.filesize} bytes (max 2GB)")
            
            # Download the video
            logger.info("Starting video stream download...")
            
            # Use a temporary filename for the video part if merging is needed
            video_filename_prefix = f"video_{uuid.uuid4()}" if is_adaptive else "youtube_"
            
            video_file = stream.download(
                output_path=self.download_dir,
                filename_prefix=video_filename_prefix
            )
            logger.info(f"Video download completed: {video_file}")
            
            final_video_path = video_file
            
            # If adaptive, download audio and merge
            if is_adaptive:
                logger.info("Adaptive stream detected, downloading best audio...")
                
                audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc().first()
                
                if audio_stream:
                    logger.info(f"Found audio stream: {audio_stream.abr}, {audio_stream.filesize} bytes")
                    
                    # Download audio with a temporary filename
                    audio_file = audio_stream.download(
                        output_path=self.download_dir,
                        filename_prefix=f"audio_{uuid.uuid4()}"
                    )
                    logger.info(f"Audio download completed: {audio_file}")
                    
                    # Define final merged output path
                    final_filename = f"youtube_{yt.title.replace('/', '_').replace(' ', '_')}.mp4"
                    merged_output_path = os.path.join(self.download_dir, final_filename)
                    
                    # Merge video and audio
                    self._merge_audio_video(video_file, audio_file, merged_output_path)
                    final_video_path = merged_output_path
                    
                else:
                    logger.warning("No audio stream found for adaptive video. The final video will be silent.")
            
            logger.info(f"Final video file available at: {final_video_path}")
            
            return {
                'title': yt.title,
                'duration': yt.length,
                'url': url,
                'local_path': final_video_path,
                'file_size': os.path.getsize(final_video_path),
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
    
    def _download_youtube_ytdlp(self, url: str, quality: str) -> Dict[str, Any]:
        """
        Download video from YouTube using yt-dlp as fallback.
        
        Args:
            url: YouTube URL
            quality: Preferred quality
            
        Returns:
            Dict with download information
        """
        try:
            logger.info(f"Using yt-dlp to download from: {url}")
            
            # First, get video info
            info_cmd = [
                'yt-dlp',
                '--no-warnings',
                '--dump-json',
                '--no-playlist',
                url
            ]
            
            logger.info("Getting video information with yt-dlp...")
            result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise DownloadError(f"yt-dlp info extraction failed: {result.stderr}")
            
            video_info = json.loads(result.stdout)
            
            # Check video length (max 3 hours)
            duration = video_info.get('duration', 0)
            if duration > 10800:  # 3 hours in seconds
                raise DownloadError(f"Video too long: {duration} seconds (max 3 hours)")
            
            # Set up quality format selector
            quality_formats = {
                '4k': 'best[height<=2160]',
                '1080p': 'best[height<=1080]',
                '720p': 'best[height<=720]',
                'best': 'best',
                'worst': 'worst'
            }
            
            format_selector = quality_formats.get(quality, 'best[height<=1080]')
            
            # Generate output filename
            safe_title = "".join(c for c in video_info.get('title', 'video') if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_filename = f"ytdlp_{safe_title[:50]}_{uuid.uuid4().hex[:8]}.%(ext)s"
            output_path = os.path.join(self.download_dir, output_filename)
            
            # Download the video
            download_cmd = [
                'yt-dlp',
                '--no-warnings',
                '--no-playlist',
                '--format', format_selector,
                '--output', output_path,
                '--merge-output-format', 'mp4',
                '--write-auto-subs',
                '--sub-lang', 'en,ru',
                '--embed-subs',
                '--max-filesize', '2G',
                url
            ]
            
            logger.info(f"Downloading video with yt-dlp: {' '.join(download_cmd)}")
            result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                raise DownloadError(f"yt-dlp download failed: {result.stderr}")
            
            # Find the downloaded file
            downloaded_files = []
            for file in os.listdir(self.download_dir):
                if file.startswith('ytdlp_') and file.endswith('.mp4'):
                    downloaded_files.append(os.path.join(self.download_dir, file))
            
            if not downloaded_files:
                raise DownloadError("Downloaded file not found")
            
            # Get the most recent file (in case of multiple)
            final_video_path = max(downloaded_files, key=os.path.getctime)
            
            logger.info(f"yt-dlp download completed: {final_video_path}")
            
            return {
                'title': video_info.get('title', 'Unknown'),
                'duration': duration,
                'url': url,
                'local_path': final_video_path,
                'file_size': os.path.getsize(final_video_path),
                'format': 'mp4',
                'resolution': f"{video_info.get('height', 'unknown')}p",
                'description': video_info.get('description', '')[:500],
                'author': video_info.get('uploader', 'Unknown'),
                'views': video_info.get('view_count', 0)
            }
            
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp download timed out")
            raise DownloadError("Download timed out")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse yt-dlp info: {e}")
            raise DownloadError(f"Failed to parse video info: {e}")
        except Exception as e:
            logger.error(f"yt-dlp download failed: {e}")
            raise DownloadError(f"yt-dlp download failed: {e}")
    
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
                # Try PyTubeFix first, then fallback to yt-dlp
                try:
                    yt = YouTube(url, use_oauth=False, allow_oauth_cache=False, use_po_token=False)
                    return {
                        'title': yt.title,
                        'duration': yt.length,
                        'description': yt.description[:500] if yt.description else '',
                        'author': yt.author or 'Unknown',
                        'views': yt.views or 0,
                        'thumbnail': yt.thumbnail_url,
                        'url': url
                    }
                except Exception as e:
                    logger.warning(f"PyTubeFix info extraction failed: {e}")
                    logger.info("Attempting info extraction with yt-dlp...")
                    return self._get_video_info_ytdlp(url)
            else:
                raise DownloadError("Unsupported URL for info extraction")
                
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise DownloadError(f"Failed to get video info: {e}")
    
    def _get_video_info_ytdlp(self, url: str) -> Dict[str, Any]:
        """
        Get video information using yt-dlp as fallback.
        
        Args:
            url: Video URL
            
        Returns:
            Dict with video information
        """
        try:
            info_cmd = [
                'yt-dlp',
                '--no-warnings',
                '--dump-json',
                '--no-playlist',
                url
            ]
            
            result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise DownloadError(f"yt-dlp info extraction failed: {result.stderr}")
            
            video_info = json.loads(result.stdout)
            
            return {
                'title': video_info.get('title', 'Unknown'),
                'duration': video_info.get('duration', 0),
                'description': video_info.get('description', '')[:500],
                'author': video_info.get('uploader', 'Unknown'),
                'views': video_info.get('view_count', 0),
                'thumbnail': video_info.get('thumbnail', ''),
                'url': url
            }
            
        except Exception as e:
            logger.error(f"yt-dlp info extraction failed: {e}")
            raise DownloadError(f"yt-dlp info extraction failed: {e}")
    
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