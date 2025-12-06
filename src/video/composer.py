import logging
import os
from pathlib import Path
from typing import List, Dict, Any
from moviepy import *

logger = logging.getLogger(__name__)

class VideoComposer:
    def __init__(self):
        pass

    def create_video(self, scenes: List[Dict[str, Any]], audio_dir: str, image_dir: str, output_path: str):
        """
        Assemble video from scenes, images, and audio.
        """
        clips = []
        audio_dir = Path(audio_dir)
        image_dir = Path(image_dir)
        
        logger.info(f"Assembling video with {len(scenes)} scenes...")

        for i, scene in enumerate(scenes):
            # Find corresponding assets
            # Assuming 1 image per scene for now
            image_path = image_dir / f"scene_{i:03d}.png"
            # Audio might be split by paragraphs or one per scene. 
            # For this implementation, let's assume we need to match audio to scene text.
            # BUT, our TTS script generated audio per paragraph.
            # We need a way to map scene text to audio files.
            # SIMPLIFICATION: For now, let's assume the TTS script was run with a mode that matches scenes, 
            # OR we just take all audio files in order and try to match duration?
            # Better: Let's update the pipeline to generate TTS *per scene* instead of per paragraph for this flow.
            # OR: We just grab all audio files for the chapter and concatenate them, 
            # and show images for duration = total_audio_duration / num_images? No, that's bad.
            
            # Let's assume for this "Scene-based" flow, we will generate TTS for the scene text specifically.
            # I will add a method to generate TTS for scenes in the pipeline script.
            
            audio_path = audio_dir / f"scene_{i:03d}.mp3"
            
            if not image_path.exists():
                logger.warning(f"Image not found for scene {i}: {image_path}")
                # Use a placeholder or skip? Skip for now.
                continue
                
            if not audio_path.exists():
                logger.warning(f"Audio not found for scene {i}: {audio_path}")
                continue

            # Create Audio Clip
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration
            
            # Create Image Clip with Ken Burns Effect (Pan/Zoom)
            # Standard 1080p
            w, h = 1920, 1080
            
            # Load image
            img_clip = ImageClip(str(image_path)).with_duration(duration)
            
            # Resize to be slightly larger than screen to allow for movement (e.g. 1.2x)
            # We want to zoom from 1.0 to 1.15 or pan
            
            # Simple Zoom In effect:
            # Resize from 100% to 115% over duration, centered
            def zoom_in(t):
                scale = 1 + 0.15 * (t / duration)
                return scale

            # Apply resize transformation
            # Note: In moviepy v2, resizing might be expensive per frame. 
            # A more efficient way for simple zoom is using 'resize' with a function.
            
            # Ensure base size fits height
            img_clip = img_clip.resized(height=h*1.2) # Start slightly larger
            
            # Center crop to 16:9
            img_clip = img_clip.cropped(width=w, height=h, x_center=img_clip.w/2, y_center=img_clip.h/2)
            
            # Apply zoom
            # For moviepy, we can use 'resize' with a lambda, but it can be slow.
            # Let's try a simple linear zoom.
            img_clip = img_clip.resized(lambda t: 1 + 0.05 * t / duration)
            
            # Re-crop to ensure we stay within 1920x1080 after zoom
            img_clip = img_clip.with_position("center")
            
            video_clip = img_clip.with_audio(audio_clip)
            clips.append(video_clip)

        if not clips:
            logger.error("No clips created.")
            return

        final_video = concatenate_videoclips(clips, method="compose")
        
        logger.info(f"Writing video to {output_path}...")
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        logger.info("Video generation complete.")
