# CLAUDE.md

## Project Overview
Novel Video Generator: Converts text chapters into animated videos with narration.

## Commands

### Run Full Pipeline
```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe scripts/run_pipeline.py --chapter data/ihacw/chapters/ihacw_ch0001.json
```

### Individual Steps
- **Scene Extraction**: `scripts/run_scene_extraction.py`
- **Image Generation**: `scripts/run_image_generation.py`
- **TTS Generation**: `scripts/run_tts.py`
- **Video Assembly**: `scripts/run_video_build.py`

## Architecture
- `src/parser`: Gemini 2.5 Flash based scene extraction.
- `src/image`: Pollinations.ai Flux models for image generation (Manhua style).
- `src/tts`: Gemini TTS (gemini-2.5-flash-preview-tts).
- `src/video`: MoviePy based assembly with Ken Burns effect.

## Environment
- `GEMINI_API_KEY`: For Gemini 2.5 (Text, Images, and TTS).
