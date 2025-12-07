"""Gemini TTS provider implementation."""

import base64
import json
import logging
from pathlib import Path
from typing import Optional, Union

import requests

from ..common import get_api_key
from .base import TTSProvider, VoiceConfig

logger = logging.getLogger(__name__)

class GeminiTTSProvider(TTSProvider):
    """TTS provider using Gemini 2.5 Flash API."""

    def __init__(self, model: str = "gemini-2.5-flash-preview-tts"):
        """
        Initialize Gemini TTS provider.

        Args:
            model: Gemini model to use for TTS
        """
        self.api_key = get_api_key("gemini")
        self.model = model
        self.base_url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent"
        )

    async def generate_audio(
        self,
        text: str,
        output_path: Union[str, Path],
        voice_config: VoiceConfig
    ) -> Optional[str]:
        """
        Generate audio from text using Gemini API.

        Args:
            text: Text to convert to speech
            output_path: Path where audio file will be saved
            voice_config: Voice configuration (uses voice name for Gemini voice selection)

        Returns:
            Path to saved audio file, or None if generation failed
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            headers = {"Content-Type": "application/json"}

            # Gemini TTS API payload
            payload = {
                "contents": [{
                    "parts": [{"text": text}]
                }],
                "generationConfig": {
                    "responseMimeType": "audio/mp3",
                    "speechConfig": {
                        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_config.name}}
                    }
                }
            }

            url = f"{self.base_url}?key={self.api_key}"

            logger.info(f"Generating TTS with Gemini ({self.model}, voice: {voice_config.name})...")
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)

            if response.status_code != 200:
                logger.error(
                    f"Gemini TTS request failed: {response.status_code} - {response.text}"
                )
                try:
                    error_details = response.json()
                    logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
                except Exception:
                    pass
                return None

            response_json = response.json()

            # Check for safety/recitation blocks
            if 'promptFeedback' in response_json and response_json['promptFeedback'].get('blockReason'):
                logger.warning(f"Content blocked: {response_json['promptFeedback']}")
                return None

            candidates = response_json.get('candidates', [])
            if not candidates:
                logger.warning("No candidates returned from Gemini.")
                return None

            part = candidates[0]['content']['parts'][0]

            # Extract audio from inlineData (base64 encoded)
            if 'inlineData' in part:
                audio_data = base64.b64decode(part['inlineData']['data'])
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                logger.info(f"Audio saved to {output_path}")
                return str(output_path)
            else:
                logger.warning(
                    f"No audio data found in response. "
                    f"Response might be text: {part.get('text', '')[:100]}"
                )
                return None

        except Exception as e:
            logger.error(f"Gemini TTS error: {e}", exc_info=True)
            return None
