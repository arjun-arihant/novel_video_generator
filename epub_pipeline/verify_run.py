"""Quick verification script — runs Stages 0-8 (no Wan2GP calls)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.ingestor import ingest
from pipeline.normalizer import normalize_all
from pipeline.extractor import extract_all_chapters
from pipeline.entity_resolver import resolve_entities
from pipeline.state_manager import update_state_for_chapter
from pipeline.validator import validate_all
from pipeline.prompt_builder import build_prompts_for_chapter
from pipeline.image_queue import build_image_queue
from pipeline.audio_queue import build_audio_queues
from config import novel_path

EPUB = str(Path(__file__).parent.parent / "I Have a Cultivation World.epub")
CHAPTER = 1

print("=" * 60)
print("EPUB Pipeline — Verification Run (Stages 0-8, no generation)")
print("=" * 60)

# Stage 0
print("\n[Stage 0] Ingesting EPUB...")
book_slug, _ = ingest(EPUB)
print(f"  Book slug: {book_slug}")

raw_path = novel_path(book_slug, "chapters", "raw", "raw_book.json")
raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
total = len(raw["chapters"])
print(f"  Total chapters: {total}")
for ch in raw["chapters"][:3]:
    wc = len(ch["raw_text"].split())
    title = ch["title"]
    cid = ch["chapter_id"]
    print(f"  Ch{cid}: {title!r} ({wc} words)")

# Stage 1
print("\n[Stage 1] Normalizing chapter 1...")
ch1_raw = next((c for c in raw["chapters"] if c["chapter_id"] == CHAPTER), None)
if not ch1_raw:
    print("  ERROR: Chapter 1 not found!")
    sys.exit(1)
# normalize_all expects a raw_book dict with a "chapters" key
normalize_all(book_slug, {"chapters": [ch1_raw]})
norm_path = novel_path(book_slug, "chapters", "normalized", f"normalized_ch{CHAPTER}.json")
norm = json.loads(Path(norm_path).read_text(encoding="utf-8"))
print(f"  Paragraphs: {len(norm['paragraphs'])}")

# Stage 2 — LLM call
print("\n[Stage 2] Extracting scenes via LLM (1 call)...")
# extract_all_chapters expects a list of normalized chapter dicts
extract_all_chapters(book_slug, [norm])
scenes_path = novel_path(book_slug, "chapters", "scenes", f"scenes_raw_ch{CHAPTER}.json")
scenes_raw = json.loads(Path(scenes_path).read_text(encoding="utf-8"))
n_scenes = len(scenes_raw.get("scenes", []))
print(f"  Scenes extracted: {n_scenes}")
for s in scenes_raw["scenes"]:
    loc = s.get("location_name", "?")
    mood = s.get("mood", "?")
    n_seq = len(s.get("sequence", []))
    print(f"    Scene {s['scene_id']}: {loc!r} | mood={mood} | {n_seq} sequence items")

# Stage 3 — LLM call
print("\n[Stage 3] Entity resolution (1 LLM call for whole book)...")
resolve_entities(book_slug, [CHAPTER])
char_map_path = novel_path(book_slug, "db", "character_canonical_map.json")
loc_map_path = novel_path(book_slug, "db", "location_canonical_map.json")
char_map = json.loads(Path(char_map_path).read_text(encoding="utf-8"))
loc_map = json.loads(Path(loc_map_path).read_text(encoding="utf-8"))
print(f"  Character canonical map: {len(char_map)} entries")
print(f"  Location canonical map: {len(loc_map)} entries")

# Stage 4 — LLM calls
print("\n[Stage 4] State manager (LLM Pass 2 + 3)...")
update_state_for_chapter(book_slug, CHAPTER)
char_db_path = novel_path(book_slug, "db", "character_db.json")
loc_db_path = novel_path(book_slug, "db", "location_db.json")
char_db = json.loads(Path(char_db_path).read_text(encoding="utf-8"))
loc_db = json.loads(Path(loc_db_path).read_text(encoding="utf-8"))
print(f"  Characters in DB: {len(char_db['characters'])}")
print(f"  Locations in DB: {len(loc_db['locations'])}")

# Stage 5
print("\n[Stage 5] Validation...")
validate_all(book_slug, [CHAPTER])

# Stage 6
print("\n[Stage 6] Building prompts...")
build_prompts_for_chapter(book_slug, CHAPTER)
prompts_path = novel_path(book_slug, "prompts", f"prompts_ch{CHAPTER}.json")
prompts = json.loads(Path(prompts_path).read_text(encoding="utf-8"))
print(f"  Scenes with prompts: {len(prompts['scenes'])}")

# Stage 7
print("\n[Stage 7] Building image queue...")
iq_path = build_image_queue(book_slug, CHAPTER)
iq = json.loads(Path(iq_path).read_text(encoding="utf-8"))
print(f"  Image queue tasks: {len(iq)}")
print(f"  First task output_filename: {iq[0]['params']['output_filename']}")

# Stage 8
print("\n[Stage 8] Building audio queues...")
pa, pb, pc = build_audio_queues(book_slug, CHAPTER)
qa = json.loads(Path(pa).read_text(encoding="utf-8"))
qb = json.loads(Path(pb).read_text(encoding="utf-8"))
qc = json.loads(Path(pc).read_text(encoding="utf-8"))
print(f"  Pass A (voice design): {len(qa)} tasks")
print(f"  Pass B (narrator/fallback): {len(qb)} tasks")
print(f"  Pass C (voice cloning): {len(qc)} tasks")

print("\n" + "=" * 60)
print("ALL STAGES 0-8 PASSED")
print(f"Novel folder: novels/{book_slug}/")
print("=" * 60)
