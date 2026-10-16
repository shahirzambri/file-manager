# File Manager — Handoff

## What It Is
A Python tool for macOS and Windows that sorts ad creative image files into
platform folders, optionally sub-sorts them by dimension, then compresses them
to size limits. It opens as a desktop window via PyWebView (no browser).

GitHub: https://github.com/shahirzambri/file-manager
Local:  ~/Desktop/FileSorter/

## Pipeline
1. Auto-create folders (only when matching files exist)
2. Sort files: keyword, alias (GDB, MAN), case-insensitive, plural-aware,
   90% fuzzy match
3. Sub-sort by dimension (UI toggle). Runs only if 2+ different sizes exist
   in a folder. Falls back to image metadata if the filename has no size.
4. Compress JPG/WebP/GIF to KB limits. PNG untouched. Dimensions never change.
- Dry Run previews without changing anything.
- Unmatched files show a "custom folder" panel. Custom folders save to
  custom_config.json (gitignored) and are fuzzy-checked before creation.

## Repo Structure
    mac/      FileManager_Setup.command, FileManager.command, FileManager_Uninstall.command
    windows/  FileManager_Setup.bat, FileManager_Uninstall.bat
    file_manager.py      core logic (shared)
    file_manager_ui.py   PyWebView window + local HTTP server on port 8765 (shared)
    README.md, LICENSE, .gitignore

## Key Settings (file_manager.py)
FOLDERS, ALIASES, SIZE_RULES (KB), SIMILARITY_THRESHOLD = 0.90

## Current State
- UI redesigned in Apple frosted-glass style (done).
- Run button: blue when Dry Run ON, red when OFF. Must stay this way.
- Windows installer installs Python (if missing), Pillow and PyWebView,
  and creates FileManager.bat on the Desktop.

## Environment Notes
- Mac: Python 3.9 (/usr/bin/python3), user is NOT an admin (no sudo).
  pywebview 6.2.1 installed.
- .app bundles failed (Gatekeeper, no admin). Mac launcher is
  FileManager.command on the Desktop. Do not reintroduce .app builds.
- Windows .bat files: avoid labels inside if-blocks, avoid `|` in
  echo-generated launchers, avoid inline multi-line Python.
- User prefers full-file rewrites to copy-paste, step-by-step instructions.
- Push: git add . && git commit -m "..." && git push

## Known Issues
- mac/FileManager_Setup.command references build_app.py (deleted). Needs a
  rewrite to install Pillow + pywebview and create FileManager.command.
- README says Mac installs "FileManager.app". Should say FileManager.command.

## Next Task
Fix mac/FileManager_Setup.command (see Known Issues), then update README
to match.
