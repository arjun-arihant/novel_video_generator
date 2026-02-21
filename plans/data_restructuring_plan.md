# Data Restructuring Plan

## Overview

This plan outlines the restructuring of the `data/` folder to simplify novel management. The key changes are:
1. Remove the intermediate `novels/` subfolder - novels go directly under `data/`
2. Remove ID prefixes from folder names - use novel title only
3. Move consistency data (characters, locations) into each novel's folder
4. Clean up all existing data for fresh start

## Current vs Proposed Structure

### Current Structure
```
data/
├── consistency/                    # Global (problematic for multiple novels)
│   ├── characters.json
│   └── locations.json
├── novels/                         # Intermediate folder
│   └── 7b1fe5d4_I_Have_a_Cultivation_World/  # ID prefix
│       ├── metadata.json
│       ├── source/
│       ├── chapters/
│       └── processing/
├── uploads/
└── web_runs/
```

### Proposed Structure
```
data/
├── .gitkeep                        # Keep folder tracked in git
├── uploads/                        # Temporary file uploads
│   └── .gitkeep
│
├── I_Have_a_Cultivation_World/     # Novel folder (name only, no ID)
│   ├── metadata.json               # Novel metadata (title, author, etc.)
│   ├── source/
│   │   └── original.epub           # Original uploaded EPUB
│   │
│   ├── chapters/                   # Extracted chapter content
│   │   ├── ch001.json
│   │   ├── ch002.json
│   │   └── ...
│   │
│   ├── consistency/                # Novel-specific consistency data
│   │   ├── characters.json         # Characters in this novel
│   │   └── locations.json          # Locations in this novel
│   │
│   ├── processing/                 # Per-chapter processing outputs
│   │   └── ch001/
│   │       ├── extraction/
│   │       │   ├── scenes.json
│   │       │   └── extraction_meta.json
│   │       ├── assets/
│   │       │   ├── images/
│   │       │   ├── audio/
│   │       │   └── voice_samples/
│   │       ├── video/
│   │       │   └── ch001_final.mp4
│   │       └── logs/
│   │           └── pipeline.log
│   │
│   └── exports/                    # Final exported packages
│       └── ch001_package/
│
└── Another_Novel_Title/            # Second novel
    └── ... (same structure)
```

## Key Design Decisions

### 1. Novel Folder Naming
- **Before**: `{uuid8}_{safe_title}` (e.g., `7b1fe5d4_I_Have_a_Cultivation_World`)
- **After**: `{safe_title}` only (e.g., `I_Have_a_Cultivation_World`)
- **Rationale**: Simpler, more intuitive. Novel titles are expected to be unique.

### 2. Consistency Data Scope
- **Before**: Global `data/consistency/` shared across all novels
- **After**: Each novel has `consistency/` subfolder
- **Rationale**: Different novels have different characters and locations. No cross-contamination.

### 3. Novel Identification
- **Before**: UUID-based `novel_id` field in metadata
- **After**: Use `title` (sanitized) as the identifier
- **Impact**: API routes change from `/api/novels/{id}` to `/api/novels/{title}`

### 4. Metadata Structure
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

## Code Changes Required

### 1. `src/core/library_manager.py`
**Changes:**
- Remove `NOVELS_DIR = DATA_DIR / "novels"` → use `DATA_DIR` directly
- Change folder creation from `{novel_id}_{safe_title}` to `{safe_title}`
- Remove `novel_id` field from metadata (use title as identifier)
- Update `get_novel()` to find by title instead of ID
- Add `consistency/` folder creation in `create_novel_from_epub()`
- Update `get_library()` to scan `DATA_DIR` directly

### 2. `src/consistency/store.py`
**Changes:**
- Remove default `base_dir = Path("data/consistency")`
- Make `base_dir` a required parameter
- Update initialization to work with novel-specific paths

### 3. `src/web/web_server.py`
**Changes:**
- Update routes that use `novel_id` to use `novel_title` or `novel_name`
- Initialize `ConsistencyStore` with novel-specific path
- Update API responses to use title-based identification

### 4. `docs/DATA_STORAGE_STRATEGY.md`
**Changes:**
- Update documentation to reflect new structure
- Remove references to `novels/` subfolder
- Update naming conventions section

### 5. `cli.py`
**Changes:**
- Update any ID-based novel references to use title
- Update help text and argument names

## API Changes

### Before
```
GET  /api/library                    # List all novels
GET  /api/novels/{novel_id}          # Get novel metadata
GET  /api/novels/{novel_id}/chapters # List chapters
```

### After
```
GET  /api/library                    # List all novels
GET  /api/novels/{novel_title}       # Get novel metadata (title-based)
GET  /api/novels/{novel_title}/chapters # List chapters
```

## Migration Strategy

Since user wants to re-upload novels, no migration is needed. We will:

1. **Delete all existing data** in `data/` folder
2. **Create empty structure** with `.gitkeep` files
3. **Update code** to use new structure
4. **Test** by uploading a novel through the web UI

## Files to Delete

```
data/
├── consistency/              # DELETE (moving to novel-specific)
│   ├── characters.json
│   └── locations.json
├── novels/                   # DELETE entire folder
│   └── 7b1fe5d4_.../
├── uploads/                  # KEEP (empty)
└── web_runs/                 # KEEP (empty) or DELETE based on usage
```

## Implementation Steps

### Phase 1: Data Cleanup
1. Delete `data/consistency/` folder
2. Delete `data/novels/` folder
3. Delete contents of `data/uploads/` and `data/web_runs/`
4. Create `.gitkeep` files to preserve empty folders

### Phase 2: Code Updates
1. Update `src/core/library_manager.py`
2. Update `src/consistency/store.py`
3. Update `src/web/web_server.py`
4. Update `cli.py`
5. Update `docs/DATA_STORAGE_STRATEGY.md`

### Phase 3: Testing
1. Start web server
2. Upload test EPUB
3. Verify folder structure created correctly
4. Verify consistency data stored in novel folder
5. Test chapter extraction and processing

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Novel name collisions | High | Add validation to prevent duplicate names |
| Breaking existing API clients | Medium | Document API changes clearly |
| Path length issues on Windows | Low | Truncate long titles if needed |

## Questions Resolved

1. ✅ Consistency data: Novel-specific (not global)
2. ✅ Uploads/web_runs: Keep empty folders
3. ✅ Folder naming: Novel name only (no ID prefix)
