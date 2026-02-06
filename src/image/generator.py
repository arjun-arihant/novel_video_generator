"""Image generation using Want2GP Z-Image models."""

import logging
from pathlib import Path
from typing import Optional, Union

import requests

from ..common import get_config, retry_with_backoff

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generates images using Want2GP Z-Image API."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize image generator.

        Args:
            model: Want2GP image model to use (defaults to z-image).
        """
        config = get_config().want2gp
        self.model = model or config.image_model
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.timeout = config.timeout

    def generate(
        self,
        prompt: str,
        output_path: Union[str, Path],
        aspect_ratio: str = "landscape",
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
            logger.error("Failed to generate image after retries: %s", e)
            return False

    @retry_with_backoff(max_attempts=10, min_wait=10, max_wait=120)
    def _generate_with_retry(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str,
    ) -> None:
        """Generate image with retry logic."""
        logger.info("Generating image: %s...", prompt[:80])

        enhanced_prompt = self._enhance_prompt(prompt)
        width, height = self._get_dimensions(aspect_ratio)

        payload = {
            "model": self.model,
            "prompt": enhanced_prompt,
            "width": width,
            "height": height,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/images/generations"
        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(
                f"Want2GP image error {response.status_code}: {response.text[:200]}"
            )

        content_type = response.headers.get("Content-Type", "")
        if content_type.startswith("image/"):
            image_bytes = response.content
        else:
            data = response.json()
            image_bytes = self._extract_image_bytes(data)

        if not image_bytes:
            raise RuntimeError("No image data returned from Want2GP.")

        with open(output_path, "wb") as f:
            f.write(image_bytes)
        logger.info("Image saved to %s", output_path)

    @staticmethod
    def _enhance_prompt(prompt: str) -> str:
        """Enhance prompt with style description."""
        style_suffix = (
            " in a detailed cinematic manhua webtoon style, "
            "clean line art, vibrant colors, soft depth of field, 4k resolution"
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
        return 1280, 720  # 16:9 ratio

    @staticmethod
    def _extract_image_bytes(data: dict) -> Optional[bytes]:
        """Extract image bytes from Want2GP responses."""
        if "data" in data and data["data"]:
            item = data["data"][0]
            if "b64_json" in item:
                import base64

                return base64.b64decode(item["b64_json"])
            if "url" in item:
                response = requests.get(item["url"], timeout=120)
                response.raise_for_status()
                return response.content
        if "image" in data:
            import base64

            return base64.b64decode(data["image"])
        return None
