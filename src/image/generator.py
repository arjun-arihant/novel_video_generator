import os
import logging
import google.generativeai as genai
from typing import Optional
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found")
            
        genai.configure(api_key=api_key)
        self.enabled = True
        try:
            # Use Gemini 2.5 Flash Image Preview which supports native image generation
            self.model = genai.GenerativeModel("gemini-2.5-flash-image-preview")
        except Exception as e:
            logger.error(f"Failed to initialize GenerativeModel: {e}")
            self.enabled = False
            self.model = None

    def generate_image(self, prompt: str, output_path: str, aspect_ratio: str = "16:9"):
        """
        Generate an image from a prompt using Gemini 2.5 and save it to output_path.
        """
        if not self.enabled:
            raise RuntimeError("Image generation is disabled.")
            
        return self._generate_with_retry(prompt, output_path)

    @retry(
        retry=retry_if_exception_type(Exception), 
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(7),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _generate_with_retry(self, prompt: str, output_path: str):
        try:
            logger.info(f"Generating image with Gemini 2.5 for prompt: {prompt[:50]}...")
            
            # For Gemini 2.5, we ask for an image in the text prompt
            response = self.model.generate_content(f"Generate an image of: {prompt}")
            
            # Check for image parts in the response
            if response.parts:
                for part in response.parts:
                    # Check if part has inline_data (image)
                    if hasattr(part, "inline_data") and part.inline_data:
                        # This is likely the image data
                        # The data is already bytes if accessed via inline_data.data usually
                        img_data = part.inline_data.data
                        
                        with open(output_path, 'wb') as f:
                            f.write(img_data)
                        logger.info(f"Image saved to {output_path}")
                        return output_path
            
            logger.warning("No image data found in response.")
            return None
                
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                logger.warning(f"Rate limit hit: {e}. Retrying...")
                raise e
            
            logger.error(f"Error generating image: {e}")
            # Fallback to placeholder ONLY if it's NOT a rate limit error (or after retries exhausted)
            # But here we are inside the retry loop, so we should raise if it's retryable.
            # If it's another error, we might want to fallback immediately.
            # Let's assume we fallback only on final failure or non-retryable error.
            # Actually, tenacity will catch the raise.
            raise e
