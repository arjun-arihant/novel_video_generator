# Implementation Plan: Novel Video Generator Overhaul

## Overview
This plan outlines the transition to Qwen3 TTS, improved context-aware image prompting, and a new "Pipeline View" for manual review and editing.

---

## Phase 1: Database & Schema
**Goal:** Enable persistent voice design for characters.

1.  **Update `ConsistencyStore` Schema**:
    *   Add `voice_design_params: Dict[str, Any]` to `_CHARACTER_SCHEMA`. This will store the output of the `voicedesign` process (weights, tags, etc.).
    *   Add `voice_is_designed: bool` flag to track if we need to run the design pass for this character.
2.  **Migration**:
    *   Update `upsert_characters` to preserve these new fields during chapter transitions.

---

## Phase 2: Prompt Engineering
**Goal:** Generate more descriptive, story-aware image prompts.

1.  **Context Injection**:
    *   Modify `OpenRouterParser.extract_scenes` to include a summary of the previous chapter/scene in the system prompt.
2.  **Visual Enrichment**:
    *   Update the Scene extraction schema to explicitly request:
        *   `atmospheric_lighting`: Description of light and shadow.
        *   `composition_notes`: Camera angle and framing (close-up, wide, etc.).
        *   `narrative_detail`: Small story-specific visual cues.
3.  **Output Format**:
    *   Refine the `visual_description` field to be a weighted prompt (e.g., "(detailed face:1.2), cinematic lighting,...").

---

## Phase 3: Qwen3 TTS Engine
**Goal:** Implement the "Batch-by-Model" optimization for Qwen3.

1.  **Refactor `TTSManager`**:
    *   Implement `generate_chapter_audio(scenes: List[Scene])`.
    *   **Pass 1: Narrator**:
        *   Extract all narrative segments.
        *   Load `qwen3_tts_customvoice`.
        *   Generate using `alt_prompt` derived from scene mood.
    *   **Pass 2: Design**:
        *   Identify characters with `voice_is_designed = False`.
        *   Load `qwen3_tts_voicedesign`.
        *   Generate voice samples and save parameters to `ConsistencyStore`.
    *   **Pass 3: Dialogue**:
        *   Load `qwen3_tts_base`.
        *   For each character, use their `voice_design_params` as the reference for cloning dialogue.
        *   Map `prosody` from scene text to the `alt_prompt` field.
2.  **CLI Wrapper**:
    *   Update `src/tts/provider.py` to interface with `wgp.py --process` using the JSON templates provided.

---

## Phase 4: Backend API
**Goal:** Support the Review/Edit workflow.

1.  **New Endpoints**:
    *   `POST /api/scenes/<id>/regenerate-image`: Async trigger for image generation for a specific scene.
    *   `POST /api/scenes/<id>/regenerate-audio`: Async trigger for TTS for a specific segment.
    *   `PUT /api/scenes/<id>`: Update scene text/prompts manually.
2.  **Pipeline State Tracking**:
    *   Add a `status` field to scenes (Pending, Review, Generated).

---

## Phase 5: Frontend Overhaul
**Goal:** Provide a "Pipeline View" and integrated player.

1.  **Pipeline Review Tab**:
    *   Display a vertical timeline of scenes.
    *   Each scene shows:
        *   Generated Image (with click-to-enlarge).
        *   Editable Visual Prompt.
        *   Editable Dialog/Narrative text.
        *   "Regenerate" buttons for visual/audio.
2.  **Video Player**:
    *   Add an `<audio>` preview for individual scenes.
    *   Add a final `<video>` player in the "Generation" tab that points to the latest `/output/final.mp4`.

---

## Phase 6: Verification
**Goal:** Ensure quality and performance.

1.  **Voice Consistency Test**: Generate two chapters featuring the same character and verify the voice signature remains identical.
2.  **Prompt Quality Check**: Compare old vs. new visual prompts for descriptiveness.
3.  **Model Loading Benchmark**: Verify that the 3-pass batch approach is faster than the scene-by-scene approach (fewer model swaps).
