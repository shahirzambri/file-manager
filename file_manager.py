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
