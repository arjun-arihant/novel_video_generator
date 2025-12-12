"""Image generation using Pollinations.ai Flux models."""

import logging
import random
from pathlib import Path
from typing import Optional, Union

import requests

from ..common import retry_with_backoff

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generates images using Pollinations.ai Flux API."""

    def __init__(self, model: str = "flux-anime"):
        """
        Initialize image generator.

        Args:
            model: Flux model to use (flux-anime, flux, etc.)
        """
        self.model = model
        self.base_url = "https://image.pollinations.ai/prompt"

    def generate(
        self,
        prompt: str,
        output_path: Union[str, Path],
        aspect_ratio: str = "landscape"
    ) -> bool:
        """
        Generate an image from a prompt.

        Args:
            prompt: Text description of the image
            output_path: Path where image will be saved
            aspect_ratio: "landscape" (16:9) or "portrait" (2:3)

        Returns:
            True if successful, False otherwise
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._generate_with_retry(prompt, output_path, aspect_ratio)
            return True
        except Exception as e:
            logger.error(f"Failed to generate image after retries: {e}")
            return False

    @retry_with_backoff(max_attempts=10, min_wait=10, max_wait=120)
    def _generate_with_retry(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str
    ) -> None:
        """Generate image with retry logic."""
        logger.info(f"Generating image: {prompt[:50]}...")

        # Enhance prompt with style description
        enhanced_prompt = self._enhance_prompt(prompt)
        
        # Get dimensions based on aspect ratio - include in prompt since query params cause 502
        width, height = self._get_dimensions(aspect_ratio)
        
        # Add resolution hint to prompt instead of using query params (Pollinations API is buggy with params)
        dimension_hint = f" --ar {width}:{height}"
        enhanced_prompt_with_size = enhanced_prompt + dimension_hint

        # Pollinations.ai API - using minimal params to avoid 502 errors
        # The full param API is broken, so we just use the basic endpoint
        import urllib.parse
        encoded_prompt = urllib.parse.quote(enhanced_prompt_with_size)
        
        # Simplified URL - query params are causing 502 errors
        url = f"{self.base_url}/{encoded_prompt}"

        logger.debug(f"Requesting: {url[:100]}...")

        # Make GET request
        response = requests.get(
            url,
            timeout=120
        )

        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Image saved to {output_path}")
        else:
            error_msg = f"Pollinations API returned {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    @staticmethod
    def _enhance_prompt(prompt: str) -> str:
        """Enhance prompt with style description."""
        style_suffix = (
            " in a beautiful Chinese manhua webtoon style, "
            "clean line art, vibrant colors, cinematic lighting, 4k resolution"
        )

        if "manhua" not in prompt.lower():
            return f"{prompt}{style_suffix}"

        return prompt

    @staticmethod
    def _get_dimensions(aspect_ratio: str) -> tuple[int, int]:
        """
        Get image dimensions based on aspect ratio.

        Args:
            aspect_ratio: "landscape" or "portrait"

        Returns:
            Tuple of (width, height)
        """
        if aspect_ratio == "portrait":
            return 768, 1152  # 2:3 ratio
        else:
            return 1280, 720  # 16:9 ratio
