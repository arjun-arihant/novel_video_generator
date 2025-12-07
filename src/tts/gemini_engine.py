import os
import requests
import json
import logging
from typing import Optional
from .base import TTSProvider, VoiceConfig

logger = logging.getLogger(__name__)

class GeminiTTSProvider(TTSProvider):
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found")
        
        # Use a compatible model. gemini-2.0-flash-exp is multimodal.
        # User requested gemini-2.5-flash.
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash") 
        # is_flash_2_5 = "2.5" in self.model # Not logic needed if we trust the string.
        
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate_audio(self, text: str, output_path: str, voice_config: VoiceConfig) -> Optional[str]:
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            # Prompt engineering to force reading
            # For Gemini multimodal output, we likely need to prompt it to 'speak'.
            # However, exact 'text-to-speech' model might have different payload.
            # Assuming standard multimodal generateContent with audio response.
            
            # User's hint suggests tools might be needed or specific structure.
            # "tools": [{"google_search_retrieval": {}}] was in the hint, unrelated to TTS but maybe structure matters.
            # But the key for TTS is likely just requesting audio.
            
            # Back to basics: Just responseMimeType. 
            # If that failed before, maybe the prompt needs to be "say this"?
            
            # Trying user's exact suggestion: including 'tools'
            
            # Standard Gemini Audio Generation Payload
            # If this model supports audio output, this is the correct way.
            
            payload = {
                "contents": [{
                    "parts": [{"text": f"Please read this text out loud: {text}"}]
                }],
                "generationConfig": {
                    "responseMimeType": "audio/mp3"
                }
            }

            url = f"{self.base_url}?key={self.api_key}"
            
            logger.info(f"Generating TTS with Gemini ({self.model})...")
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            
            if response.status_code != 200:
                logger.error(f"Gemini TTS request failed: {response.status_code} - {response.text}")
                # Try to print more details
                try: 
                    error_details = response.json()
                    logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
                except:
                    pass
                return None
                
            response_json = response.json()
            
            # Parse response for audio bytes
            # Structure usually: candidates[0].content.parts[0].inlineData.data (base64)
            # But with audio/mp3 mimetype, it might return binary or base64.
            # Let's inspect typical Gemini response structure.
            
            try:
                # Basic check for Safety/Recitation errors
                if 'promptFeedback' in response_json and response_json['promptFeedback'].get('blockReason'):
                     logger.warning(f"Blocked: {response_json['promptFeedback']}")
                     return None
                     
                candidates = response_json.get('candidates', [])
                if not candidates:
                    logger.warning("No candidates returned from Gemini.")
                    return None
                    
                part = candidates[0]['content']['parts'][0]
                
                # If audio is returned, it's likely inlineData (base64)
                if 'inlineData' in part:
                    import base64
                    audio_data = base64.b64decode(part['inlineData']['data'])
                    with open(output_path, 'wb') as f:
                        f.write(audio_data)
                    logger.info(f"Audio saved to {output_path}")
                    return output_path
                else:
                    logger.warning(f"No inlineData (audio) found. Response might be text: {part.get('text')}")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to parse Gemini TTS response: {e}")
                logger.debug(f"Full response: {response_json}")
                return None

        except Exception as e:
            logger.error(f"Gemini TTS error: {e}")
            return None
