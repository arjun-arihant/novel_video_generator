# Novel Video Generator Blueprint

This document outlines the core architecture and data flow for rebuilding the Novel Video Generator application. The new architecture offloads heavy AI generation (Images, Audio, LLM) to external APIs, keeping only the orchestration and final video rendering (FFmpeg) local.

## 1. Core Pipeline Stages

The application pipeline consists of five distinct, sequential stages per chapter:

1. **Extraction (LLM API)**
   - **Input:** Raw chapter text (parsed from EPUB or provided directly).
   - **Action:** An LLM processes the text to identify characters, locations, and chronologically break the chapter down into visual "scenes".
   - **Output:** A structured `scenes.json` mapping out the sequence of events, dialogue, and visual descriptions.

2. **Image Generation (External API)**
   - **Input:** `visual_description` from each scene in `scenes.json`.
   - **Action:** Calls an external image generation API (e.g., Midjourney, DALL-E 3, Flux) to produce a static frame for the scene.
   - **Output:** Sequential image files (e.g., `scene_001.png`, `scene_002.png`).

3. **Audio Generation (External API)**
   - **Input:** Sequential `narration` and `dialogue` lines from each scene, along with character voice mappings.
   - **Action:** Calls an external Text-to-Speech API (e.g., ElevenLabs, OpenAI TTS). Handles distinct voices for the Narrator vs. specific Characters.
   - **Output:** Sequential audio files for each scene (e.g., `scene_001.wav`). *Note: Requires programmatic insertion of silence gaps between dialogue lines for pacing.*

4. **Stitching & Assembly (Local FFmpeg)**
   - **Input:** The generated `.png` and `.wav` files for each scene.
   - **Action:** A local FFmpeg subprocess dynamically merges the static image and its corresponding audio track into a scene-level video clip, then concatenates all clips together.
   - **Output:** The final chapter video (`chXXXX.mp4`).

---

## 2. Essential Data Structures

### The Scene Object (`scenes.json`)
The most critical data structure that drives the entire pipeline. Every chapter must be parsed into an array of these objects:

```json
{
  "id": 1,
  "title": "Scene Title",
  "visual_description": "Comprehensive physical description of the environment, characters, and action for the image generator prompt.",
  "characters": ["Character A", "Character B"],
  "sequence": [
    {
      "type": "narration",
      "text": "The wind howled through the valley.",
      "speaker": "narrator"
    },
    {
      "type": "dialogue",
      "text": "We must hurry!",
      "speaker": "Character A"
    }
  ]
}
```

### The Consistency Store (Optional but Recommended)
A lightweight local database (JSON) to track global entities across chapters to ensure continuity:
- **Characters:** Names, visual descriptions, assigned TTS voice IDs.
- **Locations:** Names, visual descriptions to keep environments consistent.

---

## 3. Directory Architecture

A clean, predictable file structure per novel is necessary for the modular pipeline to independently verify if a stage is complete.

```text
data/
└── {Novel_Name}/
    ├── novel_meta.json
    └── processing/
        └── {chapter_id}/
            ├── scenes.json       (Step 1 Output)
            ├── images/           (Step 2 Output)
            │   ├── scene_000.png
            │   └── ...
            ├── audio/            (Step 3 Output)
            │   ├── scene_000.wav
            │   └── ...
            └── {chapter_id}.mp4  (Step 4 Output)
```

## 4. Implementation Notes for the Rewrite

- **Idempotency:** The pipeline should check for the existence of files in the `processing/` directories before calling expensive external APIs. If `scene_001.png` exists, skip image generation for that scene.
- **FFmpeg Concat:** When concatenating mismatched audio or video, always use FFmpeg's `filter_complex` rather than a raw copy operation to avoid silent crashes due to conflicting sample rates.
- **UI Decoupling:** The UI should only poll the filesystem state (`.mp4` exists, `scenes.json` exists) rather than relying on deep, stateful websocket connections for progress.
