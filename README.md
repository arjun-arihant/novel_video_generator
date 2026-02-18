# Novel Video Generator

A Python pipeline + Web UI that converts novel chapters into narrated, illustrated videos.

## Pipeline

```
EPUB → Scene Extraction (OpenRouter LLM) → Images (WanGP CLI) → Audio (Kokoro TTS) → Video (FFmpeg)
```

## Project Structure

```
novel_video_generator/
├── cli.py                  # CLI entry point
├── configs/
│   └── voices.yaml         # Kokoro voice presets (10 voices)
├── data/
│   └── ihacw/              # Novel chapter data
├── src/
│   ├── common/             # Config, logging, retry, validation
│   ├── consistency/        # Character/location store + voice assignment
│   ├── image/              # WanGP CLI image generator
│   ├── llm/                # OpenRouter client
│   ├── parser/             # Scene extraction from text
│   ├── storage/            # EPUB loader
│   ├── tts/                # Kokoro TTS engine + manager
│   ├── video/              # FFmpeg video composer
│   └── web/                # Streamlit web UI
├── tests/                  # Test directory
├── z_image_settings.json   # WanGP Z-Image settings template
├── KOKORO_TTS_API_REFERENCE.md
├── Wan2GP_CLI_headless_procesing_instructions.md
├── requirements.txt
└── .env                    # Environment config (not committed)
```

## Prerequisites

| Dependency | Purpose | Install |
|-----------|---------|---------|
| Python 3.10+ | Runtime | [python.org](https://python.org) |
| OpenRouter API key | Scene extraction | [openrouter.ai](https://openrouter.ai) |
| WanGP | Image generation | [GitHub](https://github.com/deepbeepmeep/WanGP) (local install) |
| Kokoro TTS | Text-to-speech | [HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M) (local server) |
| FFmpeg | Video composition | [ffmpeg.org](https://ffmpeg.org/download.html) |
| Conda | WanGP environment | [conda.io](https://docs.conda.io/) |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Edit `.env` with your keys and paths:

```env
OPENROUTER_API_KEY=your_key_here
KOKORO_BASE_URL=http://localhost:8000
WANGP_PATH=D:\GeneAI\Wan2GP
```

### Start Services

**Kokoro TTS:**
```bash
# Start server, then verify:
curl http://localhost:8000/health
```

**WanGP:**
```bash
cd D:\GeneAI\Wan2GP
conda activate wan2gp
python wgp.py  # for web UI, or use --process for headless
```

## Usage

### Web UI
```bash
streamlit run -m src.web.app
```

1. Upload EPUB → select chapters → choose voice → review scenes → generate

### CLI
```bash
python cli.py pipeline chapter.json       # Full pipeline
python cli.py extract chapter.json        # Scene extraction only
python cli.py images scenes.json          # Image generation only
python cli.py audio scenes.json           # TTS only
python cli.py video scenes.json           # Video assembly only
```

## Voices

10 Kokoro voices available (5 female, 5 male):

| Key | Voice | Gender | Description |
|-----|-------|--------|-------------|
| narrator_female_1 | af_heart | F | ❤️ Warm, flagship (A grade) |
| narrator_female_2 | af_bella | F | 🔥 Intimate, husky |
| narrator_female_3 | af_sarah | F | 📚 Friendly educator |
| narrator_female_4 | bf_emma | F | 🇬🇧 British professional |
| narrator_female_5 | af_nova | F | 🌟 Natural, approachable |
| narrator_male_1 | am_michael | M | 🎙️ Warm narrator |
| narrator_male_2 | am_fenrir | M | ⚡ Energetic, clear |
| narrator_male_3 | am_puck | M | 🎮 Youthful, upbeat |
| narrator_male_4 | bm_fable | M | 📖 Refined storyteller |
| narrator_male_5 | bm_george | M | 🎩 British classic |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Kokoro not responding | Verify `curl http://localhost:8000/health` returns OK |
| WanGP not found | Set `WANGP_PATH` in `.env` to WanGP install directory |
| Missing API key | Set `OPENROUTER_API_KEY` in `.env` |
| FFmpeg not found | Install FFmpeg and add to PATH |

## License

MIT
