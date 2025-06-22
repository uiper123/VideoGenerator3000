"""
Video processor using MoviePy for better reliability and easier text/subtitle handling.
"""
import os
import logging
import uuid
import subprocess
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
        Process video with MoviePy and FFmpeg: add title, subtitles, convert to shorts format, then fragment.
        This version uses a highly optimized subtitle workflow.
        """
        try:
            logger.info("Starting optimized video processing...")
            
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
            
            # Save the video with title but without subtitles to a temporary path.
            # This is done first because subtitle burning is now a separate, final step.
            temp_video_path = os.path.join(self.output_dir, f"temp_{uuid.uuid4().hex[:8]}.mp4")
            logger.info(f"Saving temporary video to: {temp_video_path}")
            try:
                processed_video.write_videofile(
                    temp_video_path,
                    fps=SHORTS_FPS,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=f'/tmp/temp-audio-intermediate-{uuid.uuid4().hex[:8]}.m4a',
                    remove_temp=True,
                    logger=None,
                    preset='ultrafast',
                    threads=2
                )
            except Exception as e:
                logger.error(f"Failed to save intermediate video: {e}")
                raise RuntimeError(f"Could not save intermediate video: {e}")

            processed_video_path = temp_video_path

            # Generate and burn subtitles if enabled
            if enable_subtitles and video.audio is not None:
                subtitles = self._generate_subtitles_moviepy(video_path, video.duration)
                if subtitles:
                    srt_path = os.path.join(self.output_dir, f"subs_{uuid.uuid4().hex[:8]}.srt")
                    final_video_path = os.path.join(self.output_dir, "processed_full_video.mp4")
                    
                    try:
                        self._generate_srt_file(subtitles, srt_path)
                        logger.info(f"Burning {len(subtitles)} subtitles using FFmpeg...")
                        
                        self._burn_subtitles_with_ffmpeg(
                            video_path=temp_video_path,
                            srt_path=srt_path,
                            output_path=final_video_path,
                            font_path=font_path,
                            video_height=processed_video.h
                        )
                        processed_video_path = final_video_path
                        
                    except Exception as e:
                        logger.error(f"Failed to generate or burn subtitles: {e}. Using video without subtitles as fallback.")
                        # The temp_video_path (without subs) will be used
                    finally:
                        # Cleanup SRT file
                        if os.path.exists(srt_path):
                            os.remove(srt_path)
                        # Cleanup temp video if final video was created
                        if processed_video_path == final_video_path and os.path.exists(temp_video_path):
                            os.remove(temp_video_path)
                else:
                    logger.warning("No subtitles were generated.")
            
            # Clean up MoviePy objects
            video.close()
            processed_video.close()
            
            # Cut into fragments
            logger.info("Creating fragments from final video...")
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
        text_color = color_map.get(color, 'red')  # Changed default to red
        
        # Get font size
        size_map = {
            'small': int(video.h * 0.04),
            'medium': int(video.h * 0.06),
            'large': int(video.h * 0.08),
            'extra_large': int(video.h * 0.10)
        }
        font_size = size_map.get(size, size_map['medium'])
        
        # Determine font to use
        if font_path and os.path.exists(font_path):
            font_name = font_path
        else:
            # Try Kaph font as fallback
            kaph_path = "/app/fonts/Kaph/static/Kaph-Regular.ttf"
            if os.path.exists(kaph_path):
                font_name = kaph_path
            else:
                font_name = 'DejaVu-Sans-Bold'
        
        logger.info(f"Using font for title: {font_name}")
        
        # Create title clip
        title_clip = TextClip(
            title,
            fontsize=font_size,
            color=text_color,
            font=font_name,
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
            logger.info("Starting speech recognition with faster-whisper...")
            
            # Try to use faster-whisper directly with better error handling
            from faster_whisper import WhisperModel
            
            # Create temporary audio file
            temp_audio = os.path.join("/tmp", f"temp_audio_{uuid.uuid4().hex[:8]}.wav")
            
            # Extract audio from video
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian
                '-ac', '1',  # Convert to mono
                '-ar', '16000',  # 16kHz sample rate for faster-whisper
                '-f', 'wav',  # Force WAV format
                '-y',
                temp_audio
            ]
            
            # Extract audio
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            
            if not os.path.exists(temp_audio):
                logger.warning("Audio extraction failed, using simple subtitles")
                return self._generate_simple_subtitles(duration)
            
            # Set custom cache directory to avoid permission issues
            os.environ['HF_HOME'] = '/tmp/.cache/huggingface'
            os.environ['TRANSFORMERS_CACHE'] = '/tmp/.cache/transformers'
            
            # Load faster-whisper model
            model = WhisperModel("base", device="cpu", compute_type="int8", download_root="/tmp/.cache/whisper")
            
            # Transcribe audio
            segments, info = model.transcribe(
                temp_audio,
                language="ru",  # Russian language
                word_timestamps=True,
                task="transcribe"
            )
            
            # Convert to subtitle format
            subtitles = []
            for segment in segments:
                if segment.text.strip():
                    subtitles.append({
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text.strip()
                    })
            
            # Clean up
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            logger.info(f"Generated {len(subtitles)} subtitle segments")
            return subtitles
            
        except ImportError as e:
            logger.warning(f"faster-whisper not available: {e}")
            return self._generate_simple_subtitles(duration)
        except Exception as e:
            logger.error(f"faster-whisper transcription failed: {e}")
            # Clean up temp file if it exists
            temp_audio = locals().get('temp_audio')
            if temp_audio and os.path.exists(temp_audio):
                os.remove(temp_audio)
            # Return simple demo subtitles
            logger.info("Generated 10 simple subtitle segments")
            return self._generate_simple_subtitles(duration)
    
    def _generate_srt_file(self, subtitles: List[Dict[str, Any]], srt_path: str):
        """Generates an SRT subtitle file from subtitle data."""
        def to_srt_time(seconds: float) -> str:
            """Converts seconds to SRT time format (HH:MM:SS,ms)."""
            if seconds < 0: seconds = 0
            millis = int((seconds % 1) * 1000)
            seconds = int(seconds)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles):
                f.write(f"{i + 1}\n")
                f.write(f"{to_srt_time(sub['start'])} --> {to_srt_time(sub['end'])}\n")
                f.write(f"{sub['text'].strip()}\n\n")
        logger.info(f"Generated SRT file at: {srt_path}")

    def _burn_subtitles_with_ffmpeg(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        font_path: str = None,
        video_height: int = 1920
    ) -> str:
        """Burns subtitles into a video file using FFmpeg for high performance."""
        logger.info(f"Burning subtitles into {video_path} using FFmpeg...")

        # Determine font to use for subtitles
        if font_path and os.path.exists(font_path):
            font_dir_for_ffmpeg = os.path.dirname(os.path.abspath(font_path))
            font_name_for_style = os.path.splitext(os.path.basename(font_path))[0]
        else:
            kaph_path = "/app/fonts/Kaph/static/Kaph-Regular.ttf"
            if os.path.exists(kaph_path):
                font_dir_for_ffmpeg = "/app/fonts/Kaph/static"
                font_name_for_style = "Kaph-Regular"
            else: # Fallback to DejaVu
                font_dir_for_ffmpeg = "/usr/share/fonts/truetype/dejavu"
                font_name_for_style = "DejaVu Sans"

        # Sanitize paths for FFmpeg's vf_subtitles filter
        sanitized_srt_path = srt_path.replace('\\', '/').replace(':', '\\:')
        sanitized_font_dir = font_dir_for_ffmpeg.replace('\\', '/').replace(':', '\\:')
        
        # Dynamic font size based on video height
        font_size = int(video_height * 0.03) # 3% of video height for better fit

        # Style for subtitles: White text, with a semi-transparent black box for readability, centered at the bottom.
        # PrimaryColour is in &HBBGGRR format. White is &HFFFFFF.
        # BackColour is &HAABBGGRR format. ~56% transparent black is &H90000000.
        # BorderStyle=3 includes a background box. Alignment=2 is bottom-center.
        style_string = (
            f"FontName='{font_name_for_style}',"
            f"FontSize={font_size},"
            f"PrimaryColour=&HFFFFFF,"
            f"BorderStyle=3,"
            f"BackColour=&H90000000,"
            f"OutlineColour=&H90000000,"
            f"Alignment=2,"
            f"MarginV=40" # 40 pixels from the bottom
        )

        video_filter = f"subtitles='{sanitized_srt_path}':fontsdir='{sanitized_font_dir}':force_style='{style_string}'"
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', video_filter,
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'veryfast', # A good balance of speed and quality
            '-crf', '23',
            '-y',
            output_path
        ]

        try:
            logger.info(f"Executing FFmpeg command for subtitle burn...")
            # Use a higher timeout because subtitle burning can be slow on shared CPUs
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1800) # 30 min timeout
            logger.info(f"Successfully burned subtitles. Output: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg subtitle burning failed. STDOUT: {e.stdout}. STDERR: {e.stderr}")
            raise RuntimeError(f"FFmpeg failed while burning subtitles: {e.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg subtitle burning timed out.")
            raise RuntimeError("FFmpeg subtitle burning timed out.")

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
                
                # Calculate end time for this fragment
                if i == num_fragments - 1:
                    # Last fragment - use remaining duration
                    end_time = total_duration
                    actual_duration = total_duration - start_time
                else:
                    end_time = start_time + fragment_duration
                    actual_duration = fragment_duration
                
                # Skip fragments that are too short
                if actual_duration < 5:
                    continue
                
                fragment_filename = f"fragment_{i+1:03d}_{title.replace(' ', '_')[:20]}.mp4"
                fragment_path = os.path.join(self.output_dir, fragment_filename)
                
                # Cut fragment
                fragment_clip = video.subclip(start_time, end_time)
                
                # Save fragment
                try:
                    fragment_clip.write_videofile(
                        fragment_path,
                        fps=SHORTS_FPS,
                        codec='libx264',
                        audio_codec='aac',
                        temp_audiofile=f'/tmp/temp-audio-frag-{uuid.uuid4().hex[:8]}.m4a',
                        remove_temp=True,
                        logger=None,
                        preset='ultrafast'
                    )
                except Exception as e:
                    logger.warning(f"Failed to save fragment {i+1}: {e}")
                    # Try without audio as a fallback
                    fragment_clip.write_videofile(
                        fragment_path,
                        fps=SHORTS_FPS,
                        codec='libx264',
                        audio=False,
                        temp_audiofile=None,
                        remove_temp=True,
                        logger=None,
                        preset='ultrafast'
                    )
                
                # Get fragment info
                if os.path.exists(fragment_path):
                    fragments.append({
                        'fragment_number': i + 1,
                        'filename': fragment_filename,
                        'local_path': fragment_path,
                        'duration': actual_duration,
                        'start_time': start_time,
                        'size_bytes': os.path.getsize(fragment_path),
                        'resolution': f"{fragment_clip.w}x{fragment_clip.h}",
                        'fps': SHORTS_FPS
                    })
                
                fragment_clip.close()
            
            video.close()
            return fragments
            
        except Exception as e:
            logger.error(f"Failed to create fragments: {e}")
            return fragments
    
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
        
        return quality_map.get(quality, (SHORTS_WIDTH, SHORTS_HEIGHT)) 