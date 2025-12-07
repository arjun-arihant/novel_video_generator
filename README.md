# Novel Video Generator

A Python pipeline that converts novel chapters (text) into animated videos with narration.

## Features

- **Scene Extraction**: Uses **Gemini 2.5 Flash** to analyze text and extract visual scenes.
- **Image Generation**: Uses **Pollinations.ai Flux models** to generate high-quality images.
- **Style**: Enforces a **Chinese Manhua/Webtoon** aesthetic.
- **Narration**: Uses **Gemini 2.5 Flash Preview TTS** for high-quality audio.
- **Animation**: Applies **Ken Burns effect** (Pan/Zoom) to static images.
- **Video Assembly**: Combines images, audio, and effects into a final `.mp4`.

## Prerequisites

- Python 3.10+
- **Gemini API Key** (for text processing, image generation, and TTS)
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
    ```

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

- **Voices**: Edit `configs/voices.yaml` to change voice assignments for different characters.

---

## Project Structure

### Directory Overview

```
novel_video_generator/
├── src/                    # Source code modules
│   ├── parser/            # Scene extraction from text
│   ├── image/             # Image generation
│   ├── tts/               # Text-to-speech engine
│   ├── video/             # Video assembly
│   └── epub/              # EPUB processing utilities
├── scripts/               # Executable scripts for pipeline stages
├── configs/               # Configuration files (voices, settings)
├── data/                  # Input data and outputs
│   ├── ihacw/            # Novel source data
│   │   ├── chapters/     # Processed chapter JSON files
│   │   ├── character_db/ # Character information
│   │   └── raw_epubs/    # Original EPUB files
│   ├── scenes/           # Extracted scene JSON files
│   ├── images/           # Generated images (organized by chapter)
│   ├── audio/            # Generated audio files (organized by chapter)
│   └── videos/           # Final output videos
├── outputs/              # Alternative output directory
├── notebooks/            # Jupyter notebooks for interactive testing
└── requirements.txt      # Python dependencies
```

---

### Source Modules (`src/`)

#### 1. **Parser Module** (`src/parser/`)
- **File**: `gemini_parser.py`
- **Class**: `SceneExtractor`
- **Purpose**: Analyzes chapter text using Gemini 2.5 Flash and breaks it into 3-6 visual scenes
- **Input**: Raw chapter text (string)
- **Output**: List of scene dictionaries with:
  - `visual_description`: Natural language prompt for image generation
  - `text_segment`: The narration text for this scene
  - `characters`: List of characters present
  - `estimated_duration`: Scene duration in seconds
- **Used by**: `run_scene_extraction.py`, `run_pipeline.py`

#### 2. **Image Module** (`src/image/`)
- **File**: `generator.py`
- **Class**: `ImageGenerator`
- **Purpose**: Generates images from text prompts using Pollinations.ai Flux models
- **Model Used**: `flux-anime` (for Manhua/webtoon style)
- **Features**:
  - Natural language prompts (no tag soup)
  - Automatic style enhancement (adds "Chinese manhua webtoon style, cinematic lighting")
  - Aspect ratio support (landscape: 1280x720, portrait: 768x1152)
  - Retry logic with exponential backoff
- **Input**: Text prompt, output path, aspect ratio
- **Output**: PNG image file
- **Used by**: `run_image_generation.py`, `run_pipeline.py`

#### 3. **TTS Module** (`src/tts/`)
- **Files**:
  - `base.py`: Abstract base classes (`TTSProvider`, `VoiceConfig`)
  - `gemini_engine.py`: Gemini TTS implementation using `gemini-2.5-flash-preview-tts`
  - `manager.py`: TTS manager that loads voice configs and initializes provider
- **Class**: `GeminiTTSProvider`
- **Purpose**: Converts text to speech audio files
- **Voice Support**: Multiple Gemini voices (Puck, Charon, Kore, Fenrir, Aoede)
- **Input**: Text, output path, voice config
- **Output**: MP3 audio file
- **Used by**: `run_tts.py`, `run_pipeline.py`

#### 4. **Video Module** (`src/video/`)
- **File**: `composer.py`
- **Class**: `VideoComposer`
- **Purpose**: Assembles final video from scenes, images, and audio
- **Features**:
  - Ken Burns effect (zoom/pan on static images)
  - Syncs audio duration with image display
  - Concatenates all scenes into final video
  - Output: 1920x1080, 24fps, H.264 codec
- **Input**: Scenes JSON, audio directory, image directory
- **Output**: MP4 video file
- **Used by**: `run_video_build.py`, `run_pipeline.py`

#### 5. **EPUB Module** (`src/epub/`)
- **File**: `epub_cleaner.py`
- **Purpose**: Utilities to extract and clean text from EPUB files
- **Used by**: Data preprocessing scripts (not in main pipeline)

---

### Scripts (`scripts/`)

#### **Main Pipeline Script**

**`run_pipeline.py`** - End-to-end automation
```
Input: Chapter JSON file (--chapter)
Output: Final video in data/videos/

Pipeline Flow:
1. Load chapter → Extract scenes (SceneExtractor)
2. Generate images for each scene (ImageGenerator)
3. Generate audio for each scene (TTSManager)
4. Assemble video (VideoComposer)
```

**Usage**:
```powershell
python scripts/run_pipeline.py --chapter data/ihacw/chapters/ihacw_ch0001.json --out data
```

---

#### **Individual Stage Scripts**

These scripts allow you to run each stage independently:

**`run_scene_extraction.py`**
- **Input**: Chapter JSON (`--chapter`)
- **Output**: Scenes JSON in `data/scenes/scenes_{chapter_id}.json`
- **Module Used**: `src.parser.gemini_parser.SceneExtractor`
- **Process**: Reads chapter text → Calls Gemini API → Saves scene data

**Usage**:
```powershell
python scripts/run_scene_extraction.py --chapter data/ihacw/chapters/ihacw_ch0001.json --out data/scenes
```

---

**`run_image_generation.py`**
- **Input**: Scenes JSON (`--scenes`)
- **Output**: PNG images in `data/images/chapter_{id}/scene_000.png`
- **Module Used**: `src.image.generator.ImageGenerator`
- **Process**: Reads scenes → Extracts `visual_description` → Calls Pollinations.ai → Saves images

**Usage**:
```powershell
python scripts/run_image_generation.py --scenes data/scenes/scenes_1.json --out data/images --aspect landscape
```

---

**`run_tts.py`**
- **Input**: Chapter JSON or Scenes JSON (`--chapter`)
- **Output**: MP3 audio files in `data/audio/chapter_{id}/scene_000.mp3`
- **Module Used**: `src.tts.manager.TTSManager`, `src.tts.gemini_engine.GeminiTTSProvider`
- **Process**: Reads text segments → Calls Gemini TTS → Saves audio files

**Usage**:
```powershell
python scripts/run_tts.py --chapter data/ihacw/chapters/ihacw_ch0001.json --out data/audio --provider gemini
```

---

**`run_video_build.py`**
- **Input**: Scenes JSON (`--scenes`), Audio directory (`--audio`), Images directory (`--images`)
- **Output**: MP4 video in `outputs/video_{chapter_id}.mp4`
- **Module Used**: `src.video.composer.VideoComposer`
- **Process**: Loads scenes + images + audio → Applies Ken Burns effect → Concatenates → Exports video

**Usage**:
```powershell
python scripts/run_video_build.py --scenes data/scenes/scenes_1.json --audio data/audio/chapter_1 --images data/images/chapter_1 --out outputs
```

---

### Data Flow Diagram

```
┌─────────────────────┐
│  Chapter JSON       │  (data/ihacw/chapters/ihacw_ch0001.json)
│  {id, paragraphs[]} │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ STEP 1:      │
    │ Scene        │  (run_scene_extraction.py)
    │ Extraction   │   Uses: SceneExtractor (Gemini 2.5 Flash)
    └──────┬───────┘
           │
           ▼
┌──────────────────────────┐
│ Scenes JSON              │  (data/scenes/scenes_1.json)
│ [{visual_description,    │
│   text_segment,          │
│   characters,            │
│   estimated_duration}]   │
└────┬─────────────────┬───┘
     │                 │
     │                 │
     ▼                 ▼
┌─────────────┐  ┌─────────────┐
│ STEP 2:     │  │ STEP 3:     │
│ Image Gen   │  │ TTS Gen     │  (run_image_generation.py)  (run_tts.py)
│             │  │             │   Uses: ImageGenerator       Uses: TTSManager
└──────┬──────┘  └──────┬──────┘         (Pollinations.ai)         (Gemini TTS)
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────┐
│ Images/     │  │ Audio/      │  (data/images/chapter_1/)  (data/audio/chapter_1/)
│ scene_*.png │  │ scene_*.mp3 │
└──────┬──────┘  └──────┬──────┘
       │                │
       └────────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ STEP 4:      │
         │ Video        │  (run_video_build.py)
         │ Assembly     │   Uses: VideoComposer (MoviePy)
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ Final Video  │  (data/videos/video_1.mp4)
         │ video_*.mp4  │
         └──────────────┘
```

---

### Configuration Files

#### `configs/voices.yaml`
Defines voice assignments for different characters/narrators:
```yaml
voices:
  narrator:
    name: "Puck"          # Gemini voice name
    provider: "gemini"
    rate: 1.0            # Speech rate multiplier
    pitch: 0.0           # Pitch adjustment
```

**Available Gemini Voices**: Puck, Charon, Kore, Fenrir, Aoede

---

### How Components Connect

**Dependencies Between Modules**:
```
run_pipeline.py
├── src.parser.gemini_parser (SceneExtractor)
├── src.image.generator (ImageGenerator)
├── src.tts.manager (TTSManager)
│   └── src.tts.gemini_engine (GeminiTTSProvider)
│       └── src.tts.base (VoiceConfig, TTSProvider)
└── src.video.composer (VideoComposer)

run_scene_extraction.py
└── src.parser.gemini_parser (SceneExtractor)

run_image_generation.py
└── src.image.generator (ImageGenerator)

run_tts.py
└── src.tts.manager (TTSManager)
    └── src.tts.gemini_engine (GeminiTTSProvider)

run_video_build.py
└── src.video.composer (VideoComposer)
```

---

### Technology Stack by Component

| Component          | Technology                          | API/Service          |
|--------------------|-------------------------------------|----------------------|
| Scene Extraction   | `google-generativeai` (Gemini SDK) | Gemini 2.5 Flash     |
| Image Generation   | `requests` HTTP client              | Pollinations.ai      |
| Text-to-Speech     | `google-generativeai` (Gemini SDK) | Gemini TTS Preview   |
| Video Assembly     | `moviepy`                           | Local processing     |

---

### Running the Full Pipeline

**Option 1: Run everything at once**
```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe scripts/run_pipeline.py --chapter data/ihacw/chapters/ihacw_ch0001.json
```

**Option 2: Run stages individually**
```powershell
# Step 1: Extract scenes
python scripts/run_scene_extraction.py --chapter data/ihacw/chapters/ihacw_ch0001.json

# Step 2: Generate images
python scripts/run_image_generation.py --scenes data/scenes/scenes_1.json

# Step 3: Generate audio (uses scenes for text_segment)
python scripts/run_tts.py --chapter data/ihacw/chapters/ihacw_ch0001.json

# Step 4: Assemble video
python scripts/run_video_build.py --scenes data/scenes/scenes_1.json --audio data/audio/chapter_1 --images data/images/chapter_1
```