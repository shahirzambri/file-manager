# File Manager — Handoff

## What It Is
A Python tool for macOS and Windows that sorts ad creative image files into
platform folders, optionally sub-sorts them by dimension, then compresses them
to size limits. It opens as a desktop window via PyWebView (no browser).

GitHub: https://github.com/shahirzambri/file-manager
Local:  ~/Desktop/FileSorter/

## Pipeline
1. Auto-create folders (only when matching files exist)
2. Sort files: built-in aliases (GDB, MAN), built-in folders (fuzzy,
   plural-aware, 90%), then saved identifiers (whole-section match only)
3. Sub-sort by dimension (UI toggle). Runs only if 2+ different sizes exist
   in a folder. Falls back to image metadata if the filename has no size.
4. Compress JPG/WebP/GIF to KB limits. PNG untouched. Dimensions never change.
5. Smart Sort panel for unrecognized files (see below)
- Dry Run previews without changing anything.

## Smart Sort (unrecognized files)
- Splits filenames on "_" (or "-" if there are no underscores). Ignores
  dimensions, noise words (v1, FINAL, copy, NEW...) and bracketed text.
- Identifier = the section that varies most. 2-letter country codes skipped.
  Single files are compared with recognized files from the same batch.
  Files that differ only by dimension get a "Low confidence" flag.
- Panel shows one row per identifier: checkbox, editable name, "Map to"
  existing folder, optional Max KB. Buttons: Accept All, Confirm, Skip All.
  An "Identifier section" dropdown lets the user pick another section.
- Live run: Confirm creates folders, moves files, saves identifiers, then
  sub-sorts and compresses only the new folders.
- Dry Run: Accept All / Confirm asks first, saves the identifiers, turns
  Dry Run OFF and runs everything live (endpoint /save-and-run).
- Skip / untick = skipped for this run only; nothing is saved.
- Manual "Create & Sort" folder input stays below the panel as a fallback.

## Saved Config (custom_config.json, gitignored)
    {"folders": [...], "size_rules": {...}, "aliases": {"META": "FB IG"}}
Saved names match whole sections only (LINE never matches ONLINE).
Folder names are UPPERCASE, underscores turned into spaces.

## Repo Structure
    mac/      FileManager_Setup.command, FileManager.command, FileManager_Uninstall.command
    windows/  FileManager_Setup.bat, FileManager_Uninstall.bat
    file_manager.py      core logic + Smart Sort (shared)
    file_manager_ui.py   PyWebView window + local HTTP server on port 8765 (shared)
    README.md, LICENSE, .gitignore

## Key Functions
- file_manager.py: run_all, detect_identifiers, apply_identifiers,
  save_identifiers, create_custom_folder, find_target_folder, section_match
- file_manager_ui.py endpoints: /run, /poll, /browse, /skipped, /detect,
  /check-folder, /add-folder, /apply-identifiers, /save-and-run

## Key Settings (file_manager.py)
FOLDERS, ALIASES, SIZE_RULES (KB), SIMILARITY_THRESHOLD = 0.90, NOISE_WORDS

## Rules to Keep
- UI: Apple frosted-glass style. Run button blue when Dry Run ON, red when OFF.
- Dry Run never changes files unless the user confirms leaving it.
- Do not reintroduce .app builds (no admin rights, Gatekeeper blocks them).

## Environment Notes
- Mac: Python 3.9 (/usr/bin/python3), user is NOT an admin (no sudo).
  pywebview 6.2.1 installed. Launcher: FileManager.command on the Desktop.
- Windows .bat files: avoid labels inside if-blocks, avoid `|` in
  echo-generated launchers, avoid inline multi-line Python.
- User prefers full-file rewrites or one-paste patch scripts, with
  step-by-step Terminal instructions.
- Push: git add . && git commit -m "..." && git push

## Known Issues
- Cosmetic: in the Smart Sort panel, the Max KB box wraps onto its own line
  under each row. Should fit on one line.
- Smart Sort has only been tested on a few real batches so far.

## Next Task
(Write your next idea here before starting a new session.)

## Future Updates (parked)
1. DONE: Name-clash sub-sort bug fixed (sub-sort moves the renamed new file; preview and Dry Run predict renames).
2. Merge manual Unsorted panel into Smart Sort review ("Add a folder" row, whole-section matching, live in tree).
3. Animated WebP loses animation on compression (same fix as GIF).
4. Dates in filenames (e.g. 20250101) read as sub-sort sizes.
5. JPG/WebP compression drops embedded colour profiles.
6. Remove test names (RAKUTEN, LAZADA, SHOPEE?) from custom_config.json.
7. Size limits editor (Settings screen for Max KB per platform).
8. Test the three-panel layout and tree on Windows.

## Status (end of session)
Done: GIF fix, shared plan engine, three-panel layout + Max KB fix, folder tree + live Smart Sort, Dry Run rehearsal, name-clash fix.
In progress: item 6, cleaning test names from custom_config.json (clean_config.py on Desktop; backup at ~/Desktop/custom_config_backup.json).
Next suggested: item 8 Windows test, then item 2 merge manual panel into Smart Sort.
Delivery tip: prefer patch scripts over clipboard pastes; check files with grep before running.
