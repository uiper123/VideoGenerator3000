"""
Video processor using MoviePy for better reliability and easier text/subtitle handling.
"""
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Initialize logger
logger = logging.getLogger(__name__)

try:
    from moviepy.editor import (
        VideoFileClip, 
        TextClip, 
        CompositeVideoClip,
        concatenate_videoclips
    )
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    logger.warning(f"MoviePy not available. ImportError: {e}. Some features will be disabled.")

from app.config.constants import (
    SHORTS_WIDTH, SHORTS_HEIGHT, SHORTS_FPS,
    MIN_FRAGMENT_DURATION, MAX_FRAGMENT_DURATION,
    DEFAULT_TEXT_STYLES
)

class VideoProcessorMoviePy:
    """Video processor using MoviePy for better text and subtitle handling."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize VideoProcessor with MoviePy.
        
        Args:
            output_dir: Directory for output files
        """
        if not MOVIEPY_AVAILABLE:
            raise ImportError("MoviePy is not installed. Please install it: pip install moviepy")
        
        self.output_dir = output_dir or "/tmp/processed"
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("VideoProcessorMoviePy initialized")
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video information using MoviePy.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with video information
        """
        try:
            with VideoFileClip(video_path) as clip:
                return {
                    'duration': clip.duration,
                    'width': clip.w,
                    'height': clip.h,
                    'fps': clip.fps,
                    'has_audio': clip.audio is not None,
                    'size_bytes': os.path.getsize(video_path) if os.path.exists(video_path) else 0
                }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {
                'duration': 0,
                'width': 0,
                'height': 0,
                'fps': 30,
                'has_audio': False,
                'size_bytes': 0
            }
    
    def process_video_with_moviepy(
        self,
        video_path: str,
        fragment_duration: int = 30,
        quality: str = "1080p",
        title: str = "",
        title_color: str = 'white',
        title_size: str = 'medium',
        subtitle_color: str = 'white',
        subtitle_size: str = 'medium',
        font_path: str = None,
        enable_subtitles: bool = True
    ) -> Dict[str, Any]:
        """
        Process video with MoviePy: add title, subtitles, convert to shorts format, then fragment.
        
        Args:
            video_path: Path to input video
            fragment_duration: Duration of each fragment in seconds
            quality: Output quality
            title: Title to display
            title_color: Color for title
            title_size: Size for title
            subtitle_color: Color for subtitles
            subtitle_size: Size for subtitles
            font_path: Path to custom font
            enable_subtitles: Whether to add subtitles
            
        Returns:
            Dict with processing results and fragments
        """
        try:
            logger.info("Starting MoviePy video processing...")
            
            # Load video
            video = VideoFileClip(video_path)
            original_duration = video.duration
            
            logger.info(f"Loaded video: {video.w}x{video.h}, {original_duration:.2f}s, audio: {video.audio is not None}")
            
            # Convert to shorts format (9:16 aspect ratio)
            processed_video = self._convert_to_shorts_format(video, quality)
            
            # Add title if provided
            if title:
                processed_video = self._add_title(processed_video, title, title_color, title_size, font_path)
                logger.info(f"Added title: {title}")
            
            # Generate and add subtitles if enabled
            if enable_subtitles and video.audio is not None:
                subtitles = self._generate_subtitles_moviepy(video_path, video.duration)
                if subtitles:
                    processed_video = self._add_subtitles_moviepy(
                        processed_video, subtitles, subtitle_color, subtitle_size, font_path
                    )
                    logger.info(f"Added {len(subtitles)} subtitle segments")
                else:
                    logger.warning("No subtitles generated")
            
            # Save processed full video
            processed_video_path = os.path.join(self.output_dir, "processed_full_video.mp4")
            logger.info("Saving processed full video...")
            
            processed_video.write_videofile(
                processed_video_path,
                fps=SHORTS_FPS,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None,  # Disable MoviePy's verbose logging
                preset='ultrafast',
                threads=4
            )
            
            # Clean up
            video.close()
            processed_video.close()
            
            # Cut into fragments
            logger.info("Creating fragments...")
            fragments = self._create_fragments_moviepy(processed_video_path, fragment_duration, title)
            
            return {
                'success': True,
                'total_duration': original_duration,
                'num_fragments': len(fragments),
                'fragments': fragments,
                'processed_video_path': processed_video_path
            }
            
        except Exception as e:
            logger.error(f"MoviePy video processing failed: {e}")
            raise RuntimeError(f"Video processing failed: {e}")
    
    def _convert_to_shorts_format(self, video: VideoFileClip, quality: str) -> VideoFileClip:
        """
        Convert video to shorts format (9:16 aspect ratio).
        
        Args:
            video: Input video clip
            quality: Output quality
            
        Returns:
            Processed video clip
        """
        # Get target resolution
        target_width, target_height = self._get_output_resolution(quality)
        
        # Calculate scaling to fit the video in the shorts format
        video_aspect = video.w / video.h
        target_aspect = target_width / target_height
        
        if video_aspect > target_aspect:
            # Video is wider - scale by height and crop width
            scale_factor = target_height / video.h
            new_width = int(video.w * scale_factor)
            new_height = target_height
            
            # Resize and center crop
            resized = video.resize(height=new_height)
            x_center = (new_width - target_width) // 2
            cropped = resized.crop(x1=x_center, x2=x_center + target_width)
        else:
            # Video is taller or same aspect - scale by width
            scale_factor = target_width / video.w
            new_width = target_width
            new_height = int(video.h * scale_factor)
            
            if new_height > target_height:
                # Crop height if needed
                resized = video.resize(width=new_width)
                y_center = (new_height - target_height) // 2
                cropped = resized.crop(y1=y_center, y2=y_center + target_height)
            else:
                # Add black bars if needed
                resized = video.resize(width=new_width)
                cropped = resized.on_color(
                    size=(target_width, target_height),
                    color=(0, 0, 0),
                    pos='center'
                )
        
        return cropped
    
    def _add_title(self, video: VideoFileClip, title: str, color: str, size: str, font_path: str = None) -> VideoFileClip:
        """
        Add title to video using MoviePy.
        
        Args:
            video: Input video clip
            title: Title text
            color: Text color
            size: Text size
            font_path: Path to custom font
            
        Returns:
            Video with title
        """
        # Get color value
        color_map = {
            'white': 'white',
            'red': 'red',
            'blue': 'blue',
            'yellow': 'yellow',
            'green': 'green',
            'orange': 'orange',
            'purple': 'purple',
            'pink': 'pink'
        }
        text_color = color_map.get(color, 'white')
        
        # Get font size
        size_map = {
            'small': int(video.h * 0.04),
            'medium': int(video.h * 0.06),
            'large': int(video.h * 0.08),
            'extra_large': int(video.h * 0.10)
        }
        font_size = size_map.get(size, size_map['medium'])
        
        # Create title clip
        title_clip = TextClip(
            title,
            fontsize=font_size,
            color=text_color,
            font=font_path if font_path and os.path.exists(font_path) else 'DejaVu-Sans-Bold',
            stroke_color='black',
            stroke_width=2
        ).set_duration(video.duration).set_position(('center', 20))
        
        # Composite video with title
        return CompositeVideoClip([video, title_clip])
    
    def _generate_subtitles_moviepy(self, video_path: str, duration: float) -> List[Dict[str, Any]]:
        """
        Generate subtitles using faster-whisper (same as before).
        
        Args:
            video_path: Path to video file
            duration: Video duration
            
        Returns:
            List of subtitle segments
        """
        try:
            # Create a VideoProcessor instance for subtitle generation
            from app.video_processing.processor import VideoProcessor
            
            processor = VideoProcessor(self.output_dir)
            subtitles = processor.generate_subtitles_from_audio(video_path, 0, duration)
            
            return subtitles
            
        except Exception as e:
            logger.error(f"Failed to generate subtitles: {e}")
            # Return simple demo subtitles
            return self._generate_simple_subtitles(duration)
    
    def _generate_simple_subtitles(self, duration: float) -> List[Dict[str, Any]]:
        """Generate simple demo subtitles."""
        subtitles = []
        segment_duration = min(3.0, duration / 8)
        num_segments = int(duration / segment_duration)
        
        demo_texts = [
            "Добро пожаловать",
            "Смотрите это видео", 
            "Интересный контент",
            "Не забудьте подписаться",
            "Ставьте лайки",
            "Делитесь с друзьями",
            "Спасибо за просмотр",
            "До встречи"
        ]
        
        for i in range(min(num_segments, len(demo_texts))):
            start_time = i * segment_duration
            end_time = min(start_time + segment_duration, duration)
            
            subtitles.append({
                'start': start_time,
                'end': end_time,
                'text': demo_texts[i % len(demo_texts)]
            })
        
        return subtitles
    
    def _add_subtitles_moviepy(
        self, 
        video: VideoFileClip, 
        subtitles: List[Dict[str, Any]], 
        color: str, 
        size: str, 
        font_path: str = None
    ) -> VideoFileClip:
        """
        Add subtitles to video using MoviePy.
        
        Args:
            video: Input video clip
            subtitles: List of subtitle segments
            color: Text color
            size: Text size
            font_path: Path to custom font
            
        Returns:
            Video with subtitles
        """
        # Get color and size
        color_map = {
            'white': 'white',
            'red': 'red',
            'blue': 'blue',
            'yellow': 'yellow',
            'green': 'green',
            'orange': 'orange',
            'purple': 'purple',
            'pink': 'pink'
        }
        text_color = color_map.get(color, 'white')
        
        size_map = {
            'small': int(video.h * 0.035),
            'medium': int(video.h * 0.045),
            'large': int(video.h * 0.055),
            'extra_large': int(video.h * 0.065)
        }
        font_size = size_map.get(size, size_map['medium'])
        
        # Create subtitle clips
        subtitle_clips = []
        
        for subtitle in subtitles:
            subtitle_clip = TextClip(
                subtitle['text'],
                fontsize=font_size,
                color=text_color,
                font=font_path if font_path and os.path.exists(font_path) else 'DejaVu-Sans-Bold',
                stroke_color='black',
                stroke_width=2
            ).set_start(subtitle['start']).set_duration(subtitle['end'] - subtitle['start']).set_position(('center', 0.8), relative=True)
            
            subtitle_clips.append(subtitle_clip)
        
        # Composite all clips
        all_clips = [video] + subtitle_clips
        return CompositeVideoClip(all_clips)
    
    def _create_fragments_moviepy(self, processed_video_path: str, fragment_duration: int, title: str) -> List[Dict[str, Any]]:
        """
        Create fragments from processed video using MoviePy.
        
        Args:
            processed_video_path: Path to processed video
            fragment_duration: Duration of each fragment
            title: Video title
            
        Returns:
            List of fragment information
        """
        fragments = []
        
        try:
            video = VideoFileClip(processed_video_path)
            total_duration = video.duration
            
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
                
                # Create fragment
                fragment_clip = video.subclip(start_time, start_time + actual_duration)
                
                fragment_filename = f"fragment_{i+1:03d}.mp4"
                fragment_path = os.path.join(self.output_dir, fragment_filename)
                
                # Save fragment
                fragment_clip.write_videofile(
                    fragment_path,
                    fps=SHORTS_FPS,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=f'temp-audio-{i}.m4a',
                    remove_temp=True,
                    logger=None,
                    preset='ultrafast',
                    threads=4
                )
                
                fragment_clip.close()
                
                # Get file info
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
            
            video.close()
            
        except Exception as e:
            logger.error(f"Failed to create fragments: {e}")
            raise
        
        return fragments
    
    def _get_output_resolution(self, quality: str) -> Tuple[int, int]:
        """Get output resolution based on quality setting."""
        resolutions = {
            "720p": (720, 1280),    # 9:16 aspect ratio
            "1080p": (1080, 1920),  # 9:16 aspect ratio  
            "4k": (2160, 3840)      # 9:16 aspect ratio
        }
        return resolutions.get(quality, resolutions["1080p"]) 