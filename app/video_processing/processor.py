"""
Video processor module using FFmpeg for cutting and converting videos.
"""
import os
import tempfile
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json

from app.config.constants import (
    SHORTS_RESOLUTION, 
    SHORTS_FPS, 
    SHORTS_BITRATE,
    MIN_FRAGMENT_DURATION,
    MAX_FRAGMENT_DURATION
)

# Настройки стилей для текста
DEFAULT_TEXT_STYLES = {
    'title': {
        'color': 'red',
        'border_color': 'black',
        'border_width': 3,
        'size_ratio': 0.04,  # 4% от высоты видео
        'position_y_ratio': 0.05,  # 5% от верха видео
    },
    'subtitle': {
        'color': 'white',
        'border_color': 'black', 
        'border_width': 3,
        'size_ratio': 0.05,  # 5% от высоты видео
        'position_y_ratio': 0.85,  # 85% от верха видео (внизу)
    }
}

# Пресеты цветов для заголовков и субтитров
TEXT_COLOR_PRESETS = {
    'white': {'color': 'white', 'border_color': 'black'},
    'red': {'color': 'red', 'border_color': 'white'},
    'blue': {'color': '#0066FF', 'border_color': 'white'},
    'yellow': {'color': 'yellow', 'border_color': 'black'},
    'green': {'color': '#00FF66', 'border_color': 'black'},
    'orange': {'color': 'orange', 'border_color': 'black'},
    'purple': {'color': '#9966FF', 'border_color': 'white'},
    'pink': {'color': '#FF66CC', 'border_color': 'black'},
}

# Пресеты размеров
TEXT_SIZE_PRESETS = {
    'small': {'title': 0.03, 'subtitle': 0.04},
    'medium': {'title': 0.04, 'subtitle': 0.05},
    'large': {'title': 0.05, 'subtitle': 0.06},
    'extra_large': {'title': 0.06, 'subtitle': 0.07},
}

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Video processor using FFmpeg."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize video processor.
        
        Args:
            output_dir: Directory to save processed videos
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Check if FFmpeg is available
        if not self._check_ffmpeg():
            logger.warning("FFmpeg not found. Video processing will be limited.")
    
    @staticmethod
    def create_custom_text_style(
        text_type: str,
        color_preset: str = 'white',
        size_preset: str = 'medium',
        custom_border_width: int = None
    ) -> Dict[str, Any]:
        """
        Создает кастомный стиль для текста на основе пресетов.
        
        Args:
            text_type: 'title' или 'subtitle'
            color_preset: Пресет цвета из TEXT_COLOR_PRESETS
            size_preset: Пресет размера из TEXT_SIZE_PRESETS
            custom_border_width: Кастомная ширина обводки
            
        Returns:
            Словарь с настройками стиля
        """
        if text_type not in ['title', 'subtitle']:
            raise ValueError("text_type должен быть 'title' или 'subtitle'")
        
        # Базовый стиль
        style = DEFAULT_TEXT_STYLES[text_type].copy()
        
        # Применяем цветовой пресет
        if color_preset in TEXT_COLOR_PRESETS:
            color_settings = TEXT_COLOR_PRESETS[color_preset]
            style['color'] = color_settings['color']
            style['border_color'] = color_settings['border_color']
        
        # Применяем размерный пресет
        if size_preset in TEXT_SIZE_PRESETS:
            size_settings = TEXT_SIZE_PRESETS[size_preset]
            style['size_ratio'] = size_settings[text_type]
        
        # Кастомная ширина обводки
        if custom_border_width is not None:
            style['border_width'] = custom_border_width
        
        return style
    
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
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            audio_stream = None
            for stream in data['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                elif stream['codec_type'] == 'audio':
                    audio_stream = stream
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            format_info = data['format']
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'size_bytes': int(format_info.get('size', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': self._parse_fps(video_stream.get('r_frame_rate', '30/1')),
                'codec': video_stream.get('codec_name', 'unknown'),
                'pixel_format': video_stream.get('pix_fmt', 'unknown'),
                'has_audio': audio_stream is not None,
                'audio_codec': audio_stream.get('codec_name', 'none') if audio_stream else 'none',
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise
    
    def create_fragments(
        self, 
        video_path: str, 
        fragment_duration: int = 30,
        quality: str = "1080p",
        title: str = "",
        subtitle_style: str = "modern"
    ) -> List[Dict[str, Any]]:
        """
        Cut video into fragments and convert to professional shorts format.
        
        Args:
            video_path: Path to input video
            fragment_duration: Duration of each fragment in seconds
            quality: Output quality (720p, 1080p, 4k)
            title: Title to display at the top
            subtitle_style: Style of subtitles (modern, classic, colorful)
            
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
                has_subtitles=False  # Default to no subtitles in basic create_fragments
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
            logger.info(f"Created fragment {i+1}/{num_fragments}: {fragment_filename}")
        
        return fragments
    
    def _process_fragment(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        quality: str
    ) -> Dict[str, Any]:
        """
        Process a single video fragment.
        
        Args:
            video_path: Input video path
            output_path: Output fragment path
            start_time: Start time in seconds
            duration: Duration in seconds
            quality: Output quality
            
        Returns:
            Dict with fragment processing results
        """
        try:
            # Get output resolution based on quality
            output_width, output_height = self._get_output_resolution(quality)
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', self._build_video_filters(output_width, output_height),
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-r', str(SHORTS_FPS),
                '-c:a', 'aac',
                '-b:a', '128k',
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
                timeout=300  # 5 minute timeout per fragment
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
                    'success': True
                }
            else:
                raise RuntimeError("Output file was not created")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr}")
            raise RuntimeError(f"Video processing failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout")
            raise RuntimeError("Video processing timeout")
        except Exception as e:
            logger.error(f"Fragment processing failed: {e}")
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
        except Exception:
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
    
    def _build_video_filters(
        self, 
        width: int, 
        height: int, 
        title: str = "", 
        font_path: str = None,
        title_style: Dict[str, Any] = None
    ) -> str:
        """
        Build FFmpeg video filter string for professional shorts conversion.
        
        Args:
            width: Target width
            height: Target height
            title: Optional title to overlay at the top
            font_path: Path to custom font file
            title_style: Custom style settings for title
            
        Returns:
            FFmpeg filter string
        """
        # Create professional shorts layout:
        # 1. Background: Blurred and scaled version of original video
        # 2. Main video: Centered, scaled to fit with aspect ratio preserved
        # 3. Title overlay at the top
        # 4. Subtitle area reserved at the bottom
        
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
            # Use custom style or default
            style = title_style or DEFAULT_TEXT_STYLES['title']
            
            # Use custom font if provided, otherwise use Kaph font
            if font_path and os.path.exists(font_path):
                fontfile = font_path
            else:
                # Try Kaph font first
                kaph_font_path = "/app/fonts/Kaph/static/Kaph-Regular.ttf"
                if os.path.exists(kaph_font_path):
                    fontfile = kaph_font_path
                else:
                    fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            title_escaped = title.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
            
            # Build title filter with custom styling
            font_size = int(height * style['size_ratio'])
            y_position = int(height * style['position_y_ratio'])
            
            title_filter = f"drawtext=text='{title_escaped}':fontfile={fontfile}:fontsize={font_size}:fontcolor={style['color']}:bordercolor={style['border_color']}:borderw={style['border_width']}:x=(w-text_w)/2:y={y_position}"
            filters.append(f"[with_main]{title_filter}[output]")
        else:
            # If no title, rename the final output
            filters.append("[with_main]null[output]")
        
        # Note: Fade effects removed due to FFmpeg compatibility issues
        # Can be added later with proper syntax: fade=in:0:30,fade=out:st=duration-30:d=30
        
        return ";".join(filters)
    
    def get_available_fonts(self) -> Dict[str, str]:
        """
        Get available fonts from the fonts directory.
        
        This function scans the /app/fonts directory for font families. For each family,
        it looks for font files in a 'static' subdirectory first. If it exists,
        it scans that directory. Otherwise, it scans the family's root directory.

        Returns:
            Dict mapping font names to font file paths
        """
        fonts = {}
        fonts_dir = "/app/fonts"

        if not os.path.isdir(fonts_dir):
            logger.warning(f"Fonts directory not found or not a directory: {fonts_dir}")
            return fonts

        logger.info(f"Scanning fonts directory: {fonts_dir}")
        try:
            for font_family in sorted(os.listdir(fonts_dir)):
                family_path = os.path.join(fonts_dir, font_family)
                if os.path.isdir(family_path):
                    logger.debug(f"Processing font family directory: {family_path}")
                    
                    search_path = family_path
                    static_path = os.path.join(family_path, "static")

                    if os.path.isdir(static_path):
                        search_path = static_path
                    
                    logger.debug(f"Scanning for font files in: {search_path}")
                    for font_file in sorted(os.listdir(search_path)):
                        if font_file.lower().endswith(('.ttf', '.otf')):
                            font_path = os.path.join(search_path, font_file)
                            if os.path.isfile(font_path):
                                clean_name = Path(font_file).stem.replace('-', ' ').replace('_', ' ')
                                font_name = f"{font_family} - {clean_name}"
                                
                                if font_name not in fonts:
                                    fonts[font_name] = font_path
                                    logger.debug(f"Added font: {font_name} -> {font_path}")
        except Exception as e:
            logger.error(f"Error scanning fonts directory '{fonts_dir}': {e}", exc_info=True)
            
        logger.info(f"Total fonts available: {len(fonts)}")
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
                font_path=font_path,
                has_subtitles=True  # Enable subtitles in create_fragments_with_subtitles
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
        font_path: str = None,
        has_subtitles: bool = False,
        title_color: str = 'white',
        title_size: str = 'medium',
        subtitle_color: str = 'white',
        subtitle_size: str = 'medium'
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
            has_subtitles: Whether to add subtitles
            title_color: Color preset for title
            title_size: Size preset for title
            subtitle_color: Color preset for subtitles
            subtitle_size: Size preset for subtitles
            
        Returns:
            Dict with fragment processing results
        """
        try:
            # Get output resolution based on quality
            output_width, output_height = self._get_output_resolution(quality)
            
            # Create custom styles for title and subtitles
            custom_title_style = self.create_custom_text_style('title', title_color, title_size) if title else None
            custom_subtitle_style = self.create_custom_text_style('subtitle', subtitle_color, subtitle_size)
            
            # Build FFmpeg command for professional shorts
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-filter_complex', self._build_video_filters(output_width, output_height, title, font_path, custom_title_style),
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
            
            # Add subtitles if enabled
            if has_subtitles and os.path.exists(output_path):
                logger.info(f"Adding subtitles to fragment: {output_path}")
                
                # Generate subtitles for this fragment
                subtitles = self.generate_subtitles_from_audio(
                    video_path=video_path,
                    start_time=start_time,
                    duration=duration
                )
                
                if subtitles:
                    # Create temporary file for video with subtitles
                    temp_output = output_path.replace('.mp4', '_temp.mp4')
                    
                    # Add animated subtitles
                    if self.add_animated_subtitles(
                        video_path=output_path,
                        output_path=temp_output,
                        subtitles=subtitles,
                        subtitle_style=subtitle_style,
                        custom_subtitle_style=custom_subtitle_style
                    ):
                        # Replace original with subtitled version
                        if os.path.exists(temp_output):
                            os.replace(temp_output, output_path)
                            logger.info(f"Successfully added subtitles to fragment")
                        else:
                            logger.warning(f"Failed to create subtitled version")
                    else:
                        logger.warning(f"Failed to add subtitles to fragment")
                else:
                    logger.warning(f"No subtitles generated for fragment")
            
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
                    'has_subtitles': has_subtitles,
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
    
    def add_animated_subtitles(
        self,
        video_path: str,
        output_path: str,
        subtitles: List[Dict[str, Any]],
        subtitle_style: str = "modern",
        custom_subtitle_style: Dict[str, Any] = None
    ) -> bool:
        """
        Add animated word-by-word subtitles to video.
        
        Args:
            video_path: Input video path
            output_path: Output video path with subtitles
            subtitles: List of subtitle segments with timing
            subtitle_style: Style of subtitles (modern, classic, colorful)
            custom_subtitle_style: Custom style settings for subtitles
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get video resolution for subtitle positioning
            video_info = self.get_video_info(video_path)
            width = video_info['width']
            height = video_info['height']
            
            # Use custom style or default
            style = custom_subtitle_style or DEFAULT_TEXT_STYLES['subtitle']
            
            # Calculate subtitle positioning and sizing
            subtitle_y = int(height * style['position_y_ratio'])
            font_size = int(height * style['size_ratio'])
            
            # Build subtitle filters for word-by-word animation
            subtitle_filters = []
            
            for i, subtitle in enumerate(subtitles):
                words = subtitle['text'].split()
                start_time = subtitle['start']
                end_time = subtitle['end']
                word_duration = (end_time - start_time) / len(words)
                
                for j, word in enumerate(words):
                    word_start = start_time + (j * word_duration)
                    word_end = word_start + word_duration
                    
                    # Escape special characters
                    word_escaped = word.replace("'", "\\'").replace(":", "\\:")
                    
                    # Create animated word subtitle with custom styling
                    if subtitle_style == "modern":
                        text_color = style['color']
                        border_color = style['border_color']
                        border_width = style['border_width']
                    elif subtitle_style == "colorful":
                        text_color = "yellow"
                        border_color = style['border_color']
                        border_width = style['border_width']
                    else:  # classic
                        text_color = style['color']
                        border_color = style['border_color']
                        border_width = max(2, style['border_width'] - 1)  # Немного тоньше для классического стиля
                    
                    subtitle_filter = f"drawtext=text='{word_escaped}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize={font_size}:fontcolor={text_color}:bordercolor={border_color}:borderw={border_width}:x=(w-text_w)/2:y={subtitle_y}:enable='between(t,{word_start},{word_end})'"
                    
                    subtitle_filters.append(subtitle_filter)
            
            # Combine all subtitle filters
            if subtitle_filters:
                full_filter = ",".join(subtitle_filters)
                
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-vf', full_filter,
                    '-map', '0:v',  # Map video stream
                    '-map', '0:a?',  # Map audio stream if exists
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '20',
                    '-c:a', 'copy',  # Copy audio without re-encoding
                    '-y',
                    output_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=600
                )
                
                return os.path.exists(output_path)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to add animated subtitles: {e}")
            return False
    
    def generate_subtitles_from_audio(
        self,
        video_path: str,
        start_time: float = 0,
        duration: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate subtitles from video audio using faster-whisper speech recognition.
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds for subtitle generation
            duration: Duration in seconds (if None, process entire video)
            
        Returns:
            List of subtitle segments with timing
        """
        try:
            # Check if video has audio stream
            video_info = self.get_video_info(video_path)
            if not video_info.get('has_audio', False):
                logger.info("Video has no audio stream, using simple subtitle generation")
                return self._generate_simple_subtitles(start_time, duration or video_info['duration'])
            
            # Create temporary audio file
            temp_audio = os.path.join(self.output_dir, "temp_audio.wav")
            
            # Extract audio segment from video
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
            ]
            
            if duration:
                cmd.extend(['-t', str(duration)])
            
            cmd.extend([
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian
                '-ac', '1',  # Convert to mono
                '-ar', '16000',  # 16kHz sample rate for faster-whisper
                '-f', 'wav',  # Force WAV format
                '-y',
                temp_audio
            ])
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg audio extraction failed: {e.stderr}")
                logger.error(f"FFmpeg command: {' '.join(cmd)}")
                # Fallback to simple subtitle generation without audio analysis
                logger.info("Falling back to simple subtitle generation")
                return self._generate_simple_subtitles(start_time, duration or video_info['duration'])
            
            if not os.path.exists(temp_audio):
                logger.warning("Audio file was not created, falling back to simple subtitles")
                return self._generate_simple_subtitles(start_time, duration or self.get_video_info(video_path)['duration'])
            
            # Use faster-whisper for speech recognition
            logger.info("Starting speech recognition with faster-whisper...")
            
            try:
                from faster_whisper import WhisperModel
                
                # Load faster-whisper model (base model for good balance of speed/accuracy)
                model = WhisperModel("base", device="cpu", compute_type="int8")
                
                # Transcribe audio with word-level timestamps
                segments, info = model.transcribe(
                    temp_audio,
                    language="ru",  # Russian language
                    word_timestamps=True,
                    task="transcribe"
                )
                
                # Convert faster-whisper results to our subtitle format
                subtitles = []
                
                for segment in segments:
                    # Adjust timestamps by adding start_time offset
                    segment_start = segment.start + start_time
                    segment_end = segment.end + start_time
                    segment_text = segment.text.strip()
                    
                    if segment_text:  # Only add non-empty segments
                        subtitles.append({
                            'start': segment_start,
                            'end': segment_end,
                            'text': segment_text
                        })
                
                logger.info(f"Successfully generated {len(subtitles)} subtitle segments from speech recognition")
                logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
                
                # Clean up temporary audio file
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                
                return subtitles
                
            except ImportError:
                logger.error("faster-whisper not available, falling back to simple subtitles")
                # Clean up temporary audio file
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                return self._generate_simple_subtitles(start_time, duration or self.get_video_info(video_path)['duration'])
            
            except Exception as whisper_error:
                logger.error(f"faster-whisper transcription failed: {whisper_error}")
                # Clean up temporary audio file
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                return self._generate_simple_subtitles(start_time, duration or self.get_video_info(video_path)['duration'])
            
        except Exception as e:
            logger.error(f"Failed to generate subtitles: {e}")
            return []
    
    def _generate_simple_subtitles(self, start_time: float, total_duration: float) -> List[Dict[str, Any]]:
        """
        Generate simple subtitles without audio analysis.
        
        Args:
            start_time: Start time in seconds
            total_duration: Total duration in seconds
            
        Returns:
            List of subtitle segments
        """
        try:
            # Create simple subtitle segments
            subtitles = []
            segment_duration = min(3.0, total_duration / 10)  # Each subtitle segment ~3 seconds
            num_segments = int(total_duration / segment_duration)
            
            demo_texts = [
                "Добро пожаловать",
                "Смотрите это видео", 
                "Интересный контент",
                "Не забудьте подписаться",
                "Ставьте лайки",
                "Делитесь с друзьями",
                "Спасибо за просмотр",
                "До встречи",
                "Увидимся позже",
                "Отличное видео"
            ]
            
            for i in range(min(num_segments, len(demo_texts))):
                subtitle_start = start_time + (i * segment_duration)
                subtitle_end = start_time + ((i + 1) * segment_duration)
                
                subtitles.append({
                    'start': subtitle_start,
                    'end': min(subtitle_end, start_time + total_duration),
                    'text': demo_texts[i % len(demo_texts)]
                })
            
            logger.info(f"Generated {len(subtitles)} simple subtitle segments")
            return subtitles
            
        except Exception as e:
            logger.error(f"Failed to generate simple subtitles: {e}")
            return []
    
    def process_full_video_then_fragment(
        self,
        video_path: str,
        fragment_duration: int = 30,
        quality: str = "1080p",
        title: str = "",
        subtitle_style: str = "modern",
        title_color: str = 'white',
        title_size: str = 'medium',
        subtitle_color: str = 'white',
        subtitle_size: str = 'medium',
        font_path: str = None,
        enable_subtitles: bool = True
    ) -> Dict[str, Any]:
        """
        Process video with the correct workflow:
        1. First process the full video (add title, subtitles)
        2. Then cut the processed video into fragments
        
        Args:
            video_path: Path to input video
            fragment_duration: Duration of each fragment in seconds
            quality: Output quality (720p, 1080p, 4k)
            title: Title to display at the top
            subtitle_style: Style of subtitles
            title_color: Color preset for title
            title_size: Size preset for title
            subtitle_color: Color preset for subtitles
            subtitle_size: Size preset for subtitles
            font_path: Path to custom font file
            enable_subtitles: Whether to add subtitles
            
        Returns:
            Dict with processing results and fragments
        """
        try:
            # Step 1: Process the full video
            logger.info("Step 1: Processing full video with title and subtitles...")
            
            # Get video info
            video_info = self.get_video_info(video_path)
            total_duration = video_info['duration']
            
            # Create processed video filename
            processed_video_path = os.path.join(self.output_dir, "processed_full_video.mp4")
            
            # Get output resolution
            output_width, output_height = self._get_output_resolution(quality)
            
            # Create custom styles
            custom_title_style = self.create_custom_text_style('title', title_color, title_size) if title else None
            custom_subtitle_style = self.create_custom_text_style('subtitle', subtitle_color, subtitle_size)
            
            # Build video filter for title and layout
            video_filter = self._build_video_filters(output_width, output_height, title, font_path, custom_title_style)
            
            # First pass: Create video with title and proper layout
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-filter_complex', video_filter,
                '-map', '[output]',  # Map processed video
                '-map', '0:a?',  # Map original audio if exists
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '20',
                '-r', str(SHORTS_FPS),
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '44100',  # Standard audio sample rate
                '-ac', '2',  # Stereo audio
                '-movflags', '+faststart',
                '-y',
                processed_video_path
            ]
            
            # Run FFmpeg
            logger.info("Creating video with title and layout...")
            logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=1200)
                logger.info("FFmpeg completed successfully")
                if result.stderr:
                    logger.warning(f"FFmpeg stderr: {result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg failed with return code {e.returncode}")
                logger.error(f"FFmpeg stderr: {e.stderr}")
                logger.error(f"FFmpeg stdout: {e.stdout}")
                raise
            except subprocess.TimeoutExpired:
                logger.error("FFmpeg timeout during video processing")
                raise
            
            # Step 2: Add subtitles to the processed video (if enabled)
            if enable_subtitles and video_info.get('has_audio', False):
                logger.info("Generating subtitles for the full video...")
                
                # Generate subtitles for the entire video
                subtitles = self.generate_subtitles_from_audio(
                    video_path=video_path,  # Use original video for audio extraction
                    start_time=0,
                    duration=total_duration
                )
                
                if subtitles:
                    logger.info(f"Generated {len(subtitles)} subtitle segments")
                    
                    # Create temporary file for video with subtitles
                    temp_subtitled_path = processed_video_path.replace('.mp4', '_subtitled.mp4')
                    
                    # Add subtitles to the processed video
                    if self.add_animated_subtitles(
                        video_path=processed_video_path,
                        output_path=temp_subtitled_path,
                        subtitles=subtitles,
                        subtitle_style=subtitle_style,
                        custom_subtitle_style=custom_subtitle_style
                    ):
                        # Replace processed video with subtitled version
                        os.replace(temp_subtitled_path, processed_video_path)
                        logger.info("Successfully added subtitles to full video")
                    else:
                        logger.warning("Failed to add subtitles to full video")
                else:
                    logger.warning("No subtitles generated for full video")
            
            # Step 3: Cut the processed video into fragments
            logger.info("Step 3: Cutting processed video into fragments...")
            
            fragments = []
            
            # Calculate number of fragments
            if total_duration < fragment_duration:
                num_fragments = 1
                fragment_duration = int(total_duration)
            else:
                num_fragments = int(total_duration // fragment_duration)
                if total_duration % fragment_duration > 10:
                    num_fragments += 1
            
            for i in range(num_fragments):
                start_time = i * fragment_duration
                
                if i == num_fragments - 1:
                    # Last fragment - use remaining duration
                    actual_duration = total_duration - start_time
                else:
                    # Regular fragment - use exact duration
                    actual_duration = min(fragment_duration, total_duration - start_time)
                
                # Skip fragments that are too short
                if actual_duration < 5:
                    continue
                
                fragment_filename = f"fragment_{i+1:03d}.mp4"
                fragment_path = os.path.join(self.output_dir, fragment_filename)
                
                # Simple cut without re-encoding (much faster and preserves quality)
                cut_cmd = [
                    'ffmpeg',
                    '-i', processed_video_path,
                    '-ss', str(start_time),
                    '-t', str(actual_duration),
                    '-c', 'copy',  # Copy streams without re-encoding
                    '-avoid_negative_ts', 'make_zero',
                    '-y',
                    fragment_path
                ]
                
                # Run FFmpeg for cutting
                result = subprocess.run(cut_cmd, capture_output=True, text=True, check=True, timeout=300)
                
                if os.path.exists(fragment_path):
                    file_size = os.path.getsize(fragment_path)
                    fragment_info = {
                        'fragment_number': i + 1,
                        'filename': fragment_filename,
                        'local_path': fragment_path,
                        'start_time': start_time,
                        'duration': actual_duration,
                        'size_bytes': file_size,
                        'title': f"{title} - Часть {i+1}" if title else f"Фрагмент {i+1}"
                    }
                    fragments.append(fragment_info)
                    logger.info(f"Created fragment {i+1}/{num_fragments}: {fragment_filename}")
            
            # Clean up the processed full video (optional, can keep it)
            # os.remove(processed_video_path)
            
            return {
                'success': True,
                'total_duration': total_duration,
                'num_fragments': len(fragments),
                'fragments': fragments,
                'processed_video_path': processed_video_path
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr}")
            raise RuntimeError(f"Video processing failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            raise
 
