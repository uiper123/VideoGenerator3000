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

from app.config.settings import settings

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
                # Use enhanced strategy with multiple fallbacks
                return self._download_youtube_enhanced(url, quality)
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
    
    def _download_youtube_enhanced(self, url: str, quality: str) -> Dict[str, Any]:
        """
        Enhanced YouTube download with multiple fallback strategies.
        
        Args:
            url: YouTube URL
            quality: Preferred quality
            
        Returns:
            Dict with download information
        """
        strategies = [
            {
                'name': 'ytdlp_with_cookies',
                'method': lambda: self._try_ytdlp_download_with_cookies(url, quality)
            },
            {
                'name': 'yt-dlp_advanced_bypass',
                'method': lambda: self._try_ytdlp_download(url, quality, [
                    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '--referer', 'https://www.youtube.com/',
                    '--add-header', 'Accept-Language:en-US,en;q=0.9',
                    '--sleep-interval', '1',
                    '--max-sleep-interval', '3',
                    '--extractor-retries', '3',
                    '--no-check-certificate'
                ])
            },
            {
                'name': 'yt-dlp_mobile_bypass', 
                'method': lambda: self._try_ytdlp_download(url, quality, [
                    '--user-agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                    '--referer', 'https://m.youtube.com/',
                    '--add-header', 'Accept-Language:en-US,en;q=0.9',
                    '--extractor-retries', '5'
                ])
            },
            {
                'name': 'pytubefix_no_token',
                'method': lambda: self._download_youtube_pytubefix(url, quality, use_po_token=False)
            },
            {
                'name': 'yt-dlp_embed_bypass',
                'method': lambda: self._try_ytdlp_download(url, quality, [
                    '--user-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    '--referer', 'https://www.youtube.com/',
                    '--add-header', 'X-Forwarded-For:8.8.8.8',
                    '--add-header', 'Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    '--sleep-interval', '2',
                    '--max-sleep-interval', '5'
                ])
            },
            {
                'name': 'pytubefix_with_token', 
                'method': lambda: self._download_youtube_pytubefix(url, quality, use_po_token=True)
            },
            {
                'name': 'yt-dlp_basic_safe',
                'method': lambda: self._try_ytdlp_download(url, quality, [
                    '--no-check-certificate',
                    '--ignore-errors',
                    '--extractor-retries', '3'
                ])
            }
        ]
        
        last_error = None
        for strategy in strategies:
            try:
                logger.info(f"Trying download strategy: {strategy['name']}")
                result = strategy['method']()
                logger.info(f"Successfully downloaded using strategy: {strategy['name']}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Strategy '{strategy['name']}' failed: {e}")
                
                # Special handling for bot detection
                if "Sign in to confirm you're not a bot" in str(e) or "bot detection" in str(e).lower():
                    logger.warning("YouTube bot detection encountered - trying next strategy")
                    continue
                    
                # For Chrome cookies error, skip to next strategy
                if "could not find chrome cookies" in str(e).lower():
                    logger.warning("Chrome cookies not available in container - skipping to next strategy")
                    continue
                    
                # For other errors, also try next strategy
                continue
        
        # If all strategies failed, try one more desperate attempt with alternative URL format
        logger.warning("All primary strategies failed, trying alternative URL formats...")
        try:
            return self._try_alternative_url_formats(url, quality)
        except Exception as alt_error:
            logger.error(f"Alternative URL formats also failed: {alt_error}")
        
        # If all strategies failed
        if last_error:
            raise DownloadError(f"All download strategies failed. YouTube может блокировать автоматическое скачивание. Попробуйте другое видео или повторите позже. Последняя ошибка: {last_error}")
        else:
            raise DownloadError("All download strategies failed with unknown errors")
    
    def _try_ytdlp_download_with_cookies(self, url: str, quality: str) -> Dict[str, Any]:
        """
        Try downloading with yt-dlp using a cookies file.
        This is the most reliable method to bypass bot detection.
        """
        cookies_file = settings.youtube_cookies_file_path
        if not cookies_file or not os.path.exists(cookies_file):
            raise DownloadError("Cookies file not configured or not found. Skipping strategy.")
            
        logger.info(f"Attempting download with cookies from: {cookies_file}")
        
        # We can reuse the main ytdlp download function and just add the cookies argument
        extra_args = ['--cookies', cookies_file]
        return self._try_ytdlp_download(url, quality, extra_args)
    
    def _try_alternative_url_formats(self, url: str, quality: str) -> Dict[str, Any]:
        """
        Try alternative URL formats and extraction methods.
        
        Args:
            url: Original YouTube URL
            quality: Preferred quality
            
        Returns:
            Dict with download information
        """
        # Extract video ID from URL
        video_id = None
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        
        if not video_id:
            raise DownloadError("Could not extract video ID from URL")
        
        # Try different URL formats
        alternative_urls = [
            f"https://youtu.be/{video_id}",
            f"https://www.youtube.com/watch?v={video_id}",
            f"https://m.youtube.com/watch?v={video_id}",
            f"https://youtube.com/watch?v={video_id}"
        ]
        
        for alt_url in alternative_urls:
            if alt_url == url:  # Skip the original URL
                continue
                
            try:
                logger.info(f"Trying alternative URL format: {alt_url}")
                return self._try_ytdlp_download(alt_url, quality, [
                    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    '--sleep-interval', '2',
                    '--extractor-retries', '2'
                ])
            except Exception as e:
                logger.warning(f"Alternative URL {alt_url} failed: {e}")
                continue
        
        raise DownloadError("All alternative URL formats failed")
    
    def _download_youtube_pytubefix(self, url: str, quality: str, use_po_token: bool = False) -> Dict[str, Any]:
        """
        Download video from YouTube using PyTubeFix with specific token settings.
        
        Args:
            url: YouTube URL
            quality: Preferred quality
            use_po_token: Whether to use PO token
            
        Returns:
            Dict with download information
        """
        try:
            logger.info(f"Extracting YouTube video info from: {url} (use_po_token={use_po_token})")
            
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=False, use_po_token=use_po_token)
            
            # Test if we can access basic video info
            _ = yt.title
            logger.info(f"Successfully initialized YouTube object (use_po_token={use_po_token})")
            
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
                'views': yt.views or 0,
                'thumbnail': getattr(yt, 'thumbnail_url', '')
            }
            
        except VideoUnavailable as e:
            logger.error(f"YouTube video unavailable: {e}")
            raise DownloadError(f"Video unavailable: {e}")
        except RegexMatchError as e:
            logger.error(f"Invalid YouTube URL: {e}")
            raise DownloadError(f"Invalid YouTube URL: {e}")
        except Exception as e:
            logger.error(f"PyTubeFix download failed: {e}")
            # Try to provide more specific error information
            if "400" in str(e):
                raise DownloadError(f"YouTube returned 400 error - video may be restricted or unavailable: {e}")
            elif "403" in str(e):
                raise DownloadError(f"YouTube returned 403 error - access forbidden: {e}")
            else:
                raise DownloadError(f"PyTubeFix download failed: {e}")
    
    def _try_ytdlp_download(self, url: str, quality: str, extra_args: list) -> Dict[str, Any]:
        """
        Try downloading with specific yt-dlp arguments.
        
        Args:
            url: YouTube URL
            quality: Preferred quality  
            extra_args: Additional yt-dlp arguments
            
        Returns:
            Dict with download information
        """
        # First, get video info with timeout and better error handling
        info_cmd = [
            'yt-dlp',
            '--no-warnings',
            '--dump-json',
            '--no-playlist',
            '--ignore-errors',
            '--socket-timeout', '30'
        ] + extra_args + [url]
        
        logger.info("Getting video information with yt-dlp...")
        try:
            result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            raise DownloadError("yt-dlp info extraction timed out")
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "Sign in to confirm you're not a bot" in error_msg:
                raise DownloadError(f"YouTube bot detection - need authentication")
            elif "Video unavailable" in error_msg:
                raise DownloadError(f"Video unavailable") 
            elif "Private video" in error_msg:
                raise DownloadError(f"Video is private")
            elif "removed by the uploader" in error_msg:
                raise DownloadError(f"Video was removed by uploader")
            raise DownloadError(f"yt-dlp info extraction failed: {error_msg}")
        
        try:
            video_info = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise DownloadError(f"Failed to parse video info: {e}")
        
        # Check video length (max 3 hours)
        duration = video_info.get('duration', 0)
        if duration > 10800:  # 3 hours in seconds
            raise DownloadError(f"Video too long: {duration} seconds (max 3 hours)")
        
        # Set up quality format selector with better options
        quality_formats = {
            '4k': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]', 
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'best': 'bestvideo+bestaudio/best',
            'worst': 'worst'
        }
        
        format_selector = quality_formats.get(quality, 'bestvideo[height<=1080]+bestaudio/best[height<=1080]')
        
        # Generate output filename
        safe_title = "".join(c for c in video_info.get('title', 'video') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_filename = f"ytdlp_{safe_title[:50]}_{uuid.uuid4().hex[:8]}.%(ext)s"
        output_path = os.path.join(self.download_dir, output_filename)
        
        # Download the video with improved options
        download_cmd = [
            'yt-dlp',
            '--no-warnings',
            '--no-playlist',
            '--format', format_selector,
            '--output', output_path,
            '--merge-output-format', 'mp4',
            '--max-filesize', '2G',
            '--retries', '5',
            '--fragment-retries', '5',
            '--ignore-errors',
            '--no-check-certificate',
            '--socket-timeout', '30',
            '--extractor-retries', '3'
        ] + extra_args + [url]
        
        logger.info(f"Downloading video with yt-dlp...")
        try:
            result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=1200)  # 20 minute timeout
        except subprocess.TimeoutExpired:
            raise DownloadError("yt-dlp download timed out")
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "Sign in to confirm you're not a bot" in error_msg:
                raise DownloadError(f"YouTube bot detection - authentication required")
            elif "Video unavailable" in error_msg:
                raise DownloadError(f"Video unavailable")
            raise DownloadError(f"yt-dlp download failed: {error_msg}")
        
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
            'views': video_info.get('view_count', 0),
            'thumbnail': video_info.get('thumbnail', '')
        }
    
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
                '--ignore-errors',
                '--socket-timeout', '30',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '--referer', 'https://www.youtube.com/',
                url
            ]
            
            result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "Sign in to confirm you're not a bot" in error_msg:
                    raise DownloadError("YouTube bot detection - authentication required")
                elif "Video unavailable" in error_msg:
                    raise DownloadError("Video unavailable")
                elif "Private video" in error_msg:
                    raise DownloadError("Video is private")
                raise DownloadError(f"Failed to get video info: {error_msg}")
            
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
            
        except subprocess.TimeoutExpired:
            raise DownloadError("Video info extraction timed out")
        except json.JSONDecodeError as e:
            raise DownloadError(f"Failed to parse video info: {e}")
        except Exception as e:
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