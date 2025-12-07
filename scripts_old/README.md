# Archived Scripts

This directory contains the old scripts that have been replaced by the unified CLI (`cli.py`).

These scripts are kept for reference but are no longer maintained.

## Migration Guide

Old scripts have been replaced with a unified CLI interface:

### Old → New

```bash
# Old: Individual scripts
python scripts/run_scene_extraction.py --chapter chapter.json
python scripts/run_image_generation.py --scenes scenes.json
python scripts/run_tts.py --scenes scenes.json
python scripts/run_video_build.py --scenes scenes.json
python scripts/run_pipeline.py --chapter chapter.json

# New: Unified CLI
python cli.py extract chapter.json
python cli.py images scenes.json
python cli.py audio scenes.json
python cli.py video scenes.json
python cli.py pipeline chapter.json
```

## What Changed

1. **Consolidated**: All commands in one CLI with subcommands
2. **Scene-based TTS**: Audio generation now works per-scene (not per-paragraph)
3. **Better error handling**: Validation, retry logic, and clearer error messages
4. **Type safety**: Full type hints throughout
5. **Common utilities**: Shared config, logging, and validation

For the new CLI usage, run: `python cli.py --help`
