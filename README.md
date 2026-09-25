# 📦 File Manager

Automatically sort, sub-sort and compress image files — no technical knowledge needed.

A macOS and Windows automation tool that organises advertising and creative files into the correct folders instantly. Drop your files, click Run, done.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🗂 Auto Folder Creation | Only creates folders when matching files are found |
| 📂 Smart Sorting | Case-insensitive, plural-aware, 90% fuzzy keyword matching |
| 📐 Dimension Sub-sorting | Groups files by image size e.g. 1200x628 — user confirms first |
| 🗜️ File Compression | Reduces file sizes to preset KB/MB limits per platform |
| ✏️ Custom Folders | Add your own folder rules on the fly — saved permanently |
| 🌐 Web UI | Clean browser interface — no terminal needed after setup |
| 👁 Dry Run Mode | Preview everything safely before applying any changes |
| 🔍 Fuzzy Matching | Handles plurals (PMAXS = PMAX), typos and case differences |
| 🔁 Remembers Custom Rules | Custom folders saved to custom_config.json for future runs |
| 🖥️ Cross Platform | Works on both macOS and Windows |

---

## 📋 Requirements

| | macOS | Windows |
|--|-------|---------|
| OS | macOS 10.13+ | Windows 10+ |
| Python | 3.9+ | 3.9+ (auto-installed) |
| Pillow | Auto-installed | Auto-installed |

> **Windows users** — Python is installed automatically by the installer if not found.
>
> **Mac users** — Python must be installed first from [python.org/downloads](https://python.org/downloads)

---

## 🚀 Installation

### macOS

1. Install Python from [python.org/downloads](https://python.org/downloads) if not already installed
2. Click the green **Code** button on this page → **Download ZIP**
3. Unzip the downloaded file
4. Open the **mac** folder
5. Double-click **FileManager_Setup.command**
6. If macOS blocks it → Right-click → Open → Open
7. Follow the on-screen instructions
8. **FileManager.command** appears on your Desktop — double-click it anytime to launch

### Windows

1. Click the green **Code** button on this page → **Download ZIP**
2. Right-click the ZIP → **Extract All** → **Extract**
3. Open the extracted folder → open the **windows** folder
4. Double-click **FileManager_Setup.bat**
5. If Windows blocks it → click **More info** → **Run anyway**
6. Python installs automatically if not found on your PC
7. **FileManager.bat** appears on your Desktop — double-click it anytime to launch

---

## 🖥️ How to Use

1. Double-click the launcher on your Desktop
2. Your browser opens automatically at http://localhost:8765
3. Click **Browse** and select your folder containing files
4. Keep **Dry Run ON** and click **Run** to preview what will happen
5. Check the output log looks correct
6. Turn off **Dry Run** and click **Run** again to apply for real
7. Done — files are sorted, sub-sorted and compressed ✅

---

## ⚙️ How It Works

**Step 1 — Auto-create folders**
Only creates folders when matching files are found. No empty folders ever created.

**Step 2 — Sort files into folders**
Uses keyword matching, aliases and 90% fuzzy matching. Case-insensitive and plural-aware.

**Step 3 — Sub-sort by dimensions (you confirm first)**
Groups files by image size e.g. 1200x628/. Only runs if 2 or more different sizes exist in a folder. Reads actual image metadata if no size is in the filename.

**Step 4 — Compress file sizes**
Reduces to preset KB/MB limits per platform. PNG always kept as-is (lossless format). Dimensions are never changed — only quality is reduced.

---

## 🔍 Matching Rules

| Rule | Example | Result |
|------|---------|--------|
| Case-insensitive | pmax_banner.jpg | PMAX/ ✅ |
| Separator-agnostic | PMAX_1200x628.jpg | PMAX/ ✅ |
| Plural-aware | PMAXS_banner.jpg | PMAX/ ✅ |
| Plural in phrase | GRAB_REWARD_DETAIL_PAGES.jpg | GRAB REWARD DETAIL PAGE/ ✅ |
| Alias | GDB_1200x628.jpg | GOOGLE DISCOVERY BANNER/ ✅ |
| Alias | MAN_300x250.jpg | MICROSOFT AUDIENCE NETWORK/ ✅ |
| 90% fuzzy | GOOGL_DISCOVERY_BANNER.jpg | GOOGLE DISCOVERY BANNER/ ✅ |
| No match | RANDOM_FILE.jpg | left in place, no folder created ⏭️ |

---

## 📁 Default Folders and Size Limits

| Folder | Alias | Max Size |
|--------|-------|----------|
| CAROUSELL HP BILLBOARD | — | — |
| CAROUSELL HP INTERSTITIAL | — | — |
| CAROUSELL NATIVE DOUBLE PANEL | — | — |
| CAROUSELL NATIVE INBOX | — | — |
| CRITEO | — | 5 MB |
| FB IG | — | — |
| FOODPANDA IMAGE AD | — | 100 KB |
| GOOGLE DISCOVERY BANNER | GDB | 5120 KB |
| GOOGLE UAC | — | 5120 KB |
| GRAB BRANDED VEH ICON | — | 450 KB |
| GRAB HOME FEED | — | 250 KB |
| GRAB NATIVE IMAGE | — | 250 KB |
| GRAB REWARD DETAIL PAGE | — | 250 KB |
| LEMON8 COVER IMAGE | — | 500 KB |
| MICROSOFT AUDIENCE NETWORK | MAN | — |
| PMAX | — | — |
| REDDIT CAROUSEL | — | 20 MB |
| REDDIT CAROUSELL | — | 20 MB |
| REDDIT IMAGE AD | — | 3 MB |
| REDDIT IMAGE AD THUMBNAIL | — | 3 MB |
| SHOPBACK | — | 500 KB |
| TIKTOK DISPLAY CARD | — | — |
| VIBER | — | — |
| XIAO HONG SHU | — | 700 KB |
| YT COMP | — | 100 KB |

Folders without a size limit — files are sorted but not compressed.

---

## ✏️ Customisation

Open **file_manager.py** in any text editor.

**Add a new folder**

Find the FOLDERS list and add your folder name:

    FOLDERS = [
        "PMAX",
        "MY NEW FOLDER",
    ]

**Set a size limit in KB**

Find SIZE_RULES and add your limit:

    SIZE_RULES = {
        "MY NEW FOLDER" : 500,
    }

**Add a short alias**

Find ALIASES and add your shortcut:

    ALIASES = {
        "GDB" : "GOOGLE DISCOVERY BANNER",
        "XYZ" : "MY NEW FOLDER",
    }

**Adjust fuzzy match sensitivity**

    SIMILARITY_THRESHOLD = 0.90

0.90 means 90% match required. Higher is stricter. Lower is looser.

---

## 🆕 Custom Folders via UI

When files are not matched by any existing folder, a yellow panel appears automatically at the bottom of the UI.

- Type the folder name you want to create
- Optionally set a max file size in KB
- Click **Create and Sort**
- The folder is saved permanently and remembered for all future runs

If the name you type is similar to an existing folder (fuzzy match), it will ask if you want to use that instead. If it is completely new, it asks for confirmation before creating.

---

## 🗑️ Uninstall

**macOS**

Open the mac folder from the downloaded ZIP and double-click **FileManager_Uninstall.command**

**Windows**

Open the windows folder from the downloaded ZIP and double-click **FileManager_Uninstall.bat**

Your sorted files and folders are never touched. Only the app itself is removed.

---

## 📂 Repository Structure

    file-manager/
    ├── mac/
    │   ├── FileManager_Setup.command       ← run this to install on Mac
    │   ├── FileManager.command             ← Mac launcher
    │   └── FileManager_Uninstall.command   ← removes app from Mac
    ├── windows/
    │   ├── FileManager_Setup.bat           ← run this to install on Windows
    │   └── FileManager_Uninstall.bat       ← removes app from Windows
    ├── file_manager.py                     ← core logic (shared Mac + Windows)
    ├── file_manager_ui.py                  ← web UI server (shared Mac + Windows)
    ├── README.md
    ├── LICENSE
    └── .gitignore

---

## 🔧 Troubleshooting

### macOS

| Problem | Solution |
|---------|----------|
| macOS blocks the file | Right-click → Open → Open |
| Browser does not open | Go to http://localhost:8765 manually |
| Port already in use | Run: pkill -9 -f file_manager_ui.py |
| Compression not working | Run: pip3 install Pillow |
| Files not sorted | Run Dry Run first to preview |
| file_manager.py not found | Both .py files must be in Desktop/FileSorter/ |

### Windows

| Problem | Solution |
|---------|----------|
| Windows blocks the file | Click More info → Run anyway |
| python is not recognized | Reinstall Python and tick Add Python to PATH |
| Browser does not open | Go to http://localhost:8765 manually |
| Port already in use | Restart your PC and try again |
| Compression not working | Open Command Prompt and run: pip install Pillow |
| Installer closes immediately | Run it from Command Prompt to see the error |
| Already installed message | Choose option 1 to Launch or 2 to Reinstall |

---

## 🗺️ Roadmap

- [x] macOS support
- [x] Windows support
- [x] Web UI browser-based
- [x] Dry Run mode
- [x] Custom folders with persistent memory
- [x] Fuzzy matching plural-aware 90% similarity
- [x] Auto dimension detection from image metadata
- [x] Sub-sort confirmation before executing
- [x] One-click installers for Mac and Windows
- [x] Uninstallers for Mac and Windows
- [ ] Video file support
- [ ] Batch rename files
- [ ] Export sort report as CSV or PDF
- [ ] Scheduled auto-sort

---

## 📄 License

MIT License — free to use, modify and distribute.
See [LICENSE](LICENSE) for full details.

---

## 👤 Author

Made by **Shahir Zambri**

GitHub: [@shahirzambri](https://github.com/shahirzambri)

---

## 🙏 Built With

- [Python](https://python.org) — core language
- [Pillow](https://python-pillow.org) — image compression
- HTML, CSS, JavaScript — web UI
- No frameworks, no dependencies beyond Pillow
