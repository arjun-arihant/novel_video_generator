import os
import logging
import requests
import random
import time
from typing import Optional
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self):
        # Pollinations.ai doesn't strictly need an API key for free tier, 
        # but we keep the structure consistent.
        self.enabled = True
        self.base_url = "https://image.pollinations.ai/prompt/"
        
    def generate_image(self, prompt: str, output_path: str, aspect_ratio: str = "landscape"):
        """
        Generate an image from a prompt using Pollinations.ai and save it to output_path.
        """
        if not self.enabled:
            raise RuntimeError("Image generation is disabled.")
            
        return self._generate_with_retry(prompt, output_path, aspect_ratio)

    @retry(
        retry=retry_if_exception_type(Exception), 
        wait=wait_exponential(multiplier=2, min=10, max=120), # Wait longer between retries (min 10s)
        stop=stop_after_attempt(10), # Try more times (queued requests usually succeed eventually)
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _generate_with_retry(self, prompt: str, output_path: str, aspect_ratio: str):
        try:
            logger.info(f"Generating image with Pollinations.ai for prompt: {prompt[:50]}...")
            
            # Refine prompt for Flux (Natural Language, no "tag soup")
            # User Feedback: "Flux hates tag soup... Write natural, descriptive sentences."
            # We assume the incoming prompt is relatively descriptive.
            # We append a natural style suffix instead of tags.
            
            style_suffix = " in a beautiful Chinese manhua webtoon style, clean line art, vibrant colors, cinematic lighting, 4k resolution"
            if "manhua" not in prompt.lower():
                refined_prompt = f"{prompt}{style_suffix}"
            else:
                refined_prompt = prompt
                
            # 1. Define params
            # Map aspect ratio to dimensions
            # User recommended: 1280x720 for landscape (Video), 768x1152 for portrait (Manhua native)
            if aspect_ratio == "portrait":
                width, height = 768, 1152 # 2:3 ratio approx
            else:
                width, height = 1280, 720 # 16:9 Landscape (Video Default)
            
            # 2. Construct Payload (POST Method)
            # Using POST is more robust for long prompts and avoids URL length limits
            payload = {
                "prompt": refined_prompt,
                "model": "flux-anime",
                "width": width,
                "height": height,
                "nologo": True,
                "enhance": False,
                "seed": random.randint(1, 1000000)
            }
            
            # 3. Make request
            # Pollinations accepts POST at /prompt
            url = "https://image.pollinations.ai/prompt"
            
            # Increased timeout to 120s as Flux models can be slow and queue can be long
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Image saved to {output_path} (Seed: {payload['seed']})")
                return output_path
            else:
                raise Exception(f"Pollinations API returned {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise e
