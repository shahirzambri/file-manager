# File Manager — Handoff

## What It Is
A Python tool for macOS and Windows that sorts ad creative image files into
platform folders, optionally sub-sorts them by dimension, then compresses them
to size limits. It runs as a desktop window via PyWebView.

GitHub: https://github.com/shahirzambri/file-manager
Local:  ~/Desktop/FileSorter/

## Pipeline
1. Auto-create folders (only when matching files exist)
2. Sort files: keyword, alias (GDB, MAN), case-insensitive, plural-aware,
   90% fuzzy match
3. Sub-sort by dimension (user toggle). Runs only if 2+ different sizes exist.
   Falls back to image metadata when the filename has no size.
4. Compress JPG/WebP/GIF to KB limits. PNG is untouched and dimensions never change.
- Dry Run mode previews without changing anything.
- Unmatched files trigger a "custom folder" panel. Custom folders are saved to
  custom_config.json and fuzzy-checked against the existing list before creation.

## Repo Structure
    mac/      FileManager_Setup.command, FileManager.command, FileManager_Uninstall.command
    windows/  FileManager_Setup.bat, FileManager_Uninstall.bat
    file_manager.py      core logic (shared)
    file_manager_ui.py   PyWebView desktop UI + local HTTP server on port 8765 (shared)
    README.md, LICENSE, .gitignore

## Key Settings (file_manager.py)
FOLDERS, ALIASES, SIZE_RULES (KB), SIMILARITY_THRESHOLD = 0.90

## Environment Notes
- Mac: Python 3.9 (/usr/bin/python3), user is NOT an admin (no sudo).
  pywebview 6.2.1 installed.
- The .app bundle attempts failed (Gatekeeper / no admin). The Mac launcher is
  FileManager.command on the Desktop.
- Windows .bat files must avoid nested labels and `|` inside echo-generated
  launchers. The launcher is written line by line with echo.
- Push changes with: git add . && git commit -m "..." && git push

## Known Inconsistencies
- README says Mac installs "FileManager.app". The real launcher is FileManager.command.
- mac/FileManager_Setup.command references build_app.py, which was deleted.
  It needs a rewrite so it installs pywebview and creates FileManager.command.

## Next Task
Redesign the UI in file_manager_ui.py (the HTML/CSS inside it) in a modern Apple
style: clean, frosted glass. Keep all functionality the same. The Run button must
stay blue when Dry Run is ON and red when it is OFF.
