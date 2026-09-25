#!/bin/bash
# ══════════════════════════════════════════════════════════════
# File Manager — Auto Installer
# Double-click this file to install everything automatically.
# ══════════════════════════════════════════════════════════════

clear
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║        📦  File Manager — Installer          ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
echo "  This will install File Manager on your Mac."
echo "  Everything will be set up automatically."
echo ""
echo "  Press Enter to start, or Ctrl+C to cancel."
read

# ── Paths ─────────────────────────────────────────────────────
DEST="$HOME/Desktop/FileSorter"
LAUNCHER="$HOME/Desktop/FileManager.command"

# ── Step 1: Check Python ──────────────────────────────────────
echo "  [1/5] Checking Python..."

PYTHON=""
for P in \
    /usr/local/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if [ -x "$P" ]; then
        PYTHON="$P"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    PYTHON=$(command -v python3 2>/dev/null)
fi

if [ -z "$PYTHON" ]; then
    echo ""
    echo "  ❌ Python 3 not found!"
    echo ""
    echo "  Please install Python 3 first:"
    echo "  1. Go to https://python.org/downloads"
    echo "  2. Download and install Python for macOS"
    echo "  3. Run this installer again"
    echo ""
    open "https://www.python.org/downloads/"
    read
    exit 1
fi

PY_VER=$("$PYTHON" --version 2>&1)
echo "  ✅ Found: $PY_VER at $PYTHON"
echo ""

# ── Step 2: Install Pillow ────────────────────────────────────
echo "  [2/5] Installing Pillow (image compression library)..."
"$PYTHON" -m pip install Pillow --quiet --upgrade 2>/dev/null

if "$PYTHON" -c "from PIL import Image" 2>/dev/null; then
    echo "  ✅ Pillow is ready"
else
    echo "  ⚠️  Pillow could not be installed — compression will be skipped"
fi
echo ""

# ── Step 3: Create FileSorter folder ─────────────────────────
echo "  [3/5] Creating FileSorter folder..."
mkdir -p "$DEST"
echo "  ✅ Created: $DEST"
echo ""

# ── Step 4: Write scripts ─────────────────────────────────────
echo "  [4/5] Writing scripts..."

# ── Write file_manager.py ─────────────────────────────────────
cat > "$DEST/file_manager.py" << 'PYEOF'
#!/usr/bin/env python3
"""
File Manager — All-in-One
──────────────────────────────────────────────────────────────
STEP 1 → CREATE FOLDERS : Auto-create only folders with matching files
STEP 2 → SORT           : Move files into matched folders
STEP 3 → SUB-SORT       : Move files into dimension sub-folders
STEP 4 → REDUCE         : Compress file sizes
──────────────────────────────────────────────────────────────
"""

import re
import shutil
import sys
import json
from pathlib import Path
from io import BytesIO
from difflib import SequenceMatcher

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

FOLDERS = [
    "CAROUSELL HP BILLBOARD",
    "CAROUSELL HP INTERSTITIAL",
    "CAROUSELL NATIVE DOUBLE PANEL",
    "CAROUSELL NATIVE INBOX",
    "CRITEO",
    "FB IG",
    "FOODPANDA IMAGE AD",
    "GOOGLE DISCOVERY BANNER",
    "GOOGLE UAC",
    "GRAB BRANDED VEH ICON",
    "GRAB HOME FEED",
    "GRAB NATIVE IMAGE",
    "GRAB REWARD DETAIL PAGE",
    "LEMON8 COVER IMAGE",
    "MICROSOFT AUDIENCE NETWORK",
    "PMAX",
    "REDDIT CAROUSEL",
    "REDDIT CAROUSELL",
    "REDDIT IMAGE AD THUMBNAIL",
    "REDDIT IMAGE AD",
    "SHOPBACK",
    "TIKTOK DISPLAY CARD",
    "VIBER",
    "XIAO HONG SHU",
    "YT COMP",
]

ALIASES = {
    "GDB" : "GOOGLE DISCOVERY BANNER",
    "MAN" : "MICROSOFT AUDIENCE NETWORK",
}

SIZE_RULES = {
    "REDDIT IMAGE AD THUMBNAIL"   :  3072,
    "REDDIT IMAGE AD"             :  3072,
    "REDDIT CAROUSELL"            :  20480,
    "REDDIT CAROUSEL"             :  20480,
    "FOODPANDA IMAGE AD"          :  100,
    "GOOGLE UAC"                  :  5120,
    "SHOPBACK"                    :  500,
    "LEMON8 COVER IMAGE"          :  500,
    "GRAB BRANDED VEH ICON"       :  450,
    "GRAB NATIVE IMAGE"           :  250,
    "GRAB HOME FEED"              :  250,
    "GRAB REWARD DETAIL PAGE"     :  250,
    "GOOGLE DISCOVERY BANNER"     :  5120,
    "CRITEO"                      :  5120,
    "YT COMP"                     :  100,
    "XIAO HONG SHU"               :  700,
}

SIMILARITY_THRESHOLD = 0.90
CUSTOM_CONFIG_PATH   = Path(__file__).parent / "custom_config.json"
_last_skipped        = []
_last_source         = None
NUMBER_PATTERNS      = [r"\d+x\d+", r"\d+p\b", r"\d{3,}"]
SUPPORTED_FORMATS    = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
COMPRESSIBLE_FORMATS = {".jpg", ".jpeg", ".webp", ".gif"}


def normalize(text):
    text = re.sub(r"\.[^.]+$", "", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.upper().strip()

def strip_plural_s(text):
    words = text.split()
    return ' '.join(w[:-1] if len(w) > 2 and w.endswith('S') else w for w in words)

def similarity_score(a, b):
    if not a or not b: return 0.0
    return SequenceMatcher(None, a, b).ratio()

def fuzzy_match(filename_norm, folder_norm):
    if folder_norm in filename_norm: return True
    fs = strip_plural_s(filename_norm)
    fo = strip_plural_s(folder_norm)
    if fo in fs: return True
    if folder_norm in fs: return True
    if fo in filename_norm: return True
    fc = re.sub(r'\b\d+[xX]\d+\b|\b\d+p\b|\b\d{3,}\b', '', filename_norm)
    fc = re.sub(r'\s+', ' ', fc).strip()
    fcs = strip_plural_s(fc)
    scores = [
        similarity_score(fc, folder_norm), similarity_score(fc, fo),
        similarity_score(fcs, folder_norm), similarity_score(fcs, fo),
    ]
    return bool(scores) and max(scores) >= SIMILARITY_THRESHOLD

def folders_similar(a, b):
    a, b = normalize(a), normalize(b)
    as_, bs = strip_plural_s(a), strip_plural_s(b)
    if a == b or as_ == bs: return True
    scores = [similarity_score(a,b), similarity_score(as_,bs),
              similarity_score(a,bs), similarity_score(as_,b)]
    return bool(scores) and max(scores) >= SIMILARITY_THRESHOLD

def load_custom_config():
    try:
        if CUSTOM_CONFIG_PATH.exists():
            with open(CUSTOM_CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {"folders": [], "size_rules": {}}

def save_to_custom_config(folder_name, max_kb=None):
    config = load_custom_config()
    if folder_name not in config["folders"]:
        config["folders"].append(folder_name)
    if max_kb and max_kb > 0:
        config["size_rules"][folder_name] = max_kb
    with open(CUSTOM_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def get_effective_folders():
    config = load_custom_config()
    combined = list(FOLDERS)
    for f in config.get("folders", []):
        if f not in combined: combined.append(f)
    return combined

def get_effective_size_rules():
    config = load_custom_config()
    combined = dict(SIZE_RULES)
    combined.update(config.get("size_rules", {}))
    return combined

def get_last_skipped():
    return list(_last_skipped)

def check_folder_exists(folder_name):
    custom_folders = load_custom_config().get("folders", [])
    for f in FOLDERS:
        if folders_similar(folder_name, f):
            return {"exists": True, "source": "builtin", "matched": f}
    for alias, folder in ALIASES.items():
        if folders_similar(folder_name, alias) or folders_similar(folder_name, folder):
            return {"exists": True, "source": "builtin", "matched": folder}
    for f in custom_folders:
        if folders_similar(folder_name, f):
            return {"exists": True, "source": "custom", "matched": f}
    return {"exists": False, "source": "none", "matched": ""}

def get_size_kb(path): return path.stat().st_size / 1024
def format_kb(kb):
    return f"{kb/1024:.2f} MB  ({kb:.0f} KB)" if kb >= 1024 else f"{kb:.1f} KB"

def resolve_conflict(dest):
    if not dest.exists(): return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    c = 1
    while dest.exists():
        dest = parent / f"{stem}_{c}{suffix}"
        c += 1
    return dest

def print_divider(char="─", width=65): print(f"  {char * width}")
def print_header(title):
    print(f"\n{'═'*67}\n  {title}\n{'═'*67}")

def find_target_folder(filename):
    name_norm = normalize(filename)
    for alias, folder in ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", name_norm):
            return folder
    for folder in sorted(get_effective_folders(), key=len, reverse=True):
        if fuzzy_match(name_norm, normalize(folder)):
            return folder
    return None

def run_sort(source, dry_run):
    global _last_skipped, _last_source
    files = sorted([f for f in source.iterdir()
                    if f.is_file() and not f.name.startswith(".")])
    if not files:
        print("  No files found.\n")
        return {"moved": [], "skipped": []}
    file_folder_map = {}
    needed_folders  = set()
    for file in files:
        t = find_target_folder(file.name)
        if t: file_folder_map[file.name] = t; needed_folders.add(t)
    print_header("📁 STEP 1 — Auto-Create Folders")
    print(f"  Files scanned     : {len(files)}")
    print(f"  Folders to create : {len(needed_folders)}\n")
    for folder in sorted(needed_folders):
        fp = source / folder
        if not fp.exists():
            tag = "〰 [DRY RUN]" if dry_run else "✅ Created "
            print(f"  {tag} │ 📁 '{folder}/'")
            if not dry_run: fp.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  ℹ️  Exists   │ 📁 '{folder}/'")
    print_header("📂 STEP 2 — Sort Files into Folders")
    print(f"  Files : {len(files)}  |  Matching: case-insensitive · plural-aware · {int(SIMILARITY_THRESHOLD*100)}% fuzzy\n")
    results = {"moved": [], "skipped": []}
    for file in files:
        tf = file_folder_map.get(file.name)
        if tf:
            dest = resolve_conflict(source / tf / file.name)
            tag  = "〰 [DRY RUN]" if dry_run else "✅ Moved   "
            print(f"  {tag} │ '{file.name}'\n               │ → '{tf}/'\n")
            if not dry_run: shutil.move(str(file), str(dest))
            results["moved"].append({"file": file.name, "folder": tf})
        else:
            print(f"  ⏭  No Match   │ '{file.name}'\n")
            results["skipped"].append(file.name)
    _last_skipped = list(results["skipped"])
    _last_source  = source
    print_divider()
    print(f"  ✅ Moved   : {len(results['moved'])} file(s)")
    print(f"  ⏭  Skipped : {len(results['skipped'])} file(s)")
    if results["skipped"]:
        print("\n  Unmatched:")
        for f in results["skipped"]: print(f"    • {f}")
    print(f"{'═'*67}\n")
    return results

def create_custom_folder(folder_name, max_kb=None, dry_run=False):
    global _last_skipped, _last_source
    if not _last_source or not Path(_last_source).exists():
        return {"error": "No source directory. Run sort first."}
    source    = Path(_last_source)
    name_norm = normalize(folder_name)
    matched, still = [], []
    for fname in _last_skipped:
        (matched if fuzzy_match(normalize(fname), name_norm) else still).append(fname)
    if not matched:
        return {"error": f"No unmatched files contain '{folder_name}'", "still_skipped": still}
    if not dry_run: save_to_custom_config(folder_name, max_kb)
    fp    = source / folder_name
    moved = []
    print_header(f"📁 Custom Folder — '{folder_name}/'")
    if max_kb:
        print(f"  Max size : {max_kb/1024:.0f} MB" if max_kb >= 1024 else f"  Max size : {max_kb} KB")
    else:
        print(f"  Max size : No limit")
    print(f"  Matched  : {len(matched)}\n")
    if not dry_run:
        fp.mkdir(parents=True, exist_ok=True)
        for fname in matched:
            src = source / fname
            if src.exists():
                dest = resolve_conflict(fp / fname)
                shutil.move(str(src), str(dest))
                moved.append(fname)
                print(f"  ✅ Moved : '{fname}'")
        _last_skipped = still
        print(f"\n  ✅ '{folder_name}' saved — remembered for future runs!")
    print_divider()
    print(f"  Moved : {len(moved) if not dry_run else len(matched)}\n  Still skipped : {len(still)}")
    print(f"{'═'*67}\n")
    return {"moved": len(moved if not dry_run else matched), "files": moved if not dry_run else matched,
            "folder": folder_name, "max_kb": max_kb, "still_skipped": still, "saved_to_config": not dry_run}

def extract_number_pattern(filename, file_path=None):
    nc = re.sub(r"\.[^.]+$", "", filename)
    for p in NUMBER_PATTERNS:
        m = re.search(p, nc, re.IGNORECASE)
        if m: return m.group()
    if file_path and PIL_AVAILABLE:
        try:
            ext = Path(file_path).suffix.lower()
            if ext in SUPPORTED_FORMATS:
                img = Image.open(file_path); w,h = img.size; img.close()
                return f"{w}x{h}"
        except Exception: pass
    return None

def run_subsort(source, moved_files, dry_run):
    if not moved_files:
        print("\n  ℹ️  No files sorted — skipping sub-sort.\n"); return
    fm = {}
    for e in moved_files: fm.setdefault(e["folder"],[]).append(e["file"])
    print_header("📁 STEP 3 — Dimension Sub-folder Sort")
    print(f"  Rule: Only sub-sorts if 2+ different patterns exist\n")
    tm = ts = tn = 0
    for fn, fnames in sorted(fm.items()):
        fp = source / fn
        print(f"  📂 '{fn}/'  —  {len(fnames)} file(s)"); print_divider()
        pm = {f: extract_number_pattern(f, fp/f) for f in fnames}
        up = set(p for p in pm.values() if p)
        if len(up) <= 1:
            r = "no pattern" if not up else f"only 1 pattern '{next(iter(up))}'"
            print(f"    ⏭  Skipped — {r}\n       {len(fnames)} file(s) stay in '{fn}/'\n")
            ts += len(fnames); continue
        print(f"    ✅ {len(up)} patterns ({', '.join(sorted(up))}) → sub-sorting\n")
        for f in fnames:
            p = pm[f]
            if p:
                sf   = fp / p
                dest = resolve_conflict(sf / f)
                tag  = "〰 [DRY RUN]" if dry_run else "  ✅ Moved "
                print(f"    {tag} │ '{f}'\n               │ → '{fn}/{p}/'\n")
                if not dry_run: sf.mkdir(parents=True, exist_ok=True); shutil.move(str(fp/f), str(dest))
                tm += 1
            else:
                print(f"    ⏭  No pattern │ '{f}'\n"); tn += 1
    print_divider()
    print(f"  ✅ Sub-Moved : {tm}  ⏭  Single/None : {ts}  ⏭  No Pattern : {tn}")
    print(f"{'═'*67}\n")

def find_size_rule(file_path, source):
    sr = sorted(get_effective_size_rules().items(), key=lambda x: len(x[0]), reverse=True)
    nn = normalize(file_path.name)
    for kw, mb in sr:
        if fuzzy_match(nn, normalize(kw)): return kw, mb
    for alias, folder in ALIASES.items():
        if re.search(r"\b"+re.escape(alias)+r"\b", nn):
            for kw, mb in sr:
                if fuzzy_match(normalize(folder), normalize(kw)): return kw, mb
    try:
        for part in file_path.relative_to(source).parts[:-1]:
            for kw, mb in sr:
                if fuzzy_match(normalize(part), normalize(kw)): return kw, mb
    except ValueError: pass
    return None, None

def compress_jpg(img, tkb):
    lo,hi,best = 1,95,None
    for _ in range(20):
        m = (lo+hi)//2; buf = BytesIO(); img.save(buf,format="JPEG",quality=m,optimize=True)
        d = buf.getvalue()
        if len(d)/1024 <= tkb: best=d; lo=m+1
        else: hi=m-1
    if best is None:
        buf=BytesIO(); img.save(buf,format="JPEG",quality=1,optimize=True); best=buf.getvalue()
    return best

def compress_webp(img, tkb):
    lo,hi,best = 1,95,None
    for _ in range(20):
        m=(lo+hi)//2; buf=BytesIO(); img.save(buf,format="WEBP",quality=m)
        d=buf.getvalue()
        if len(d)/1024<=tkb: best=d; lo=m+1
        else: hi=m-1
    if best is None:
        buf=BytesIO(); img.save(buf,format="WEBP",quality=1); best=buf.getvalue()
    return best

def compress_gif(img, tkb):
    buf=BytesIO(); img.save(buf,format="GIF",optimize=True); return buf.getvalue()

def compress_image(fp, tkb):
    ext = fp.suffix.lower(); okb = get_size_kb(fp)
    if ext==".png": return {"success":False,"png_skip":True,"reason":"PNG kept as-is"}
    try:
        img=Image.open(fp); img.load(); os_=img.size
        if ext in (".jpg",".jpeg"):
            if img.mode in ("RGBA","LA","P"):
                bg=Image.new("RGB",img.size,(255,255,255))
                img=img.convert("RGBA") if img.mode=="P" else img
                mask=img.split()[-1] if img.mode=="RGBA" else None
                bg.paste(img,mask=mask); img=bg
            elif img.mode!="RGB": img=img.convert("RGB")
            c=compress_jpg(img,tkb)
        elif ext==".webp": c=compress_webp(img,tkb)
        elif ext==".gif":  c=compress_gif(img,tkb)
        else: return {"success":False,"png_skip":False,"reason":f"Unsupported '{ext}'"}
        with open(fp,"wb") as f: f.write(c)
        nkb=len(c)/1024; sp=((okb-nkb)/okb)*100
        return {"success":True,"png_skip":False,"original_kb":okb,"new_kb":nkb,
                "saved_pct":sp,"under_target":nkb<=tkb,"dimensions":os_}
    except Exception as e:
        return {"success":False,"png_skip":False,"reason":str(e)}

def run_reducer(source, dry_run):
    files = sorted([f for f in source.rglob("*")
                    if f.is_file() and not f.name.startswith(".")
                    and f.suffix.lower() in SUPPORTED_FORMATS])
    counts = {"compressed":0,"already_ok":0,"untouched":0,"skipped_png":0,"failed":0}
    print_header("🗜️  STEP 4 — File Size Reduction  (PNG kept as-is)")
    print(f"  📋 Active Rules:"); print_divider()
    for kw,kb in get_effective_size_rules().items():
        print(f"    • {kw:<40} → max {kb/1024:.0f} MB" if kb>=1024 else f"    • {kw:<40} → max {kb} KB")
    print_divider(); print(f"  📄 Files : {len(files)}\n")
    for file in files:
        ext=file.suffix.lower(); ckb=get_size_kb(file)
        if ext==".png":
            print(f"  🔒 PNG   │ '{file.name}' — {format_kb(ckb)}\n")
            counts["skipped_png"]+=1; continue
        kw,mb=find_size_rule(file,source)
        if not kw:
            print(f"  ➖ No Rule│ '{file.name}' — {format_kb(ckb)}\n")
            counts["untouched"]+=1; continue
        lim=f"{mb/1024:.0f} MB" if mb>=1024 else f"{mb} KB"
        if ckb<=mb:
            print(f"  ✅ OK    │ '{file.name}' — {format_kb(ckb)} ≤ {lim}\n")
            counts["already_ok"]+=1; continue
        print(f"  🗜️  Compress│ '{file.name}'\n           │ {kw} → {lim} | Current: {format_kb(ckb)}")
        if dry_run:
            print(f"           │ [DRY RUN]\n"); counts["compressed"]+=1; continue
        r=compress_image(file,mb)
        if r["success"]:
            w,h=r["dimensions"]; s="✅ Target met" if r["under_target"] else "⚠️  Best effort"
            print(f"           │ {format_kb(r['original_kb'])} → {format_kb(r['new_kb'])} ({r['saved_pct']:.1f}% saved) {s}\n")
            counts["compressed"]+=1
        else:
            print(f"           │ ❌ {r['reason']}\n"); counts["failed"]+=1
    print_divider()
    for k,v in counts.items(): print(f"  {k:<12}: {v}")
    print(f"{'═'*67}\n")

def run_all(source_dir, dry_run=False, subsort=True):
    source = Path(source_dir.strip().strip("'\"").rstrip("/")).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Folder not found: '{source}'")
    custom = load_custom_config(); cf = custom.get("folders",[])
    print(f"\n{'█'*67}")
    print(f"  📦  FILE MANAGER{'  ⚠️  DRY RUN' if dry_run else ''}")
    print(f"{'█'*67}")
    print(f"  Source   : {source}")
    print(f"  Matching : case-insensitive · plural-aware · {int(SIMILARITY_THRESHOLD*100)}% fuzzy")
    print(f"  Sub-sort : {'✅ ON' if subsort else '⏭  OFF'}")
    if cf: print(f"  Custom   : {', '.join(cf)}")
    print(f"{'█'*67}")
    sr = run_sort(source, dry_run)
    if subsort: run_subsort(source, sr["moved"], dry_run)
    else:
        print_header("📁 STEP 3 — Dimension Sub-folder Sort")
        print(f"  ⏭  Skipped by user.\n{'═'*67}\n")
    if PIL_AVAILABLE: run_reducer(source, dry_run)
    else: print("\n  ⚠️  Pillow not installed — Step 4 skipped.\n")
    print(f"{'█'*67}")
    print(f"  ✅  ALL STEPS COMPLETE!")
    if dry_run: print(f"  ⚠️  DRY RUN — no changes made.")
    if _last_skipped:
        print(f"  ⚠️  {len(_last_skipped)} unmatched:")
        for f in _last_skipped: print(f"     • {f}")
    print(f"{'█'*67}\n")

if __name__ == "__main__":
    args    = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    folder  = args[0] if args else input("\n  Drag folder here: ").strip()
    if not dry_run:
        dry_run = input("  Preview first? (Y/n): ").strip().lower() not in ("n","no")
    subsort = input("  Sub-sort by dimensions? (Y/n): ").strip().lower() not in ("n","no")
    try:
        run_all(folder, dry_run=dry_run, subsort=subsort)
        while _last_skipped:
            if input(f"\n  {len(_last_skipped)} unmatched. Create custom folder? (y/N): ").strip().lower() not in ("y","yes"): break
            fname = input("  Folder name: ").strip()
            if not fname: break
            chk = check_folder_exists(fname)
            if not chk["exists"]:
                if input(f"  '{fname}' not in list. Create anyway? (y/N): ").strip().lower() not in ("y","yes"): continue
            size_str = input("  Max KB (blank = no limit): ").strip()
            create_custom_folder(fname, int(size_str) if size_str.isdigit() else None, dry_run)
        if dry_run and input("  Proceed for real? (y/N): ").strip().lower() in ("y","yes"):
            run_all(folder, dry_run=False, subsort=subsort)
    except FileNotFoundError as e:
        print(f"\n  ❌ {e}\n")
PYEOF

echo "  ✅ file_manager.py written"

# ── Write file_manager_ui.py ──────────────────────────────────
cat > "$DEST/file_manager_ui.py" << 'PYEOF'
#!/usr/bin/env python3
import signal as _sig
try:
    _sig.signal(_sig.SIGHUP, _sig.SIG_IGN)
except Exception:
    pass

import http.server, socketserver, threading, webbrowser
import json, sys, os, signal, socket, time, subprocess
from pathlib import Path
from urllib.parse import unquote_plus, urlparse, parse_qs

try:
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
try:
    from file_manager import (run_all, PIL_AVAILABLE, get_last_skipped,
                               create_custom_folder, check_folder_exists)
    MANAGER_OK = True
except ImportError:
    MANAGER_OK = False; PIL_AVAILABLE = False

PORT  = 8765
_log  = []
_busy = False
_lock = threading.Lock()

def free_port(port):
    try:
        r = subprocess.run(['lsof','-ti',':'+str(port)],capture_output=True,text=True)
        for pid in [p.strip() for p in r.stdout.strip().split('\n') if p.strip()]:
            try: os.kill(int(pid), signal.SIGKILL)
            except: pass
        subprocess.run(['pkill','-9','-f','file_manager_ui.py'],capture_output=True)
        time.sleep(1.5)
    except: pass

def port_free(port):
    try:
        s=socket.create_connection(('127.0.0.1',port),timeout=1); s.close(); return False
    except: return True

class Cap:
    def write(self,t):
        with _lock: _log.append(str(t))
    def flush(self): pass

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads      = True

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split('?')[0]
        if   p=='/':             self.serve_page()
        elif p=='/poll':         self.serve_poll()
        elif p=='/browse':       self.serve_browse()
        elif p=='/skipped':      self.serve_skipped()
        elif p=='/check-folder': self.serve_check_folder()
        else:                    self.send_error(404)
    def do_POST(self):
        if   self.path=='/run':        self.handle_run()
        elif self.path=='/add-folder': self.handle_add_folder()
        else:                          self.send_error(404)
    def serve_page(self):
        m = 'file_manager.py loaded OK' if MANAGER_OK else 'ERROR: file_manager.py not found!'
        p = 'Pillow installed' if PIL_AVAILABLE else 'Pillow NOT installed. Fix: pip3 install Pillow'
        self.respond(200,'text/html; charset=utf-8',
                     HTML.replace('__M__',m).replace('__P__',p).encode('utf-8'))
    def serve_poll(self):
        with _lock: d={'busy':_busy,'log':''.join(_log)}
        self.respond(200,'application/json',json.dumps(d).encode())
    def serve_skipped(self):
        files = get_last_skipped() if MANAGER_OK else []
        self.respond(200,'application/json',json.dumps({'files':files}).encode())
    def serve_check_folder(self):
        qs   = parse_qs(urlparse(self.path).query)
        name = qs.get('name',[''])[0].strip()
        r    = check_folder_exists(name) if (MANAGER_OK and name) else {"exists":False,"source":"none","matched":""}
        self.respond(200,'application/json',json.dumps(r).encode())
    def serve_browse(self):
        path=''
        try:
            r=subprocess.run(['osascript','-e','POSIX path of (choose folder with prompt "Select your source folder:")'],
                             capture_output=True,text=True,timeout=120)
            if r.returncode==0: path=r.stdout.strip()
        except: pass
        self.respond(200,'application/json',json.dumps({'path':path}).encode())
    def handle_run(self):
        pp = self._parse_post()
        folder  = pp.get('folder','').strip()
        dry     = pp.get('dry','1')=='1'
        subsort = pp.get('subsort','1')=='1'
        self.respond(200,'text/plain',b'OK')
        threading.Thread(target=self.task,args=(folder,dry,subsort),daemon=True).start()
    def handle_add_folder(self):
        pp = self._parse_post()
        name   = pp.get('name','').strip()
        size   = pp.get('size','').strip()
        max_kb = int(size) if size.isdigit() else None
        if not name:
            self.respond(400,'application/json',json.dumps({'error':'Name required'}).encode()); return
        self.respond(200,'text/plain',b'OK')
        threading.Thread(target=self.custom_task,args=(name,max_kb),daemon=True).start()
    def _parse_post(self):
        n=int(self.headers.get('Content-Length',0)); raw=self.rfile.read(n).decode('utf-8')
        pp={}
        for part in raw.split('&'):
            if '=' in part: k,v=part.split('=',1); pp[k]=unquote_plus(v)
        return pp
    def task(self,folder,dry,subsort):
        global _log,_busy
        with _lock: _log=[]; _busy=True
        old=sys.stdout; sys.stdout=Cap()
        try:
            if MANAGER_OK: run_all(folder,dry_run=dry,subsort=subsort)
            else: print('file_manager.py not found!')
        except Exception as e: print('\nError: '+str(e)+'\n')
        finally:
            sys.stdout=old
            with _lock: _busy=False
    def custom_task(self,name,max_kb):
        global _busy
        with _lock: _busy=True
        old=sys.stdout; sys.stdout=Cap()
        try:
            if MANAGER_OK:
                r=create_custom_folder(name,max_kb,dry_run=False)
                if 'error' in r: print(f"\n  Error: {r['error']}\n")
            else: print('file_manager.py not found!')
        except Exception as e: print('\nError: '+str(e)+'\n')
        finally:
            sys.stdout=old
            with _lock: _busy=False
    def respond(self,code,ctype,body):
        self.send_response(code)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-cache')
        self.end_headers(); self.wfile.write(body)
    def log_message(self,*a): pass

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>File Manager</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;background:#16161e;color:#c0caf5;min-height:100vh;padding-bottom:54px}
.hdr{background:#1f2335;padding:22px 20px;text-align:center;border-bottom:1px solid #292e42}
.hdr h1{font-size:22px;font-weight:700;margin-bottom:5px}
.hdr p{font-size:12px;color:#565f89}
.wrap{max-width:740px;margin:0 auto;padding:24px 20px}
.lbl{font-size:11px;font-weight:700;color:#7aa2f7;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.sub{font-size:12px;color:#565f89;margin-bottom:10px}
.row{display:flex;gap:8px;margin-bottom:18px}
.fin{flex:1;background:#1f2335;border:1px solid #292e42;border-radius:8px;padding:11px 14px;font-size:13px;font-family:"Menlo","Monaco",monospace;color:#c0caf5;outline:none}
.fin:focus{border-color:#7aa2f7}
.fin::placeholder{color:#3b4261}
.btn{background:#1f2335;color:#c0caf5;border:1px solid #292e42;border-radius:8px;font-size:13px;font-weight:600;padding:11px 22px;cursor:pointer;white-space:nowrap;font-family:inherit}
.btn:hover{opacity:.8}
.btn:disabled{opacity:.4;cursor:not-allowed}
#runBtn{display:block;width:100%;padding:15px;font-size:14px;font-weight:700;border-radius:10px;border:none;margin-bottom:18px;cursor:pointer;font-family:inherit}
#runBtn:hover:not(:disabled){opacity:.88}
#runBtn:disabled{opacity:.4;cursor:not-allowed}
.card{background:#1e2030;border:1px solid #292e42;border-radius:10px;padding:16px 18px;margin-bottom:18px}
.crow{display:flex;align-items:center;gap:14px}
.cinfo h3{font-size:14px;font-weight:600}
.cinfo p{font-size:12px;color:#565f89;margin-top:3px}
.divrow{border-top:1px solid #292e42;margin-top:14px;padding-top:14px}
.sw{position:relative;display:inline-block;width:44px;height:26px;flex-shrink:0;cursor:pointer}
.sw input{opacity:0;width:0;height:0}
.sl{position:absolute;top:0;left:0;right:0;bottom:0;background:#3b4261;border-radius:13px;transition:background .25s;cursor:pointer}
.sl:before{content:"";position:absolute;width:20px;height:20px;background:#fff;border-radius:50%;top:3px;left:3px;transition:transform .25s;box-shadow:0 1px 3px rgba(0,0,0,.3)}
input:checked+.sl{background:#7aa2f7}
input:checked+.sl:before{transform:translateX(18px)}
.bdg{margin-left:auto;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;flex-shrink:0}
.bon{background:#1a2e1a;color:#9ece6a}
.boff{background:#2a1520;color:#f7768e}
.note{margin-top:12px;padding:9px 13px;border-radius:7px;font-size:12px;border-left:3px solid}
.nw{background:#2a2215;color:#e0af68;border-color:#e0af68}
.nl{background:#2a1520;color:#f7768e;border-color:#f7768e}
.ns{background:#1a2030;color:#565f89;border-color:#292e42}
.ltop{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.smbtn{background:none;border:none;color:#565f89;font-size:12px;cursor:pointer;padding:4px 8px;border-radius:5px;font-family:inherit}
.smbtn:hover{color:#c0caf5;background:#292e42}
#log{background:#1f2335;border:1px solid #292e42;border-radius:10px;padding:16px;height:300px;overflow-y:auto;font-family:"Menlo","Monaco",monospace;font-size:11.5px;line-height:1.7;white-space:pre-wrap;word-break:break-word;color:#a9b1d6}
#customSection{display:none;margin-top:20px;border:1px solid #e0af68;border-radius:10px;background:#1a1800;padding:18px}
.ct{font-size:13px;font-weight:700;color:#e0af68;margin-bottom:10px}
.sl2{background:#16161e;border-radius:7px;padding:10px 14px;margin-bottom:14px;font-family:"Menlo",monospace;font-size:11px;color:#a9b1d6;max-height:120px;overflow-y:auto;border:1px solid #292e42}
.si{padding:2px 0}
.cf{display:flex;flex-direction:column;gap:12px}
.cf label{font-size:11px;font-weight:700;color:#7aa2f7;text-transform:uppercase;letter-spacing:.06em;display:block;margin-bottom:5px}
.ci{background:#1f2335;border:1px solid #292e42;border-radius:7px;padding:9px 12px;font-size:13px;color:#c0caf5;outline:none;font-family:inherit;width:100%}
.ci:focus{border-color:#e0af68}
.ci::placeholder{color:#3b4261}
.cr{display:flex;gap:10px;align-items:flex-start}
.cr .ci{flex:1}
#addBtn{background:#e0af68;color:#16161e;border:none;border-radius:7px;font-size:13px;font-weight:700;padding:10px 20px;cursor:pointer;font-family:inherit;white-space:nowrap;flex-shrink:0}
#addBtn:hover:not(:disabled){opacity:.85}
#addBtn:disabled{opacity:.4;cursor:not-allowed}
.cn{font-size:11px;color:#565f89;margin-top:5px;line-height:1.5}
#confirmBox{display:none;margin-top:12px;padding:14px 16px;border-radius:8px;background:#16161e;border:1px solid #7aa2f7;font-size:12px;color:#c0caf5;line-height:1.6}
.cm{margin-bottom:12px}
.cbs{display:flex;gap:8px}
.cy{background:#7aa2f7;color:#16161e;border:none;border-radius:6px;padding:7px 18px;font-weight:700;cursor:pointer;font-size:12px;font-family:inherit}
.cy:hover{opacity:.85}
.cn2{background:#292e42;color:#c0caf5;border:none;border-radius:6px;padding:7px 18px;font-weight:600;cursor:pointer;font-size:12px;font-family:inherit}
.cn2:hover{opacity:.85}
.sbar{position:fixed;bottom:0;left:0;right:0;background:#1f2335;border-top:1px solid #292e42;padding:9px 20px;font-size:12px;color:#565f89;display:flex;align-items:center;gap:8px}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#292e42;border-radius:3px}
</style>
</head>
<body>
<div class="hdr"><h1>&#128230; File Manager</h1>
<p>Auto-create folders &nbsp;&middot;&nbsp; Sort &nbsp;&middot;&nbsp; Sub-sort &nbsp;&middot;&nbsp; Compress</p></div>
<div class="wrap">
<div class="lbl">Source Folder</div>
<div class="sub">Click Browse to pick your folder, or paste the path</div>
<div class="row">
<input class="fin" type="text" id="fi" placeholder="Paste folder path here, or click Browse..."/>
<button class="btn" id="bb" onclick="doBrowse()">Browse</button></div>
<div class="card">
<div class="crow"><label class="sw"><input type="checkbox" id="dc" checked onchange="onDry()"><span class="sl"></span></label>
<div class="cinfo"><h3>Dry Run</h3><p>Preview only &mdash; nothing will be moved or compressed</p></div>
<span class="bdg bon" id="bdg">ON</span></div>
<div class="note nw" id="nt">Dry Run is ON &mdash; safe to run, no files will change</div>
<div class="divrow"><div class="crow">
<label class="sw"><input type="checkbox" id="sc" checked onchange="onSubsort()"><span class="sl"></span></label>
<div class="cinfo"><h3>Sub-sort by Dimensions</h3><p>Group files into sub-folders by image size e.g. 1200x628/</p></div>
<span class="bdg bon" id="sbdg">ON</span></div>
<div class="note ns" id="snt">Sub-sort is ON &mdash; files will be grouped by image dimensions</div></div></div>
<button id="runBtn" style="background:#7aa2f7;color:#16161e;" onclick="doRun()">Run File Manager &nbsp;&nbsp;(Dry Run - Preview only)</button>
<div class="ltop"><div class="lbl" style="margin:0">Output Log</div><button class="smbtn" onclick="doClear()">Clear</button></div>
<div id="log">File Manager ready!

__M__
__P__

How to use:
  1. Click Browse and select your folder
  2. Keep Dry Run ON and click Run to preview
  3. Check the output log
  4. Turn off Dry Run and click Run to apply

Options:
  Dry Run  — preview without changing anything
  Sub-sort — toggle dimension sub-folder grouping
</div>
<div id="customSection">
<div class="ct">&#9888;&nbsp; Unmatched Files &mdash; <span id="skipCount">0</span> file(s) not sorted</div>
<div class="sl2" id="skipList"></div>
<div class="cf">
<div><label>Folder Name</label>
<input class="ci" type="text" id="customName" placeholder="e.g.  XYZ BRAND"/>
<div class="cn">Files whose names contain this keyword will be moved into this folder. Saved permanently.</div></div>
<div><label>Max File Size in KB &mdash; optional</label>
<div class="cr"><div style="flex:1">
<input class="ci" type="number" id="customSize" placeholder="Leave blank = no size limit"/>
<div class="cn">500=500KB &nbsp;|&nbsp; 1024=1MB &nbsp;|&nbsp; blank=keep original</div></div>
<button id="addBtn" onclick="doAddFolder()">Create &amp; Sort</button></div></div>
<div id="confirmBox"><div class="cm" id="confirmMsg"></div>
<div class="cbs"><button class="cy" id="confirmYes">Yes, Create It</button>
<button class="cn2" onclick="hideConfirm()">Cancel</button></div></div></div></div>
</div>
<div class="sbar"><div class="dot" id="dot" style="background:#9ece6a"></div><span id="st">Ready</span></div>
<script>
var _dry=true,_subsort=true,_poll=null,_len=0,_pn='',_ps='';
function onDry(){
  _dry=document.getElementById('dc').checked;
  var b=document.getElementById('bdg'),n=document.getElementById('nt'),btn=document.getElementById('runBtn');
  if(_dry){b.className='bdg bon';b.innerText='ON';n.className='note nw';n.innerText='Dry Run is ON - safe to run, no files will change';btn.style.background='#7aa2f7';btn.style.color='#16161e';}
  else{b.className='bdg boff';b.innerText='OFF';n.className='note nl';n.innerText='Dry Run is OFF - files WILL be moved and compressed!';btn.style.background='#f7768e';btn.style.color='#16161e';}
  updBtn();
}
function onSubsort(){
  _subsort=document.getElementById('sc').checked;
  var b=document.getElementById('sbdg'),n=document.getElementById('snt');
  if(_subsort){b.className='bdg bon';b.innerText='ON';n.innerText='Sub-sort is ON - files grouped by dimensions';}
  else{b.className='bdg boff';b.innerText='OFF';n.innerText='Sub-sort is OFF - files stay in parent folder';}
}
function updBtn(){
  var btn=document.getElementById('runBtn');
  if(btn.disabled)return;
  btn.innerText=_dry?'Run File Manager  (Dry Run - Preview only)':'Run File Manager  (LIVE - files will change!)';
}
function doBrowse(){
  var btn=document.getElementById('bb');btn.disabled=true;btn.innerText='Opening...';setSt('Opening folder picker...');
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;btn.disabled=false;btn.innerText='Browse';
    if(x.status===200){try{var d=JSON.parse(x.responseText);if(d.path&&d.path.length>0){document.getElementById('fi').value=d.path;setSt('Folder: '+d.path);}else{setSt('No folder selected.');}}catch(e){setSt('Paste the path manually.');}}
  };x.open('GET','/browse',true);x.send();
}
function doClear(){document.getElementById('log').innerText='';_len=0;}
function addLog(t){var e=document.getElementById('log');e.innerText+=t;e.scrollTop=e.scrollHeight;}
function setSt(t){document.getElementById('st').innerText=t;}
function setDot(c){document.getElementById('dot').style.background=c;}
function checkSkipped(){
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4||x.status!==200)return;var d;try{d=JSON.parse(x.responseText);}catch(e){return;}
    var f=d.files||[],s=document.getElementById('customSection'),l=document.getElementById('skipList'),c=document.getElementById('skipCount');
    if(f.length>0){s.style.display='block';c.innerText=f.length;var h='';for(var i=0;i<f.length;i++){h+='<div class="si">&#8226; '+f[i]+'</div>';}l.innerHTML=h;}
    else{s.style.display='none';}
  };x.open('GET','/skipped',true);x.send();
}
function showConfirm(n,s,m){
  _pn=n;_ps=s;document.getElementById('confirmMsg').innerHTML=m;
  document.getElementById('confirmYes').onclick=function(){submitFolder(_pn,_ps);};
  document.getElementById('confirmBox').style.display='block';
}
function hideConfirm(){document.getElementById('confirmBox').style.display='none';_pn='';_ps='';}
function submitFolder(name,sv){
  hideConfirm();var btn=document.getElementById('addBtn');btn.disabled=true;btn.innerText='Creating...';setSt('Creating: '+name+'...');
  var b='name='+encodeURIComponent(name)+'&size='+encodeURIComponent(sv);
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;btn.disabled=false;btn.innerText='Create & Sort';
    if(x.status===200){
      document.getElementById('customName').value='';document.getElementById('customSize').value='';
      addLog('\nCreating: '+name+'...\n');
      var pt=setInterval(function(){
        var px=new XMLHttpRequest();
        px.onreadystatechange=function(){
          if(px.readyState!==4||px.status!==200)return;var pd;try{pd=JSON.parse(px.responseText);}catch(e){return;}
          if(pd.log&&pd.log.length>_len){addLog(pd.log.substring(_len));_len=pd.log.length;}
          if(!pd.busy){clearInterval(pt);setSt('Folder created!');setDot('#9ece6a');checkSkipped();}
        };px.open('GET','/poll',true);px.send();
      },700);
    }
  };x.open('POST','/add-folder',true);x.setRequestHeader('Content-Type','application/x-www-form-urlencoded');x.send(b);
}
function doAddFolder(){
  var name=document.getElementById('customName').value.trim(),sv=document.getElementById('customSize').value.trim();
  hideConfirm();if(!name){alert('Please enter a folder name.');return;}setSt('Checking...');
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;if(x.status!==200){submitFolder(name,sv);return;}
    var d;try{d=JSON.parse(x.responseText);}catch(e){submitFolder(name,sv);return;}setSt('');
    if(d.exists){addLog('\nFolder "'+d.matched+'" found in '+( d.source==='custom'?'custom list':'built-in list')+'. Proceeding...\n');submitFolder(name,sv);}
    else{var m='<strong style="color:#f7768e">&#9888; "'+name+'" is not in the folder list.</strong><br><br>This will:<br>&nbsp;&nbsp;&#8226; Create folder "'+name+'"<br>&nbsp;&nbsp;&#8226; Move matching files<br>&nbsp;&nbsp;&#8226; Save permanently<br><br>Create anyway?';showConfirm(name,sv,m);}
  };x.open('GET','/check-folder?name='+encodeURIComponent(name),true);x.send();
}
function doPoll(){
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4||x.status!==200)return;var d;try{d=JSON.parse(x.responseText);}catch(e){return;}
    if(d.log&&d.log.length>_len){addLog(d.log.substring(_len));_len=d.log.length;}
    if(d.busy===false&&_poll!==null){clearInterval(_poll);_poll=null;setBusy(false);setDot('#9ece6a');setSt(_dry?'Dry run done. Turn off Dry Run to apply.':'Done!');checkSkipped();}
  };x.open('GET','/poll',true);x.send();
}
function setBusy(on){
  var btn=document.getElementById('runBtn');btn.disabled=on;
  if(on){btn.style.background='#292e42';btn.style.color='#565f89';btn.innerText='Running...';setDot('#7aa2f7');}
  else{btn.style.background=_dry?'#7aa2f7':'#f7768e';btn.style.color='#16161e';updBtn();}
}
function doRun(){
  var f=document.getElementById('fi').value.trim();
  if(!f.length){alert('Please select a folder first.');return;}
  if(!_dry&&!confirm('Dry Run is OFF.\n\nFiles will be MOVED and COMPRESSED.\nThis cannot be undone.\n\nProceed?'))return;
  doClear();_len=0;hideConfirm();document.getElementById('customSection').style.display='none';
  setBusy(true);setSt('Running...');addLog((_dry?'DRY RUN':'LIVE RUN')+' - '+f+'\nSub-sort: '+(_subsort?'ON':'OFF')+'\n\n');
  var b='folder='+encodeURIComponent(f)+'&dry='+(_dry?'1':'0')+'&subsort='+(_subsort?'1':'0');
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;
    if(x.status===200){_poll=setInterval(doPoll,700);}
    else{addLog('Error: server did not respond.\n');setBusy(false);setSt('Error');setDot('#f7768e');}
  };x.open('POST','/run',true);x.setRequestHeader('Content-Type','application/x-www-form-urlencoded');x.send(b);
}
</script>
</body>
</html>"""

def main():
    try: signal.signal(signal.SIGHUP, signal.SIG_IGN)
    except: pass
    free_port(PORT)
    for _ in range(10):
        if port_free(PORT): break
        time.sleep(0.5)
    url    = 'http://localhost:'+str(PORT)
    server = Server(('',PORT),Handler)
    print('\n  File Manager is running!\n  '+'-'*40)
    print(f'  {url}\n  Press Ctrl+C to quit.\n  '+'-'*40+'\n')
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try: server.serve_forever()
    except (KeyboardInterrupt,SystemExit): pass
    finally:
        try: server.shutdown()
        except: pass

if __name__=='__main__': main()
PYEOF

echo "  ✅ file_manager_ui.py written"

# ── Step 5: Create launcher ───────────────────────────────────
echo "  [5/5] Creating launcher..."

cat > "$LAUNCHER" << 'LAUNCHEOF'
#!/bin/bash
echo "Starting File Manager..."
pkill -9 -f file_manager_ui.py 2>/dev/null
lsof -ti:8765 | xargs kill -9 2>/dev/null
sleep 2
python3 ~/Desktop/FileSorter/file_manager_ui.py &
echo "Waiting for server..."
for i in $(seq 1 20); do
    sleep 1
    if curl -s http://localhost:8765 > /dev/null 2>&1; then
        echo "Server ready!"
        open http://localhost:8765
        wait
        exit 0
    fi
done
echo "Server did not start."
LAUNCHEOF

chmod +x "$LAUNCHER"
echo "  ✅ FileManager.command created on Desktop"

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║         ✅  Installation Complete!           ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
echo "  Files created:"
echo "    • ~/Desktop/FileSorter/file_manager.py"
echo "    • ~/Desktop/FileSorter/file_manager_ui.py"
echo "    • ~/Desktop/FileManager.command"
echo ""
echo "  To launch File Manager:"
echo "  Double-click FileManager.command on your Desktop"
echo ""
echo "  Launching now..."
sleep 2
"$LAUNCHER"
