import asyncio
import os
from src.tts.manager import TTSManager

async def test_tts():
    print("Testing TTS Module...")
    
    manager = TTSManager()
    provider = manager.get_provider("edge")
    voice_id = manager.get_voice_id("narrator")
    
    print(f"Provider: {provider}")
    print(f"Voice ID: {voice_id}")
    
    output_file = "test_audio.mp3"
    text = "Hello! This is a test of the novel video generator text to speech system."
    
    print(f"Generating audio for: '{text}'")
    await provider.generate_audio(text, output_file, voice_id)
    
    if os.path.exists(output_file):
        print(f"Success! Audio saved to {output_file}")
        print(f"File size: {os.path.getsize(output_file)} bytes")
        # Clean up
        os.remove(output_file)
        print("Test file removed.")
    else:
        print("Error: File was not created.")

if __name__ == "__main__":
    asyncio.run(test_tts())
