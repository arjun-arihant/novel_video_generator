import os
import json
import logging
import google.generativeai as genai
from typing import List, Dict, Any
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SceneExtractor:
    def __init__(self, model_name: str = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Try GOOGLE_API_KEY as fallback
            api_key = os.getenv("GOOGLE_API_KEY")
            
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables")
            
        genai.configure(api_key=api_key)
        
        if not model_name:
            # User explicitly requested gemini-2.5-flash
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            
        self.model = genai.GenerativeModel(model_name)

    def extract_scenes(self, chapter_text: str) -> List[Dict[str, Any]]:
        """
        Extracts scenes from chapter text using Gemini.
        Returns a list of scene dictionaries.
        """
        prompt = f"""
        Analyze the following fiction chapter text and break it down into 3-6 distinct visual scenes.
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
        {chapter_text[:30000]} 
        """
        # Truncate to avoid token limits if necessary, though 1.5 handles large context well.
        
        return self._generate_with_retry(prompt)

    @retry(
        retry=retry_if_exception_type(Exception), 
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(7),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _generate_with_retry(self, prompt: str) -> List[Dict[str, Any]]:
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up potential markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            scenes = json.loads(response_text)
            return scenes
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                logger.warning(f"Rate limit hit: {e}. Retrying...")
                raise e # Let tenacity handle it
            else:
                logger.error(f"Error extracting scenes: {e}")
                raise

