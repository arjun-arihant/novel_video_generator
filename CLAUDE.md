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
- `src/parser`: Gemini 2.5 based scene extraction.
- `src/image`: Gemini 2.5 based image generation (Manhua style).
- `src/tts`: Google Cloud TTS (Neural2) + Edge TTS fallback.
- `src/video`: MoviePy based assembly with Ken Burns effect.

## Environment
- `GEMINI_API_KEY`: For Gemini 2.5 (Text & Images).
- `GOOGLE_APPLICATION_CREDENTIALS`: For Google Cloud TTS.
