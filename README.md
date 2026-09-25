# 📦 File Manager

> Automatically sort, sub-sort and compress image files on macOS — no technical knowledge needed.

A macOS automation tool that organises advertising and creative files into
the correct folders instantly. Drop your files, click Run, done.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🗂 Auto Folder Creation | Only creates folders when matching files exist |
| 📂 Smart Sorting | Case-insensitive, plural-aware, 90% fuzzy keyword matching |
| 📐 Dimension Sub-sorting | Groups files by image size e.g. `1200x628/` (optional, user confirms) |
| 🗜️ File Compression | Reduces file sizes to preset KB limits per platform |
| ✏️ Custom Folders | Add your own folder rules on the fly — saved permanently |
| 🌐 Web UI | Clean browser interface — no terminal needed after setup |
| 👁 Dry Run Mode | Preview everything safely before applying any changes |
| 🔍 Fuzzy Matching | Handles plurals (PMAXS = PMAX), typos and case differences |
| 🔁 Remembers Custom Rules | Custom folders saved to `custom_config.json` for future runs |

---

## 📋 Requirements

- **macOS** 10.13 or later
- **Python 3.9+** → [python.org/downloads](https://python.org/downloads)
- **Pillow** (auto-installed by the installer)

---

## 🚀 Quick Install — macOS

### Option A — One-click Installer *(Recommended)*

1. Download **`FileManager_Setup.command`** from this repo
2. Double-click it
3. If macOS blocks it → **Right-click → Open → Open**
4. Follow the on-screen instructions
5. Browser opens automatically with File Manager UI ✅

Everything is installed automatically:
- Checks Python is installed
- Installs Pillow
- Creates all scripts on your Desktop
- Creates the launcher

### Option B — Manual Setup

```bash
# Clone the repo
git clone https://github.com/shahirzambri/file-manager.git
cd file-manager

# Install Pillow
pip3 install Pillow

# Copy scripts to Desktop
cp file_manager.py ~/Desktop/FileSorter/
cp file_manager_ui.py ~/Desktop/FileSorter/

# Create launcher
cp FileManager_Setup.command ~/Desktop/
chmod +x ~/Desktop/FileManager_Setup.command

# Run
python3 ~/Desktop/FileSorter/file_manager_ui.py

## 🗑️ Uninstall

### Mac
Double-click `mac/FileManager_Uninstall.command`

### Windows
Double-click `windows/FileManager_Uninstall.bat`

> Your sorted files and folders are never touched.
> Only the app itself is removed.
