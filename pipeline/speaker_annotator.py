"""
Stages 5-6: Speaker Annotator + Script Reviewer (LLM Passes 2-3)
Uses Alexandria's generate_script.py and review_script.py to annotate scenes
with speaker labels, TTS instruct directions, and then review/fix the annotations.
"""
import json
import logging
import sys
from pathlib import Path

from pipeline.config import novel_path, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

# Ensure app/ is importable
_app_dir = str(Path(__file__).parent.parent / "app")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)


def _get_chapter_text(book_slug: str, chapter_id: int) -> str:
    """Get normalized chapter text directly (Alexandria approach).

    Reads the normalized chapter text instead of flattening scene sequences.
    This avoids the lossy round-trip through scene extraction and preserves
    the original text ordering and paragraph structure.
    """
    norm_path = Path(novel_path(
        book_slug, "chapters", "normalized", f"chapter_{chapter_id}.json"
    ))
    if not norm_path.exists():
        raise FileNotFoundError(f"No normalized text for ch{chapter_id}")

    data = json.loads(norm_path.read_text(encoding="utf-8"))
    return data.get("text", "")


def annotate_speakers(book_slug: str, chapter_id: int) -> list[dict]:
    """
    Stage 5: Speaker Annotation (LLM Pass 2).
    Takes scene text and produces Alexandria-format annotated script entries.

    Returns list of {speaker, text, instruct} dicts.
    """
    out_path = Path(novel_path(
        book_slug, "chapters", "scenes", f"annotated_script_ch{chapter_id}.json"
    ))
    if out_path.exists():
        logger.debug(f"Stage 5 — annotated_script_ch{chapter_id}.json exists, skipping.")
        return json.loads(out_path.read_text(encoding="utf-8"))

    scene_text = _get_chapter_text(book_slug, chapter_id)

    if not scene_text.strip():
        logger.warning(f"Stage 5 — No text for ch{chapter_id}, skipping annotation.")
        return []

    from generate_script import process_chunk, split_into_chunks
    from default_prompts import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
    from openai import OpenAI

    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

    # Split into manageable chunks for the LLM
    text_chunks = split_into_chunks(scene_text, max_size=3000)
    all_entries = []
    previous_entries = None

    for i, chunk_text in enumerate(text_chunks, 1):
        logger.info(
            f"Stage 5 — Annotating ch{chapter_id} chunk {i}/{len(text_chunks)}"
        )
        entries = process_chunk(
            client=client,
            model_name=LLM_MODEL,
            chunk=chunk_text,
            chunk_num=i,
            total_chunks=len(text_chunks),
            previous_entries=previous_entries,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=DEFAULT_USER_PROMPT,
            max_tokens=4096,
            temperature=0.6,
        )
        if entries:
            all_entries.extend(entries)
            # Keep last 3 entries as context for next chunk
            previous_entries = entries[-3:] if len(entries) >= 3 else entries

    # Save the annotated script
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(all_entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        f"Stage 5 — Annotated ch{chapter_id}: {len(all_entries)} entries."
    )
    return all_entries


def review_script(book_slug: str, chapter_id: int) -> list[dict]:
    """
    Stage 6: Script Review (LLM Pass 3).
    Uses Alexandria's review_batch to fix common annotation errors.

    Returns the reviewed/fixed script entries.
    """
    reviewed_path = Path(novel_path(
        book_slug, "chapters", "scenes", f"reviewed_script_ch{chapter_id}.json"
    ))
    if reviewed_path.exists():
        logger.debug(f"Stage 6 — reviewed_script_ch{chapter_id}.json exists, skipping.")
        return json.loads(reviewed_path.read_text(encoding="utf-8"))

    annotated_path = Path(novel_path(
        book_slug, "chapters", "scenes", f"annotated_script_ch{chapter_id}.json"
    ))
    if not annotated_path.exists():
        logger.error(f"Stage 6 — No annotated script for ch{chapter_id}.")
        return []

    script = json.loads(annotated_path.read_text(encoding="utf-8"))
    if not script:
        return []

    from review_script import review_batch, merge_consecutive_narrators, check_text_loss
    from review_prompts import REVIEW_SYSTEM_PROMPT, REVIEW_USER_PROMPT
    from openai import OpenAI

    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

    logger.info(f"Stage 6 — Reviewing script for ch{chapter_id} ({len(script)} entries)")

    # Process in batches of 25 (matching Alexandria's default)
    batch_size = 25
    batches = [script[i:i + batch_size] for i in range(0, len(script), batch_size)]
    all_reviewed = []
    previous_tail = None

    for i, batch in enumerate(batches, 1):
        logger.info(f"Stage 6 — Review batch {i}/{len(batches)} ({len(batch)} entries)")

        corrected = review_batch(
            client=client,
            model_name=LLM_MODEL,
            batch_entries=batch,
            batch_num=i,
            total_batches=len(batches),
            previous_tail=previous_tail,
            system_prompt=REVIEW_SYSTEM_PROMPT,
            user_prompt_template=REVIEW_USER_PROMPT,
            max_tokens=8000,
            temperature=0.4,
        )

        if corrected is None:
            logger.warning(f"Stage 6 — Review batch {i} failed, keeping original entries.")
            all_reviewed.extend(batch)
        else:
            # Flatten if review_batch returned nested lists
            if corrected and isinstance(corrected[0], list):
                corrected = [e for sublist in corrected for e in sublist]

            # Text-loss safety check
            passed, _, _, ratio = check_text_loss(batch, corrected)
            if not passed:
                logger.warning(
                    f"Stage 6 — Text loss detected in batch {i} (ratio: {ratio:.2f}). "
                    f"Keeping original entries."
                )
                all_reviewed.extend(batch)
            else:
                all_reviewed.extend(corrected)

        previous_tail = (all_reviewed[-2:] if len(all_reviewed) >= 2
                         else all_reviewed)

    # Merge consecutive narrators for cleaner output
    # merge_consecutive_narrators returns (merged_list, merge_count)
    merge_result = merge_consecutive_narrators(all_reviewed)
    if isinstance(merge_result, tuple):
        reviewed, merge_count = merge_result
    else:
        reviewed = merge_result

    reviewed_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed_path.write_text(
        json.dumps(reviewed, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        f"Stage 6 — Reviewed ch{chapter_id}: {len(reviewed)} entries "
        f"(was {len(script)})."
    )
    return reviewed
