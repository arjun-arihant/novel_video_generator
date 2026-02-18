"""Video composition using FFmpeg directly."""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


class VideoComposer:
    """Assembles final video from scenes, images, and audio using FFmpeg."""

    def __init__(self, resolution: tuple[int, int] = (1920, 1080), fps: int = 24):
        """
        Initialize video composer.

        Args:
            resolution: Output resolution (width, height)
            fps: Frames per second
        """
        self.resolution = resolution
        self.fps = fps
        self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> None:
        """Verify FFmpeg is installed and accessible."""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("FFmpeg found: %s", result.stdout.split('\n')[0])
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg and add it to your PATH. "
                "Download from: https://ffmpeg.org/download.html"
            ) from e

    def create_video(
        self,
        scenes: List[Dict[str, Any]],
        image_dir: Union[str, Path],
        audio_dir: Union[str, Path],
        output_path: Union[str, Path]
    ) -> bool:
        """
        Assemble video from scenes, images, and audio.

        Args:
            scenes: List of scene dictionaries
            image_dir: Directory containing scene images
            audio_dir: Directory containing scene audio
            output_path: Path for output video file

        Returns:
            True if successful, False otherwise
        """
        image_dir = Path(image_dir)
        audio_dir = Path(audio_dir)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Assembling video with {len(scenes)} scenes using FFmpeg...")

        # Create temporary directory for intermediate clips
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            scene_clips = []

            # Generate individual scene clips
            for i in range(len(scenes)):
                image_path = image_dir / f"scene_{i:03d}.png"
                audio_path = audio_dir / f"scene_{i:03d}.wav"
                clip_path = temp_path / f"clip_{i:03d}.mp4"

                if not image_path.exists():
                    logger.warning(f"Image not found for scene {i}: {image_path}")
                    continue

                if not audio_path.exists():
                    logger.warning(f"Audio not found for scene {i}: {audio_path}")
                    continue

                try:
                    success = self._create_scene_clip(
                        image_path, audio_path, clip_path
                    )
                    if success:
                        scene_clips.append(clip_path)
                        logger.info(f"Created clip {i+1}/{len(scenes)}")
                except Exception as e:
                    logger.error(f"Failed to create clip for scene {i}: {e}")
                    continue

            if not scene_clips:
                logger.error("No clips created")
                return False

            # Concatenate all clips
            try:
                return self._concatenate_clips(scene_clips, output_path)
            except Exception as e:
                logger.error(f"Failed to concatenate clips: {e}")
                return False

    def _create_scene_clip(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path
    ) -> bool:
        """
        Create a single scene clip with Ken Burns zoom effect.

        Args:
            image_path: Path to scene image
            audio_path: Path to scene audio
            output_path: Path for output clip

        Returns:
            True if successful, False otherwise
        """
        w, h = self.resolution

        # Ken Burns effect: slow zoom from 100% to 105% over the duration
        # zoompan filter: z = zoom factor (1.0 to 1.05), d = duration in frames
        # We'll let FFmpeg match the audio duration automatically
        video_filter = (
            f"scale={int(w*1.2)}:{int(h*1.2)},"  # Scale up for zoom headroom
            f"zoompan=z='min(1+0.05*on/{self.fps}/10,1.05)':"  # Gradual zoom
            f"d=1:s={w}x{h}:fps={self.fps}"
        )

        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-loop', '1',  # Loop the image
            '-i', str(image_path),  # Input image
            '-i', str(audio_path),  # Input audio
            '-vf', video_filter,  # Video filter (Ken Burns)
            '-c:v', 'libx264',  # Video codec
            '-preset', 'medium',  # Encoding preset
            '-crf', '23',  # Quality (lower = better, 23 is good)
            '-c:a', 'aac',  # Audio codec
            '-b:a', '192k',  # Audio bitrate
            '-shortest',  # End when shortest stream ends (audio)
            '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
            str(output_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"FFmpeg output: {result.stderr[-500:]}")  # Last 500 chars
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            return False

    def _concatenate_clips(
        self,
        clip_paths: List[Path],
        output_path: Path
    ) -> bool:
        """
        Concatenate multiple video clips into one.

        Args:
            clip_paths: List of paths to video clips
            output_path: Path for final output video

        Returns:
            True if successful, False otherwise
        """
        # Create concat file for FFmpeg
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False,
            encoding='utf-8'
        ) as f:
            concat_file = Path(f.name)
            for clip_path in clip_paths:
                # FFmpeg concat requires forward slashes even on Windows
                clip_str = str(clip_path).replace('\\', '/')
                f.write(f"file '{clip_str}'\n")

        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',  # Copy streams without re-encoding
                str(output_path)
            ]

            logger.info(f"Concatenating {len(clip_paths)} clips...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Video created: {output_path}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg concatenation error: {e.stderr}")
            return False
        finally:
            # Clean up concat file
            try:
                concat_file.unlink()
            except Exception:
                pass
