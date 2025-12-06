# Novel Video Generator

A Python pipeline that converts novel chapters (text) into animated videos with narration.

## Features

- **Scene Extraction**: Uses **Gemini 2.5 Flash Image Preview** to analyze text and extract visual scenes.
- **Image Generation**: Uses **Gemini 2.5 Flash Image Preview** to generate high-quality images.
- **Style**: Enforces a **Chinese Manhua/Webtoon** aesthetic.
- **Narration**: Uses **Google Cloud Text-to-Speech** (Neural2 voices) for high-quality audio.
- **Animation**: Applies **Ken Burns effect** (Pan/Zoom) to static images.
- **Video Assembly**: Combines images, audio, and effects into a final `.mp4`.

## Prerequisites

- Python 3.10+
- **Google Cloud Project** with:
    - Gemini API enabled (for text/images)
    - Cloud Text-to-Speech API enabled (for audio)
- `ffmpeg` installed and in your system PATH.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd novel_video_generator
    ```

2.  **Install dependencies**:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\Activate
    pip install -r requirements.txt
    ```

3.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_gemini_api_key
    GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
    ```
    *Note: Google Cloud TTS requires a service account JSON key.*

## Usage

Run the full pipeline on a chapter file:

```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe scripts/run_pipeline.py --chapter data/ihacw/chapters/ihacw_ch0001.json
```

## Output

- **Video**: `data/videos/video_<chapter_id>.mp4`
- **Scenes**: `data/scenes/scenes_<chapter_id>.json`
- **Images**: `data/images/chapter_<chapter_id>/`
- **Audio**: `data/audio/chapter_<chapter_id>/`

## Configuration

- **Voices**: Edit `configs/voices.yaml` to change voice assignments (e.g., `en-US-Neural2-D`).