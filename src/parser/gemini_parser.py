"""Scene extraction using Gemini 2.5 Flash."""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from ..common import get_api_key, retry_with_backoff

logger = logging.getLogger(__name__)


class SceneExtractor:
    """Extracts visual scenes from chapter text using Gemini."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize scene extractor.

        Args:
            model_name: Gemini model to use (defaults to gemini-2.5-flash)
        """
        api_key = get_api_key("gemini")
        genai.configure(api_key=api_key)

        if not model_name:
            model_name = "gemini-2.5-flash"

        self.model = genai.GenerativeModel(model_name)

    def extract_scenes(self, chapter_text: str, max_scenes: int = 6) -> List[Dict[str, Any]]:
        """
        Extract visual scenes from chapter text.

        Args:
            chapter_text: Full chapter text
            max_scenes: Maximum number of scenes to extract

        Returns:
            List of scene dictionaries with keys:
            - visual_description: Description for image generation
            - text_segment: Text content for this scene
            - characters: List of character names
            - estimated_duration: Duration in seconds
        """
        # Truncate to avoid token limits
        truncated_text = chapter_text[:30000]

        prompt = f"""
Analyze the following fiction chapter text and break it down into 3-{max_scenes} distinct visual scenes.
For each scene, provide:
1. A "visual_description": A detailed, natural language description of the scene suitable for an AI image generator (Flux).
   - Focus on lighting, composition, subject action, and background.
   - Describe the scene as a "Chinese Manhua/Webtoon panel".
   - Avoid comma-separated tags. Use full sentences.
   - Example: "A low-angle shot of a warrior standing on a cliff edge, silhouetted against a burning sunset, wind blowing through their robes. The art style is vibrant and cel-shaded."
2. The segment of text that corresponds to this scene.
3. A list of characters present.
4. An estimated duration in seconds.

Return the result as a valid JSON list of objects with keys: "visual_description", "text_segment", "characters", "estimated_duration".
Do not include markdown formatting like ```json ... ```, just the raw JSON string.

Chapter Text:
{truncated_text}
"""

        return self._generate_with_retry(prompt)

    @retry_with_backoff(max_attempts=7, min_wait=4, max_wait=60)
    def _generate_with_retry(self, prompt: str) -> List[Dict[str, Any]]:
        """Generate scenes with retry logic."""
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean up potential markdown formatting
            response_text = self._clean_json_response(response_text)

            scenes = json.loads(response_text)
            logger.info(f"Extracted {len(scenes)} scenes")
            return scenes

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "ResourceExhausted" in error_msg:
                logger.warning(f"Rate limit hit: {e}. Retrying...")
                raise  # Let retry decorator handle it
            else:
                logger.error(f"Error extracting scenes: {e}")
                raise

    @staticmethod
    def _clean_json_response(text: str) -> str:
        """Remove markdown formatting from JSON response."""
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        return text.strip()
