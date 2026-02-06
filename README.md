# Novel Video Generator

A modern Python pipeline + Web UI that converts novel chapters into narrated, illustrated videos.

## Highlights

- **Step-by-step workflow**: upload EPUB → choose chapters → review scenes → generate video
- **LLM extraction (OpenRouter)**: scene segmentation with narration + dialogue split
- **Image generation (Want2GP Z-Image)**: consistent Manhua-style scene art
- **TTS (Want2GP Qwen3:tts)**: narrator + character voices with per-character presets
- **Consistency store**: persistent character & location profiles for visual continuity
- **Batch mode**: generate multiple chapters without manual scene review

## Prerequisites

- Python 3.10+
- **OpenRouter API key** (scene extraction)
- **Want2GP API key** (image + TTS)
- `ffmpeg` installed and in your system PATH

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```env
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=openrouter/auto
WANT2GP_API_KEY=your_want2gp_key
WANT2GP_BASE_URL=http://localhost:8000/v1
WANT2GP_IMAGE_MODEL=z-image
WANT2GP_TTS_MODEL=qwen3:tts
```

## Web UI

```bash
streamlit run -m src.web.app
```

### Web UI Flow

1. **Upload EPUB** → chapters extracted
2. **Select chapter(s)** → estimated narration length (180 wpm)
3. **Choose narrator voice** → 10 presets (5 male, 5 female)
4. **Scene review (optional)** → edit scene visuals, narration, dialogues
5. **Generate** → images, audio, and final stitched video

Batch mode skips the scene review and goes straight to generation.

## CLI Usage

```bash
# Full pipeline
python cli.py pipeline data/ihacw/chapters/ihacw_ch0001.json

# Individual steps
python cli.py extract chapter.json
python cli.py images scenes.json
python cli.py audio scenes.json
python cli.py video scenes.json
```

## Scene Format

Scenes include narration and dialogue split to enable character voices:

```json
{
  "id": 1,
  "title": "A distant storm",
  "visual_description": "...",
  "text_segment": "...",
  "narration": "...",
  "dialogues": [{"speaker": "Ari", "line": "..."}],
  "characters": ["Ari"],
  "locations": ["Hilltop"],
  "estimated_duration": 12
}
```

## Consistency Store

Character and location profiles are stored under `data/consistency/` and reused on subsequent runs to keep visuals stable.

## Troubleshooting

- **Missing API keys**: ensure `OPENROUTER_API_KEY` and `WANT2GP_API_KEY` are set.
- **FFmpeg not found**: install and ensure it is on your PATH.

## License

MIT License (see LICENSE file)
