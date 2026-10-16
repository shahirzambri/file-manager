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
| 📐 Dimension Sub-sorting | Groups files by image size e.g. 1200x628 — optional toggle |
| 🗜️ File Compression | Reduces file sizes to preset KB/MB limits per platform |
| ✏️ Custom Folders | Add your own folder rules on the fly — saved permanently |
| 🖥️ Desktop App | Opens as a desktop window with a clean frosted-glass design |
| 👁 Dry Run Mode | Preview everything safely before applying any changes |
| 🔍 Fuzzy Matching | Handles plurals (PMAXS = PMAX), typos and case differences |
| 🌐 Cross Platform | Works on both macOS and Windows |

---

## 📋 Requirements

| | macOS | Windows |
|--|-------|---------|
| OS | macOS 10.13+ | Windows 10+ |
| Python | 3.9+ (install first) | 3.9+ (auto-installed) |
| Pillow | Auto-installed | Auto-installed |
| PyWebView | Auto-installed | Auto-installed |
| Admin rights | Not needed | Not needed |

> **Mac users** — install Python first from [python.org/downloads](https://python.org/downloads)
>
> **Windows users** — Python is installed automatically if it is missing.

---

## 🚀 Installation

### macOS

1. Install Python from [python.org/downloads](https://python.org/downloads) if not already installed
2. Click the green **Code** button on this page and click **Download ZIP**
3. Unzip the downloaded file
4. Open the **mac** folder
5. Double-click **FileManager_Setup.command**
6. If macOS blocks it — Right-click, then Open, then Open again
7. Follow the on-screen instructions
8. **FileManager.command** appears on your Desktop — double-click it anytime to launch
9. Tip: drag FileManager.command to your Dock for quick access

### Windows

1. Click the green **Code** button on this page and click **Download ZIP**
2. Right-click the ZIP and click **Extract All**, then **Extract**
3. Open the extracted folder, then open the **windows** folder
4. Double-click **FileManager_Setup.bat**
5. If Windows blocks it — click **More info**, then **Run anyway**
6. Python, Pillow and PyWebView install automatically if needed
7. **FileManager.bat** appears on your Desktop — double-click it anytime to launch

---

## 🖥️ How to Use

1. Double-click the launcher on your Desktop
2. File Manager opens as a desktop window
3. Click **Browse** and select your folder of files
4. Keep **Dry Run ON** and click **Run** to preview (button is blue)
5. Check the output log looks correct
6. Turn **Dry Run OFF** and click **Run** again to apply for real (button turns red)
7. Done — files are sorted, sub-sorted and compressed ✅

---

## ⚙️ How It Works

**Step 1 — Auto-create folders**
Only creates folders when matching files are found. No empty folders.

**Step 2 — Sort files into folders**
Keyword matching, aliases and 90% fuzzy matching. Case-insensitive and plural-aware.

**Step 3 — Sub-sort by dimensions (optional)**
Groups files by image size e.g. 1200x628. Only runs if 2 or more different sizes exist in a folder. Reads image metadata if the size is not in the filename.

**Step 4 — Compress file sizes**
Reduces JPG, WebP and GIF files to preset limits. PNG is kept as-is. Dimensions never change — only quality is reduced.

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
| No match | RANDOM_FILE.jpg | left in place ⏭️ |

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

Folders without a size limit are sorted but not compressed.

---

## 🆕 Custom Folders

When files don't match any folder, a panel appears at the bottom of the app.

- Type a folder name
- Optionally set a max file size in KB
- Click **Create & Sort**
- The folder is saved and remembered for all future runs

If the name is similar to an existing folder, it uses that folder. If it is new, the app asks you to confirm first.

---

## 🗑️ Uninstall

**macOS** — open the mac folder and double-click **FileManager_Uninstall.command**

**Windows** — open the windows folder and double-click **FileManager_Uninstall.bat**

Your sorted files and folders are never touched. Only the app is removed.

---

## 📂 Repository Structure

    file-manager/
    ├── mac/
    │   ├── FileManager_Setup.command       ← install on Mac
    │   ├── FileManager.command             ← Mac launcher
    │   └── FileManager_Uninstall.command   ← remove from Mac
    ├── windows/
    │   ├── FileManager_Setup.bat           ← install on Windows
    │   └── FileManager_Uninstall.bat       ← remove from Windows
    ├── file_manager.py                     ← core logic (shared)
    ├── file_manager_ui.py                  ← desktop UI (shared)
    ├── README.md
    ├── LICENSE
    └── .gitignore

---

## 🔧 Troubleshooting

### macOS

| Problem | Solution |
|---------|----------|
| macOS blocks the file | Right-click, then Open, then Open |
| App does not open | Run the installer again — it reinstalls PyWebView |
| PyWebView fails to install | Run `xcode-select --install`, then the installer again |
| Port already in use | Run: `pkill -9 -f file_manager_ui.py` |
| Compression not working | Run: `pip3 install Pillow` |
| Files not sorted | Run Dry Run first to preview |

### Windows

| Problem | Solution |
|---------|----------|
| Windows blocks the file | Click More info, then Run anyway |
| python is not recognized | Reinstall Python and tick Add Python to PATH |
| App does not open | Run FileManager.bat from Command Prompt to see the error |
| PyWebView not working | Run: `pip install pywebview` |
| Compression not working | Run: `pip install Pillow` |
| Port already in use | Restart your PC and try again |
| Already installed message | Choose 1 to Launch or 2 to Reinstall |

---

## 🗺️ Roadmap

- [x] macOS and Windows support
- [x] Desktop window via PyWebView
- [x] Apple-style frosted glass UI
- [x] Dry Run mode
- [x] Custom folders with persistent memory
- [x] Fuzzy, plural-aware matching
- [x] Dimension detection from image metadata
- [x] Installers and uninstallers for Mac and Windows
- [ ] Video file support
- [ ] Batch rename files
- [ ] Export sort report as CSV or PDF

---

## 📄 License

MIT License — free to use, modify and distribute. See [LICENSE](LICENSE).

---

## 👤 Author

Made by **Shahir Zambri** — [@shahirzambri](https://github.com/shahirzambri)

---

## 🙏 Built With

- [Python](https://python.org) — core language
- [Pillow](https://python-pillow.org) — image compression
- [PyWebView](https://pywebview.flowrl.com) — desktop window
- HTML, CSS, JavaScript — UI
