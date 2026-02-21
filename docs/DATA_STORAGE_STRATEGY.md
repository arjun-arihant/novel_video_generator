# Data Storage Strategy

## Overview

Novel Video Generator uses a novel-centric data storage approach where each novel has its own isolated directory containing all associated data. This ensures clean separation between different novels and their characters/locations.

## Goals
- Create one isolated workspace per uploaded novel
- Keep chapter extraction, scenes, character DB, images, audio, and final videos grouped by novel and chapter
- Use deterministic file names so UI and APIs can discover assets reliably
- Each novel has its own consistency data (characters, locations) - no cross-novel contamination

## Canonical Folder Layout

```text
data/
├── .gitkeep
├── uploads/                      # Temporary file uploads
│   └── .gitkeep
│
├── {Novel_Title}/                # Novel folder (name only, no ID prefix)
│   ├── metadata.json             # Novel metadata (title, author, etc.)
│   ├── source/
│   │   └── original.epub         # Original uploaded EPUB
│   │
│   ├── chapters/                 # Extracted chapter content
│   │   ├── ch001.json
│   │   ├── ch002.json
│   │   └── ...
│   │
│   ├── consistency/              # Novel-specific consistency data
│   │   ├── characters.json       # Characters in this novel
│   │   └── locations.json        # Locations in this novel
│   │
│   ├── processing/               # Per-chapter processing outputs
│   │   └── ch001/
│   │       ├── extraction/
│   │       │   ├── scenes.json
│   │       │   └── extraction_meta.json
│   │       ├── assets/
│   │       │   ├── images/
│   │       │   │   └── scene_000.png
│   │       │   ├── audio/
│   │       │   │   └── scene_000.wav
│   │       │   └── voice_samples/
│   │       │       └── char_{character_slug}_preview.wav
│   │       ├── video/
│   │       │   └── ch001_final.mp4
│   │       └── logs/
│   │           └── pipeline.log
│   │
│   └── exports/                  # Final exported packages
│       └── ch001_package/
│
└── {Another_Novel_Title}/        # Second novel
    └── ... (same structure)
```

## Naming Conventions

| Item | Format | Example |
|------|--------|---------|
| Novel folder | `{safe_title}` | `I_Have_a_Cultivation_World` |
| Chapter file | `ch{NNN}.json` | `ch001.json`, `ch050.json` |
| Scene assets | `scene_{index:03d}.{ext}` | `scene_000.png`, `scene_001.wav` |
| Character voice preview | `char_{character_slug}_preview.wav` | `char_chen_mobei_preview.wav` |
| Final video | `ch{NNN}_final.mp4` | `ch001_final.mp4` |

## Novel Identification

Novels are identified by their **title** (sanitized for filesystem safety):
- No UUID prefixes - just the novel name
- Titles are sanitized: alphanumeric + underscore only
- Case-insensitive lookup supported

## Metadata Structure

```json
{
  "title": "I Have a Cultivation World",
  "author": "Author Name",
  "created_at": "2026-02-19T12:00:00",
  "updated_at": "2026-02-19T12:00:00",
  "chapter_count": 150,
  "directory": "data/I_Have_a_Cultivation_World",
  "source_epub": "data/I_Have_a_Cultivation_World/source/original.epub"
}
```

## API Routes

### Library Management
```
GET    /api/library                      # List all novels
POST   /api/library/upload               # Upload new EPUB
GET    /api/library/{novel_title}        # Get novel metadata
DELETE /api/library/{novel_title}        # Delete novel
PUT    /api/library/{novel_title}/title  # Update novel title
GET    /api/library/{novel_title}/chapters           # List chapters
GET    /api/library/{novel_title}/chapters/{ch_id}   # Get chapter content
```

### Consistency Data (Novel-Specific)
```
GET    /api/novels/{novel_title}/characters           # Get characters
PUT    /api/novels/{novel_title}/characters/{name}    # Update character
GET    /api/novels/{novel_title}/locations            # Get locations
```

### Pipeline Operations
```
POST   /api/extract                      # Extract scenes (requires novel_title)
POST   /api/pipeline                     # Run full pipeline (requires novel_title)
```

## Interface Flow

1. **Upload EPUB** to library via web UI or API
2. Backend ingests EPUB, creates novel folder structure, writes chapter JSON files
3. UI lists novels and their chapters
4. Selecting chapter triggers scene extraction (updates novel-local consistency DB)
5. Vision tab shows scenes and allows:
   - Per-scene image generation
   - Generate all images
   - Prompt edits and regeneration
6. Voice tab shows character voices with previews (~10s) and supports regeneration
7. Final tab runs audio + compose to produce chapter final video

## Git Strategy

- The repository tracks only placeholder files (`.gitkeep`)
- All runtime content under `data/` is ignored by git via `.gitignore`:
  ```
  data/*
  !data/.gitkeep
  !data/uploads/.gitkeep
  ```

## Migration Notes

### From Previous Structure

If migrating from the old structure with `data/novels/{id}_{title}/`:

1. Move novel folders from `data/novels/` to `data/`
2. Remove ID prefix from folder names
3. Create `consistency/` folder in each novel directory
4. Move `data/consistency/characters.json` and `locations.json` to novel-specific folders
5. Update metadata.json to remove `id` field

## Key Differences from Previous Version

| Aspect | Before | After |
|--------|--------|-------|
| Novel folder | `data/novels/{id}_{title}/` | `data/{title}/` |
| Identification | UUID-based `novel_id` | Title-based |
| Consistency | Global `data/consistency/` | Per-novel `consistency/` |
| API routes | `/api/library/{novel_id}` | `/api/library/{novel_title}` |
