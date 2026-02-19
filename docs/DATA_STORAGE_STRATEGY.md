# Data storage and extraction strategy

## Goals
- Create one isolated workspace per uploaded novel.
- Keep chapter extraction, scenes, character DB, images, audio, and final videos grouped by novel and chapter.
- Use deterministic file names so UI and APIs can discover assets reliably.

## Canonical folder layout

```text
data/
  YOUR_DATA_IS_STORED_HERE.txt
  novels/
    {novel_id}_{safe_title}/
      metadata.json
      source/
        original.epub
      chapters/
        ch001.json
        ch002.json
      processing/
        ch001/
          extraction/
            scenes.json
            extraction_meta.json
          consistency/
            characters.json
            locations.json
          assets/
            images/
              scene_000.png
            audio/
              scene_000.wav
            voice_samples/
              char_{character_slug}_preview.wav
          video/
            ch001_final.mp4
          logs/
            pipeline.log
      exports/
        ch001_package/
```

## Naming conventions
- Novel folder: `{8-char-id}_{safe_title}`
- Chapter file: `ch{NNN}.json`
- Scene assets: `scene_{index:03d}.{ext}`
- Character voice preview: `char_{character_slug}_preview.wav`
- Final video: `ch{NNN}_final.mp4`

## Interface flow
1. Upload EPUB to library.
2. Backend ingests EPUB, creates novel folder, and writes chapter JSON files.
3. UI lists chapters and asks which chapter to work on.
4. Selecting chapter triggers scene extraction and updates chapter-local consistency DB.
5. Vision tab shows scenes and allows:
   - per-scene image generation
   - generate all images
   - prompt edits and regeneration
6. Voice tab shows character voices with short previews (target: ~10s) and supports critique/regeneration.
7. Final tab runs audio + compose to produce chapter final video.

## Git strategy
- The repository tracks only `data/` folder placeholder.
- Runtime content under `data/` is ignored by git.
