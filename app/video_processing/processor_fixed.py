"""
Video processing module for creating professional shorts with custom fonts.
"""
import os
import subprocess
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Video processing constants
SHORTS_RESOLUTION = (1080, 1920)  # 9:16 aspect ratio for shorts
SHORTS_FPS = 30
MIN_FRAGMENT_DURATION = 10  # seconds
MAX_FRAGMENT_DURATION = 300  # 5 minutes

class VideoProcessor:
    """Video processor for creating professional shorts with custom fonts."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize video processor.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir or "/tmp/processed"
        os.makedirs(self.output_dir, exist_ok=True)
        
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video information using FFprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with video information
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise RuntimeError("No video stream found")
            
            return {
                'duration': float(data['format']['duration']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': self._parse_fps(video_stream.get('r_frame_rate', '30/1')),
                'bitrate': int(data['format'].get('bit_rate', 0)),
                'codec': video_stream['codec_name'],
                'format': data['format']['format_name']
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe failed: {e.stderr}")
            raise RuntimeError(f"Failed to get video info: {e.stderr}")
        except Exception as e:
            logger.error(f"Failed to parse video info: {e}")
            raise
    
    def _get_output_resolution(self, quality: str) -> Tuple[int, int]:
        """
        Get output resolution based on quality setting.
        
        Args:
            quality: Quality setting (720p, 1080p, 4k)
            
        Returns:
            Tuple of (width, height)
        """
        quality_map = {
            '720p': (720, 1280),   
            '1080p': (1080, 1920),  
            '4k': (2160, 3840),    
        }
        
        return quality_map.get(quality, SHORTS_RESOLUTION)
    
    def _parse_fps(self, fps_str: str) -> float:
        """Parse FPS string from FFprobe."""
        try:
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den)
            else:
                return float(fps_str)
        except:
            return 30.0
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True, timeout=10)
            subprocess.run(['ffprobe', '-version'], 
                         capture_output=True, check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _build_video_filters(self, width: int, height: int, title: str = "", font_path: str = None) -> str:
        """
        Build FFmpeg video filter string for professional shorts conversion.
        
        Args:
            width: Target width
            height: Target height
            title: Optional title to overlay at the top
            font_path: Path to custom font file
            
        Returns:
            FFmpeg filter string
        """
        filters = []
        
        # Split input into two streams for background and main video
        filters.append("[0:v]split=2[bg][main]")
        
        # Background stream: blur heavily and scale to fill entire frame
        filters.append(f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},gblur=sigma=20[bg_blurred]")
        
        # Main video stream: scale to fit in center area (leaving space for title and subtitles)
        main_height = int(height * 0.7)  # 70% of height for main video
        main_area_top = int(height * 0.15)  # 15% from top for title
        
        filters.append(f"[main]scale='min({width},iw*{main_height}/ih)':'min({main_height},ih)'[main_scaled]")
        
        # Overlay main video on blurred background
        filters.append(f"[bg_blurred][main_scaled]overlay=(W-w)/2:{main_area_top}[with_main]")
        
        # Add title overlay if provided
        if title:
            # Use custom font if provided, otherwise use default
            if font_path and os.path.exists(font_path):
                fontfile = font_path
            else:
                fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            title_escaped = title.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
            title_filter = f"drawtext=text='{title_escaped}':fontfile={fontfile}:fontsize={int(height*0.04)}:fontcolor=white:x=(w-text_w)/2:y={int(height*0.05)}:box=1:boxcolor=black@0.7:boxborderw=10"
            filters.append(f"[with_main]{title_filter}[output]")
        else:
            # If no title, rename the final output
            filters.append("[with_main]null[output]")
        
        return ";".join(filters)
    
    def get_available_fonts(self) -> Dict[str, str]:
        """
        Get available fonts from the fonts directory.
        
        Returns:
            Dict mapping font names to font file paths
        """
        fonts = {}
        
        # Default system fonts
        system_fonts = {
            "DejaVu Sans Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "DejaVu Sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "Liberation Sans Bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "Liberation Sans": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        }
        
        # Add system fonts that exist
        for name, path in system_fonts.items():
            if os.path.exists(path):
                fonts[name] = path
        
        # Custom fonts from fonts directory
        fonts_dir = "/app/fonts"
        if os.path.exists(fonts_dir):
            for font_family in os.listdir(fonts_dir):
                family_path = os.path.join(fonts_dir, font_family)
                if os.path.isdir(family_path):
                    # Look for font files in static subdirectory
                    static_path = os.path.join(family_path, "static")
                    if os.path.exists(static_path):
                        for font_file in os.listdir(static_path):
                            if font_file.endswith(('.ttf', '.otf')):
                                font_name = f"{font_family} - {font_file.replace('.ttf', '').replace('.otf', '')}"
                                font_path = os.path.join(static_path, font_file)
                                fonts[font_name] = font_path
                    
                    # Also check root of family directory
                    for font_file in os.listdir(family_path):
                        if font_file.endswith(('.ttf', '.otf')):
                            font_name = f"{font_family} - {font_file.replace('.ttf', '').replace('.otf', '')}"
                            font_path = os.path.join(family_path, font_file)
                            fonts[font_name] = font_path
        
        return fonts
    
    def create_preview_image(
        self, 
        video_path: str, 
        output_path: str, 
        title: str = "", 
        font_path: str = None,
        quality: str = "1080p"
    ) -> bool:
        """
        Create a preview image showing how the video will look with title and layout.
        
        Args:
            video_path: Path to input video
            output_path: Path for preview image
            title: Title to preview
            font_path: Path to custom font
            quality: Output quality
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get output resolution
            output_width, output_height = self._get_output_resolution(quality)
            
            # Create a preview at 10 seconds into the video
            preview_time = "10"
            
            # Build filter for preview (same as video but output as image)
            video_filter = self._build_video_filters(output_width, output_height, title, font_path)
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', preview_time,
                '-vframes', '1',
                '-filter_complex', video_filter,
                '-map', '[output]',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            return os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"Failed to create preview image: {e}")
            return False
    
    def create_fragments_with_subtitles(
        self, 
        video_path: str, 
        fragment_duration: int = 30,
        quality: str = "1080p",
        title: str = "",
        subtitle_style: str = "modern",
        font_path: str = None
    ) -> List[Dict[str, Any]]:
        """
        Cut video into fragments with professional shorts layout and subtitles.
        
        Args:
            video_path: Path to input video
            fragment_duration: Duration of each fragment in seconds
            quality: Output quality (720p, 1080p, 4k)
            title: Title to display at the top
            subtitle_style: Style of subtitles (modern, classic, colorful)
            font_path: Path to custom font file
            
        Returns:
            List of fragment information
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Validate fragment duration
        if not (MIN_FRAGMENT_DURATION <= fragment_duration <= MAX_FRAGMENT_DURATION):
            raise ValueError(f"Fragment duration must be between {MIN_FRAGMENT_DURATION} and {MAX_FRAGMENT_DURATION} seconds")
        
        # Get video info
        video_info = self.get_video_info(video_path)
        total_duration = video_info['duration']
        
        if total_duration < fragment_duration:
            # If video is shorter than fragment duration, create one fragment
            num_fragments = 1
            fragment_duration = int(total_duration)
        else:
            num_fragments = int(total_duration // fragment_duration)
            if total_duration % fragment_duration > 10:  # If remainder > 10 seconds, create extra fragment
                num_fragments += 1
        
        fragments = []
        
        for i in range(num_fragments):
            start_time = i * fragment_duration
            
            # Calculate end time for this fragment
            if i == num_fragments - 1:
                # Last fragment - use remaining duration
                end_time = total_duration
                actual_duration = total_duration - start_time
            else:
                end_time = start_time + fragment_duration
                actual_duration = fragment_duration
            
            # Skip fragments that are too short
            if actual_duration < 5:  # Skip fragments shorter than 5 seconds
                continue
            
            fragment_filename = f"fragment_{i+1:03d}.mp4"
            fragment_path = os.path.join(self.output_dir, fragment_filename)
            
            # Create fragment title
            fragment_title = f"{title} - Часть {i+1}" if title else f"Фрагмент {i+1}"
            
            # Process fragment with professional layout
            fragment_info = self._process_professional_fragment(
                video_path=video_path,
                output_path=fragment_path,
                start_time=start_time,
                duration=actual_duration,
                quality=quality,
                title=fragment_title,
                subtitle_style=subtitle_style,
                font_path=font_path
            )
            
            fragment_info.update({
                'fragment_number': i + 1,
                'filename': fragment_filename,
                'start_time': start_time,
                'end_time': end_time,
                'duration': actual_duration,
                'title': fragment_title,
                'subtitle_style': subtitle_style
            })
            
            fragments.append(fragment_info)
            logger.info(f"Created professional fragment {i+1}/{num_fragments}: {fragment_filename}")
        
        return fragments
    
    def _process_professional_fragment(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        quality: str,
        title: str = "",
        subtitle_style: str = "modern",
        font_path: str = None
    ) -> Dict[str, Any]:
        """
        Process a single video fragment with professional shorts layout.
        
        Args:
            video_path: Input video path
            output_path: Output fragment path
            start_time: Start time in seconds
            duration: Duration in seconds
            quality: Output quality
            title: Title to overlay
            subtitle_style: Subtitle style
            font_path: Path to custom font
            
        Returns:
            Dict with fragment processing results
        """
        try:
            # Get output resolution based on quality
            output_width, output_height = self._get_output_resolution(quality)
            
            # Build FFmpeg command for professional shorts
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-filter_complex', self._build_video_filters(output_width, output_height, title, font_path),
                '-map', '[output]',  # Map the processed video stream
                '-map', '0:a?',  # Map the original audio stream if it exists
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '20',  # Higher quality for professional look
                '-r', str(SHORTS_FPS),
                '-c:a', 'aac',
                '-b:a', '192k',  # Higher audio quality
                '-movflags', '+faststart',
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Run FFmpeg
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=600  # 10 minute timeout for complex processing
            )
            
            # Get output file info
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                output_info = self.get_video_info(output_path)
                
                return {
                    'local_path': output_path,
                    'size_bytes': file_size,
                    'resolution': f"{output_info['width']}x{output_info['height']}",
                    'fps': output_info['fps'],
                    'bitrate': output_info['bitrate'],
                    'has_title': bool(title),
                    'title': title,
                    'subtitle_style': subtitle_style,
                    'success': True
                }
            else:
                raise RuntimeError("Output file was not created")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr}")
            raise RuntimeError(f"Professional video processing failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout during professional processing")
            raise RuntimeError("Professional video processing timeout")
        except Exception as e:
            logger.error(f"Professional fragment processing failed: {e}")
            raise
    
    def cleanup_file(self, file_path: str) -> bool:
        """Clean up processed file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")
            return False 