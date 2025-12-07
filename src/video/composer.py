"""Video composition using MoviePy."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from moviepy import *

logger = logging.getLogger(__name__)


class VideoComposer:
    """Assembles final video from scenes, images, and audio."""

    def __init__(self, resolution: tuple[int, int] = (1920, 1080), fps: int = 24):
        """
        Initialize video composer.

        Args:
            resolution: Output resolution (width, height)
            fps: Frames per second
        """
        self.resolution = resolution
        self.fps = fps

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

        logger.info(f"Assembling video with {len(scenes)} scenes...")

        clips = []

        for i in range(len(scenes)):
            image_path = image_dir / f"scene_{i:03d}.png"
            audio_path = audio_dir / f"scene_{i:03d}.mp3"

            if not image_path.exists():
                logger.warning(f"Image not found for scene {i}: {image_path}")
                continue

            if not audio_path.exists():
                logger.warning(f"Audio not found for scene {i}: {audio_path}")
                continue

            try:
                clip = self._create_scene_clip(image_path, audio_path)
                clips.append(clip)
                logger.info(f"Added clip {i+1}/{len(scenes)}")
            except Exception as e:
                logger.error(f"Failed to create clip for scene {i}: {e}")
                continue

        if not clips:
            logger.error("No clips created")
            return False

        try:
            final_video = concatenate_videoclips(clips, method="compose")
            logger.info(f"Writing video to {output_path}...")
            final_video.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="libx264",
                audio_codec="aac"
            )
            logger.info("Video generation complete")
            return True

        except Exception as e:
            logger.error(f"Failed to create final video: {e}")
            return False

    def _create_scene_clip(
        self,
        image_path: Path,
        audio_path: Path
    ) -> CompositeVideoClip:
        """
        Create a single scene clip with Ken Burns effect.

        Args:
            image_path: Path to scene image
            audio_path: Path to scene audio

        Returns:
            Video clip with audio
        """
        # Load audio to get duration
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration

        # Load and prepare image
        img_clip = ImageClip(str(image_path)).with_duration(duration)

        # Apply Ken Burns effect (slow zoom)
        img_clip = self._apply_ken_burns_effect(img_clip, duration)

        # Combine image and audio
        return img_clip.with_audio(audio_clip)

    def _apply_ken_burns_effect(
        self,
        clip: ImageClip,
        duration: float
    ) -> ImageClip:
        """
        Apply Ken Burns zoom effect to image clip.

        Args:
            clip: Image clip
            duration: Duration in seconds

        Returns:
            Clip with zoom effect applied
        """
        w, h = self.resolution

        # Resize to slightly larger than output to allow zoom
        clip = clip.resized(height=int(h * 1.2))

        # Center crop to target resolution
        clip = clip.cropped(
            width=w,
            height=h,
            x_center=clip.w / 2,
            y_center=clip.h / 2
        )

        # Apply gradual zoom (1.0x to 1.05x over duration)
        def zoom_function(t):
            return 1 + 0.05 * (t / duration)

        clip = clip.resized(zoom_function)
        clip = clip.with_position("center")

        return clip
