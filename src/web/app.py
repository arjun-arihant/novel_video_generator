"""Streamlit web UI for novel video generation."""

import asyncio
import json
from pathlib import Path
from typing import List

import streamlit as st

from ..consistency.store import ConsistencyStore
from ..consistency.voice_assigner import assign_voice
from ..parser.openrouter_parser import SceneExtractor
from ..storage.epub_loader import extract_chapters
from ..tts.manager import TTSManager
from ..image.generator import ImageGenerator
from ..video.composer import VideoComposer
from ..common import ensure_output_dir

# Kokoro voice presets: (display_label, config_key)
VOICE_PRESETS = [
    ("❤️ Heart (Female, A-grade)", "narrator_female_1"),
    ("🔥 Bella (Female, intimate)", "narrator_female_2"),
    ("📚 Sarah (Female, educator)", "narrator_female_3"),
    ("🇬🇧 Emma (Female, British)", "narrator_female_4"),
    ("🌟 Nova (Female, natural)", "narrator_female_5"),
    ("🎙️ Michael (Male, warm)", "narrator_male_1"),
    ("⚡ Fenrir (Male, energetic)", "narrator_male_2"),
    ("🎮 Puck (Male, youthful)", "narrator_male_3"),
    ("📖 Fable (Male, storyteller)", "narrator_male_4"),
    ("🎩 George (Male, British)", "narrator_male_5"),
]


def _estimate_minutes(text: str, wpm: int = 180) -> float:
    words = len(text.split())
    return round(words / wpm, 2)


def main() -> None:
    st.set_page_config(page_title="Novel Video Generator", layout="wide")
    st.title("Novel Video Generator")

    if "chapters" not in st.session_state:
        st.session_state.chapters = []
    if "selected_chapters" not in st.session_state:
        st.session_state.selected_chapters = []
    if "scenes" not in st.session_state:
        st.session_state.scenes = []
    if "characters" not in st.session_state:
        st.session_state.characters = {}

    st.header("1. Upload EPUB")
    uploaded = st.file_uploader("Upload EPUB file", type=["epub"])
    if uploaded:
        temp_path = Path("data/uploads") / uploaded.name
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(uploaded.getbuffer())
        chapters = extract_chapters(temp_path)
        st.session_state.chapters = chapters
        st.success(f"Extracted {len(chapters)} chapter(s).")

    if st.session_state.chapters:
        st.header("2. Choose chapters")
        chapter_options = [f"Chapter {i + 1}" for i in range(len(st.session_state.chapters))]
        selected = st.multiselect("Select chapter(s)", chapter_options)
        st.session_state.selected_chapters = selected
        if selected:
            total_text = "\n".join(
                st.session_state.chapters[int(ch.split()[1]) - 1] for ch in selected
            )
            minutes = _estimate_minutes(total_text)
            st.info(f"Estimated narration length: {minutes} minutes (180 wpm).")

    if st.session_state.selected_chapters:
        st.header("3. Narrator voice")
        voice_labels = [label for label, _ in VOICE_PRESETS]
        choice_idx = st.selectbox(
            "Choose narrator voice",
            range(len(voice_labels)),
            format_func=lambda i: voice_labels[i],
        )
        narrator_key = VOICE_PRESETS[choice_idx][1]
        st.session_state.narrator_voice = narrator_key

        batch_mode = st.checkbox("Batch mode (skip scene review)", value=len(st.session_state.selected_chapters) > 1)
        st.session_state.batch_mode = batch_mode

        if st.button("Extract scenes"):
            extractor = SceneExtractor()
            selected_indices = [int(ch.split()[1]) - 1 for ch in st.session_state.selected_chapters]
            combined_text = "\n\n".join(st.session_state.chapters[i] for i in selected_indices)
            response = extractor.extract_scenes(combined_text)
            st.session_state.scenes = response.get("scenes", [])
            characters_list = response.get("characters", [])
            store = ConsistencyStore()
            store.upsert_characters(characters_list)
            st.session_state.characters = store.list_characters()
            st.success(f"Extracted {len(st.session_state.scenes)} scenes.")

    if st.session_state.scenes and not st.session_state.get("batch_mode"):
        st.header("4. Review scenes")
        edited_scenes: List[dict] = []
        for idx, scene in enumerate(st.session_state.scenes):
            st.subheader(f"Scene {idx + 1}: {scene.get('title', '')}")
            scene["visual_description"] = st.text_area(
                f"Visual description {idx + 1}",
                value=scene.get("visual_description", ""),
            )
            scene["narration"] = st.text_area(
                f"Narration {idx + 1}",
                value=scene.get("narration", scene.get("text_segment", "")),
            )
            dialogues = scene.get("dialogues", [])
            updated_dialogues = []
            if dialogues:
                st.markdown("**Dialogues**")
                for didx, dialogue in enumerate(dialogues):
                    speaker = st.text_input(
                        f"Speaker {idx + 1}.{didx + 1}",
                        value=dialogue.get("speaker", ""),
                    )
                    line = st.text_area(
                        f"Line {idx + 1}.{didx + 1}",
                        value=dialogue.get("line", ""),
                    )
                    updated_dialogues.append({"speaker": speaker, "line": line})
            scene["dialogues"] = updated_dialogues
            edited_scenes.append(scene)
        st.session_state.scenes = edited_scenes

    if st.session_state.scenes:
        st.header("5. Generate video")
        if st.button("Generate"):
            output_dir = Path("data/web_runs")
            ensure_output_dir(output_dir)

            store = ConsistencyStore()
            used: List[str] = []
            characters = assign_voice(store.list_characters(), used)
            tts_manager = TTSManager()
            for name, data in characters.items():
                tts_manager.register_character_voice(name, data.get("voice_preset", ""))
            tts_manager.register_character_voice("narrator", st.session_state.narrator_voice)

            images_dir = output_dir / "images"
            audio_dir = output_dir / "audio"
            scenes_path = output_dir / "scenes.json"
            with open(scenes_path, "w", encoding="utf-8") as f:
                json.dump(st.session_state.scenes, f, indent=2, ensure_ascii=False)

            st.info("Generating images via WanGP...")
            generator = ImageGenerator()
            for i, scene in enumerate(st.session_state.scenes):
                generator.generate(scene["visual_description"], images_dir / f"scene_{i:03d}.png")

            st.info("Generating audio via Kokoro TTS...")
            audio_dir.mkdir(parents=True, exist_ok=True)

            async def _generate_audio() -> None:
                await tts_manager.generate_batch_audio(
                    st.session_state.scenes,
                    audio_dir,
                    max_concurrent=3,
                    default_voice="narrator",
                )

            asyncio.run(_generate_audio())

            st.info("Composing final video...")
            composer = VideoComposer()
            composer.create_video(st.session_state.scenes, images_dir, audio_dir, output_dir / "output.mp4")
            st.success("Video generation complete.")


if __name__ == "__main__":
    main()
