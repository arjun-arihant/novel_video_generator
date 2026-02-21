# Phase 1: Planning for Novel Video Generator Fixes

This document outlines the systematic plan to address the 6 reported issues regarding storage paths, UI features, frontend progress tracking, image prompts, and API bugs.

## Issue 1: Storage Locations (`web_runs`)
**Problem**: Output runs and extracted scenes are stored globally in `data/web_runs` instead of inside each novel's specific folder.
**Solution**:
1. Modify `src/web/web_server.py` to stop using a global `WEB_RUN_DIR`.
2. Determine `WEB_RUN_DIR` dynamically based on the current novel: `manager.get_novel_dir(novel_title) / "web_runs"`.
3. Update the `serve_runs` route to accept the novel title: `@app.route("/runs/<path:novel_title>/<path:filename>")`.
4. Update frontend `app.js` to ensure the image `src` uses the new novel-specific URL structure.

## Issue 2: Rename Novels
**Problem**: The "Edit Title" feature exists in the frontend but fails or isn't completely functional in the backend.
**Solution**:
1. Implement or fix `update_novel_title(old_title, new_title)` within `src/core/library_manager.py`. It should safely rename the inner files (like `metadata.json`) and gracefully rename the folder if appropriate.
2. Ensure the UI gracefully reloads the library list to reflect the updated title without throwing errors.

## Issue 3: Loading Animations & Working State
**Problem**: Clicking the play button or generation buttons leaves the user waiting with no real feedback, even though the backend is sending Server-Sent Events (SSE) with progress details.
**Solution**:
1. Enhance the UI in `src/web/static/index.html` and `app.js` to display the active SSE details.
2. Introduce a clear, visible progress overlay or inline terminal-like text box that displays the `msg.detail` string from the SSE stream so the user knows exactly which scene/step is processing.

## Issue 4: Image Generation Prompt Complexity
**Problem**: The generated `visual_description` describes multiple scenes or sequences, confusing the image generator.
**Solution**:
1. Update the `user_template` prompt in `src/parser/openrouter_parser.py`.
2. Add strict instructions: *"visual_description must describe ONE single static snapshot in time. Do not describe character movements, changing actions, or multiple sequential events in this field."*

## Issue 5: Image Output Display in Panel
**Problem**: After an image is generated, the panel does not automatically update with the new image.
**Solution**:
1. Verify `refreshImage(idx)` logic in `app.js`.
2. Fix the `img.src` URL to match the newly updated (Issue 1) `/runs/<novel_title>/...` path.
3. Ensure the UI element removes any `display: none` restrictions immediately after the image fully loads.

## Issue 6: "Error Loading Characters"
**Problem**: The "The Voice" tab tries to load `/api/characters` and fails with an HTML error because the endpoint doesn't exist.
**Solution**:
1. Fix the `fetch` request in `loadCharacters()` inside `src/web/static/app.js`.
2. Update it to call the correct endpoint: `/api/novels/${encodeURIComponent(state.currentNovelTitle)}/characters`.

---

## Agent Allocation for Phase 2 implementation
Following the orchestration protocol, once approved, three agents will be deployed to implement this plan in parallel:
- **`backend-specialist`**: Fix `library_manager.py` remaining logic, update `web_server.py` directory structures, and refine the `openrouter_parser.py` prompt.
- **`frontend-specialist`**: Fix the image URLs, progress streaming UI overlays, and correct the characters fetch API route in `app.js` and `index.html`.
- **`test-engineer`**: Run the Python validations and `eslint`/health checks to ensure everything ties together without breaking.
