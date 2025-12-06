import os
import logging
from typing import Optional
from google.cloud import texttospeech
from .base import TTSProvider, VoiceConfig

logger = logging.getLogger(__name__)

from google.api_core import client_options

class GoogleTTSProvider(TTSProvider):
    """
    TTS Provider using Google Cloud Text-to-Speech.
    """
    
    def __init__(self):
        try:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                options = client_options.ClientOptions(api_key=api_key)
                self.client = texttospeech.TextToSpeechClient(client_options=options)
                logger.info("Google Cloud TTS Client initialized with API Key")
            else:
                # Fallback to ADC
                self.client = texttospeech.TextToSpeechClient()
                logger.info("Google Cloud TTS Client initialized with ADC")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud TTS: {e}")
            raise

    async def generate_audio(self, text: str, output_path: str, voice_config: VoiceConfig) -> Optional[str]:
        try:
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Build the voice request
            # Parse voice name (e.g., "en-US-Neural2-A")
            lang_code = "-".join(voice_config.name.split("-")[:2]) # en-US
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_config.name
            )

            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=voice_config.rate,
                pitch=voice_config.pitch
            )

            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # The response's audio_content is binary.
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
                
            return output_path

        except Exception as e:
            logger.error(f"Error generating audio with Google TTS: {e}")
            return None
