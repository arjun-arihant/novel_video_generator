# Novel Video Generator

A Python pipeline + Web UI that converts novel chapters into narrated, illustrated videos using state-of-the-art AI.

## Pipeline

```
EPUB/Text → Scene Extraction (OpenRouter LLM) → Images (WanGP/Qwen3) → Audio (Qwen3 TTS) → Video (FFmpeg)
```

## Features

- **3-Pass TTS:** Optimized batch processing for Narrator, Voice Design, and Dialogue.
- **Voice Cloning:** Characters use consistent voices derived from descriptions (Qwen3).
- **Interactive UI:** Review & Edit scenes, regenerate specific assets, and manage consistency.
- **Batch Processing:** Efficient image and audio generation using WanGP's internal batching.

## Prerequisites

| Dependency | Purpose | Details |
|-----------|---------|---------|
| Python 3.10+ | Runtime | [python.org](https://python.org) |
| Conda | Environment | [conda.io](https://docs.conda.io/) |
| WanGP | Image/TTS | [GitHub](https://github.com/deepbeepmeep/WanGP) (Installed in `D:\GeneAI\Wan2GP`) |
| OpenRouter | LLM | API Key required |
| FFmpeg | Video | Added to PATH |

## Setup

1. **Python Environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Conda Environment (for WanGP):**
   Ensure `wan2gp` conda environment is created and WanGP is installed at `WANGP_PATH`.

3. **Configuration:**
   Create `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-...
   WANGP_PATH=D:\GeneAI\Wan2GP
   ```

## Usage

### 🚀 Web Interface (Recommended)
Launch the server:
```bash
python -m src.web.web_server
```
Open [http://localhost:5000](http://localhost:5000)

**Workflow:**
1. **Pipeline Tab:** Upload Chapter or enter text.
2. **Extract:** Parse scenes and characters.
3. **Scenes Tab:** Review generated scenes.
   - *Edit* text/dialogue.
   - *Regenerate* specific images or audio if needed.
4. **Generate:** Run full pipeline to create video.

### 💻 CLI
```bash
# Full Pipeline
python cli.py pipeline chapter.json --output data/runs/001

# Step-by-Step
python cli.py extract chapter.json
python cli.py images scenes.json
python cli.py audio scenes.json  # Uses Qwen3 via WanGP
python cli.py video scenes.json
```

## Verification

To verify the installation and pipeline:
```bash
python tests/verify_pipeline.py
```

## Project Structure
- `src/web/`: Flask backend + Static frontend
- `src/tts/`: Qwen3 integration (Wrappers around WanGP)
- `src/consistency/`: Character & Location store
- `src/image/`: WanGP image generation
- `cli.py`: Command-line entry point

## License
MIT
