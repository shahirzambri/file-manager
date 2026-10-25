#!/usr/bin/env python3
"""
File Manager — Core Logic
Works on macOS and Windows.

STEP 1  Create folders   (only when matching files exist)
STEP 2  Sort files       (keyword, alias, fuzzy, plural-aware)
STEP 3  Sub-sort         (by dimensions, optional)
STEP 4  Compress         (JPG/WebP/GIF to KB limits, PNG kept as-is)

PLAN: plan_batch() works out what a run WOULD do to every file,
without touching anything. Real Run, Dry Run and the preview tree
all use the same plan, so they always agree.

TREE: preview_tree() and get_last_tree() give the UI the folder
structure for this batch. Live runs track every move, so the
"Completed" tree shows where files really ended up.

SMART SORT: detects identifiers in unrecognized filenames and
suggests them as folder names. The user confirms first.
"""

import re
import shutil
import json
from pathlib import Path
from io import BytesIO
from difflib import SequenceMatcher
from collections import Counter

try:
    from PIL import Image, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ══════════════════════════════════════════════════════════════
# SECTION 1 — FOLDER NAMES
# ══════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════
# SECTION 2 — ALIASES
# ══════════════════════════════════════════════════════════════
ALIASES = {
    "GDB": "GOOGLE DISCOVERY BANNER",
    "MAN": "MICROSOFT AUDIENCE NETWORK",
}

# ══════════════════════════════════════════════════════════════
# SECTION 3 — SIZE RULES (KB)
# ══════════════════════════════════════════════════════════════
SIZE_RULES = {
    "REDDIT IMAGE AD THUMBNAIL": 3072,
    "REDDIT IMAGE AD":           3072,
    "REDDIT CAROUSELL":          20480,
    "REDDIT CAROUSEL":           20480,
    "FOODPANDA IMAGE AD":        100,
    "GOOGLE UAC":                5120,
    "SHOPBACK":                  500,
    "LEMON8 COVER IMAGE":        500,
    "GRAB BRANDED VEH ICON":     450,
    "GRAB NATIVE IMAGE":         250,
    "GRAB HOME FEED":            250,
    "GRAB REWARD DETAIL PAGE":   250,
    "GOOGLE DISCOVERY BANNER":   5120,
    "CRITEO":                    5120,
    "YT COMP":                   100,
    "XIAO HONG SHU":             700,
}

# ══════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════
SIMILARITY_THRESHOLD = 0.90
CUSTOM_CONFIG_PATH   = Path(__file__).parent / "custom_config.json"
NUMBER_PATTERNS      = [r"\d+x\d+", r"\d+p\b", r"\d{3,}"]
SUPPORTED_FORMATS    = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# GIF compression: colour counts tried in order until the file fits
GIF_COLOR_STEPS = (256, 128, 64, 32, 16)

# Smart Sort: ignored when comparing filenames
NOISE_WORDS  = {"FINAL", "COPY", "NEW", "DRAFT", "EDIT",
                "REVISED", "UPDATED", "LATEST"}
DIMENSION_RE = re.compile(r"^\d{2,5}\s*[xX×]\s*\d{2,5}$")
COUNTRY_RE   = re.compile(r"^[A-Z]{2}$")

_last_skipped    = []
_last_recognized = []
_last_source     = None
_last_dry        = True
_last_tree       = None   # tree for the UI after a run (see get_last_tree)
_batch           = {}     # live runs: current relative path -> tree entry


# ──────────────────────────────────────────────────────────────
#  TEXT HELPERS
# ──────────────────────────────────────────────────────────────

def strip_ext(name):
    """Remove a real file extension only (.jpg, .png ...), not '.11 Sale'."""
    return re.sub(r"\.[A-Za-z0-9]{1,5}$", "", name)


def clean_text(text):
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.upper().strip()


def normalize(text):
    return clean_text(strip_ext(text))


def strip_plural_s(text):
    return " ".join(
        w[:-1] if len(w) > 2 and w.endswith("S") else w
        for w in text.split()
    )


def section_key(text):
    """Comparison key: uppercase, plural-stripped."""
    return strip_plural_s(clean_text(text))


def format_folder_name(name):
    """UPPERCASE, underscores to spaces, no illegal path characters."""
    n = re.sub(r'[\\/:*?"<>|]', " ", str(name)).replace("_", " ")
    return re.sub(r"\s+", " ", n).strip().upper()


def similarity_score(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def fuzzy_match(fname_norm, folder_norm):
    """Used for the built-in folder list."""
    if folder_norm in fname_norm:
        return True
    fs = strip_plural_s(fname_norm)
    fo = strip_plural_s(folder_norm)
    if fo in fs or folder_norm in fs or fo in fname_norm:
        return True
    fc  = re.sub(r"\b\d+[xX]\d+\b|\b\d+p\b|\b\d{3,}\b", "", fname_norm)
    fc  = re.sub(r"\s+", " ", fc).strip()
    fcs = strip_plural_s(fc)
    return max([
        similarity_score(fc,  folder_norm),
        similarity_score(fc,  fo),
        similarity_score(fcs, folder_norm),
        similarity_score(fcs, fo),
    ], default=0) >= SIMILARITY_THRESHOLD


def folders_similar(a, b):
    a, b    = normalize(a), normalize(b)
    as_, bs = strip_plural_s(a), strip_plural_s(b)
    if a == b or as_ == bs:
        return True
    return max([
        similarity_score(a,   b),
        similarity_score(as_, bs),
        similarity_score(a,   bs),
        similarity_score(as_, b),
    ], default=0) >= SIMILARITY_THRESHOLD


# ──────────────────────────────────────────────────────────────
#  SECTION HELPERS (Smart Sort)
# ──────────────────────────────────────────────────────────────

def is_noise_word(word):
    u = word.upper()
    return (bool(DIMENSION_RE.match(u))
            or bool(re.match(r"^\d{3,4}P$", u))
            or bool(re.match(r"^V\d+$", u))
            or u in NOISE_WORDS)


def split_sections(filename):
    """
    Split on '_' (or '-' if there are no underscores).
    Drops dimensions, noise words and bracketed text.
    'FW26 11.11 Sale_Paid Digital_SG_RAKUTEN_1200x1200.jpg'
      -> ['FW26 11.11 Sale', 'Paid Digital', 'SG', 'RAKUTEN']
    """
    stem = strip_ext(filename)
    if "_" in stem:
        parts = stem.split("_")
    elif "-" in stem:
        parts = stem.split("-")
    else:
        parts = [stem]
    out = []
    for p in parts:
        p = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", p)
        words = [w for w in p.split() if not is_noise_word(w)]
        s = " ".join(words).strip()
        if s:
            out.append(s)
    return out


def has_dimension(filename):
    return bool(re.search(r"\d{2,5}\s*[xX×]\s*\d{2,5}", strip_ext(filename)))


def section_match(filename, name):
    """
    Whole-section match for saved identifiers.
    'LINE' matches '..._LINE_...' but never '..._ONLINE_...'.
    """
    target = section_key(name)
    if not target:
        return False
    for s in split_sections(filename):
        if section_key(s) == target:
            return True
    if " " in target:
        full = strip_plural_s(normalize(filename))
        pattern = r"(?<![A-Z0-9])" + re.escape(target) + r"(?![A-Z0-9])"
        if re.search(pattern, full):
            return True
    return False


# ──────────────────────────────────────────────────────────────
#  CUSTOM CONFIG
# ──────────────────────────────────────────────────────────────

def load_custom_config():
    data = {"folders": [], "size_rules": {}, "aliases": {}}
    try:
        if CUSTOM_CONFIG_PATH.exists():
            with open(CUSTOM_CONFIG_PATH, "r") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                for k in data:
                    if k in loaded:
                        data[k] = loaded[k]
    except Exception:
        pass
    return data


def _write_config(config):
    with open(CUSTOM_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def save_to_custom_config(folder_name, max_kb=None):
    config = load_custom_config()
    if folder_name not in config["folders"]:
        config["folders"].append(folder_name)
    if max_kb and max_kb > 0:
        config["size_rules"][folder_name] = max_kb
    _write_config(config)


def save_alias(identifier, target):
    config = load_custom_config()
    config["aliases"][identifier] = target
    _write_config(config)


def get_all_folders():
    combined = list(FOLDERS)
    for f in load_custom_config()["folders"]:
        if f not in combined:
            combined.append(f)
    return combined


def get_effective_size_rules():
    combined = dict(SIZE_RULES)
    combined.update(load_custom_config()["size_rules"])
    return combined


def get_last_skipped():
    return list(_last_skipped)


def check_folder_exists(folder_name):
    for f in FOLDERS:
        if folders_similar(folder_name, f):
            return {"exists": True, "source": "builtin", "matched": f}
    for alias, folder in ALIASES.items():
        if folders_similar(folder_name, alias) or folders_similar(folder_name, folder):
            return {"exists": True, "source": "builtin", "matched": folder}
    config = load_custom_config()
    for f in config["folders"]:
        if folders_similar(folder_name, f):
            return {"exists": True, "source": "custom", "matched": f}
    for ident, target in config["aliases"].items():
        if folders_similar(folder_name, ident):
            return {"exists": True, "source": "custom", "matched": target}
    return {"exists": False, "source": "none", "matched": ""}


# ──────────────────────────────────────────────────────────────
#  GENERAL HELPERS
# ──────────────────────────────────────────────────────────────

def get_size_kb(path):
    return path.stat().st_size / 1024


def format_kb(kb):
    return f"{kb/1024:.2f} MB ({kb:.0f} KB)" if kb >= 1024 else f"{kb:.1f} KB"


def _limit_text(kb):
    return f"{kb/1024:.0f} MB" if kb >= 1024 else f"{kb} KB"


def _to_kb(value):
    try:
        n = int(str(value).strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _resolve_source(source_dir):
    """Clean up a pasted/dropped folder path (quotes, trailing slashes)."""
    return Path(str(source_dir).strip().strip("'\"")
                .rstrip("/").rstrip("\\")).resolve()


def _list_batch(source):
    """The files a run will sort: top level of the source, no hidden files."""
    return sorted([
        f for f in source.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ])


def resolve_conflict(dest):
    if not dest.exists():
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    c = 1
    while dest.exists():
        dest = parent / f"{stem}_{c}{suffix}"
        c += 1
    return dest


def print_divider(char="-", width=65):
    print(f"  {char * width}")


def print_header(title):
    print(f"\n{'='*67}\n  {title}\n{'='*67}")


# ──────────────────────────────────────────────────────────────
#  TREE TRACKING (for the UI's Folder Structure panel)
# ──────────────────────────────────────────────────────────────

def _rel(path, source):
    """Path relative to the source as 'A/B/file.jpg', or None."""
    try:
        return Path(path).relative_to(Path(source)).as_posix()
    except ValueError:
        return None


def _tree_entry(name, path, kb, pattern, status=None, limit_kb=None):
    return {
        "name":     name,       # filename as it is (or will be)
        "path":     path,       # 'FOLDER/SUB/file.jpg', or 'file.jpg' if unsorted
        "kb":       kb,
        "pattern":  pattern,    # size pattern, used by the live Smart Sort preview
        "status":   status,     # see the UI's noteFor() for all values
        "limit_kb": limit_kb,
        "orig_kb":  None,
        "new_kb":   None,
        "reason":   None,
    }


def _start_batch(plan):
    """Start tracking this batch's files for a live run."""
    global _batch
    _batch = {}
    for e in plan["files"]:
        _batch[e["file"]] = _tree_entry(e["file"], e["file"], e["kb"], e["pattern"])


def _move(src, dest, source):
    """shutil.move that also remembers where batch files end up."""
    shutil.move(str(src), str(dest))
    old, new = _rel(src, source), _rel(dest, source)
    entry = _batch.pop(old, None) if old else None
    if entry is not None and new:
        entry["path"] = new
        entry["name"] = Path(new).name
        _batch[new] = entry


def _record(file, source, status, **info):
    """Store a Step 4 result on the batch file at this location."""
    key   = _rel(file, source)
    entry = _batch.get(key) if key else None
    if entry is not None:
        entry["status"] = status
        entry.update(info)


def _live_tree(subsort):
    return {"mode": "done", "subsort": bool(subsort),
            "files": [dict(e) for e in _batch.values()]}


def _plan_tree(plan, mode):
    files = []
    for e in plan["files"]:
        t = _tree_entry(e["file"], e["dest"], e["kb"], e["pattern"],
                        e["action"], e["limit_kb"])
        if mode == "dry" and e["file"] in _dry_results:
            t.update(_dry_results[e["file"]])
        files.append(t)
    return {"mode": mode, "subsort": plan["subsort"], "files": files}


def get_last_tree():
    """Tree from the last run: mode 'dry' or 'done'. None if no run yet."""
    return _last_tree


# ──────────────────────────────────────────────────────────────
#  STEP 1 + 2 — SORT
# ──────────────────────────────────────────────────────────────

def find_target_folder(filename):
    name_norm = normalize(filename)

    # 1. Built-in aliases (GDB, MAN)
    for alias, folder in ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", name_norm):
            return folder

    # 2. Built-in folders (fuzzy, longest first)
    for folder in sorted(FOLDERS, key=len, reverse=True):
        if fuzzy_match(name_norm, normalize(folder)):
            return folder

    # 3. Saved identifiers (whole-section match only)
    config = load_custom_config()
    for ident, target in sorted(config["aliases"].items(),
                                key=lambda x: len(x[0]), reverse=True):
        if section_match(filename, ident):
            return target
    for folder in sorted(config["folders"], key=len, reverse=True):
        if section_match(filename, folder):
            return folder

    return None


def run_sort(source, dry_run, plan=None):
    global _last_skipped, _last_source, _last_recognized

    if plan is None:
        plan = plan_batch(source, subsort=False)
    entries = plan["files"]

    if not entries:
        print("  No files found.")
        _last_skipped, _last_recognized, _last_source = [], [], source
        return {"moved": [], "skipped": []}

    needed_folders = set(plan["folders"])

    print_header("STEP 1 -- Auto-Create Folders")
    print(f"  Files scanned : {len(entries)}")
    print(f"  Folders needed: {len(needed_folders)}\n")
    for folder in sorted(needed_folders):
        fp = source / folder
        if not fp.exists():
            print(f"  {'[DRY RUN]' if dry_run else 'Created  '} | {folder}/")
            if not dry_run:
                fp.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  Exists    | {folder}/")

    print_header("STEP 2 -- Sort Files into Folders")
    print(f"  Files    : {len(entries)}")
    print(f"  Matching : case-insensitive, plural-aware, "
          f"{int(SIMILARITY_THRESHOLD*100)}% fuzzy\n")

    results = {"moved": [], "skipped": []}
    for e in entries:
        file = source / e["file"]
        tf   = e["folder"]
        if tf:
            dest = resolve_conflict(source / tf / file.name)
            print(f"  {'[DRY RUN]' if dry_run else 'Moved    '} | {file.name}")
            print(f"            | -> {tf}/\n")
            if not dry_run:
                _move(file, dest, source)
            results["moved"].append({"file": file.name, "folder": tf})
        else:
            print(f"  No Match  | {file.name}\n")
            results["skipped"].append(file.name)

    _last_skipped    = list(results["skipped"])
    _last_recognized = [e["file"] for e in results["moved"]]
    _last_source     = source

    print_divider()
    print(f"  Moved   : {len(results['moved'])} file(s)")
    print(f"  Skipped : {len(results['skipped'])} file(s)")
    print(f"{'='*67}\n")
    return results


# ──────────────────────────────────────────────────────────────
#  SMART SORT — Detect identifiers
# ──────────────────────────────────────────────────────────────

def _varying_positions(all_secs, length):
    """Positions whose values differ between files (country codes skipped)."""
    out = []
    for i in range(length):
        vals = [s[i] for s in all_secs]
        distinct = len({section_key(v) for v in vals})
        if distinct <= 1:
            continue
        if all(COUNTRY_RE.match(clean_text(v)) for v in vals):
            continue
        out.append((distinct, i))
    return out


def _build_pattern(sample, idx, varying, dims):
    parts = []
    for j, s in enumerate(sample):
        if j == idx:
            parts.append("[IDENTIFIER]")
        elif j in varying:
            parts.append("[VARIES]")
        else:
            parts.append(s)
    if dims:
        parts.append("[DIMENSIONS]")
    return "_".join(parts)


def _suggest_folder(name):
    key = section_key(name)
    for alias, folder in ALIASES.items():
        if section_key(alias) == key:
            return folder
    for ident, target in load_custom_config()["aliases"].items():
        if section_key(ident) == key:
            return target
    for f in get_all_folders():
        if folders_similar(name, f):
            return f
    return ""


def _build_rows(items, idx):
    """One row per identifier. Case/plural variants merge into one row."""
    buckets, order = {}, []
    for f, secs in items:
        val = secs[idx]
        k = section_key(val)
        if k not in buckets:
            buckets[k] = {"variants": Counter(), "files": []}
            order.append(k)
        buckets[k]["variants"][format_folder_name(val)] += 1
        buckets[k]["files"].append(f)
    rows = []
    for k in order:
        b = buckets[k]
        name = min(b["variants"], key=lambda v: (len(v), v))
        rows.append({
            "name":    name,
            "files":   b["files"],
            "suggest": _suggest_folder(name),
            "short":   len(re.sub(r"[^A-Z0-9]", "", name)) < 3,
        })
    return rows


def detect_identifiers():
    undetected = []

    # Group by number of sections
    by_len = {}
    for f in _last_skipped:
        secs = split_sections(f)
        if secs:
            by_len.setdefault(len(secs), []).append((f, secs))
        else:
            undetected.append(f)

    # Split into campaigns only when the prefix AND another section differ
    groups = []
    for length, items in by_len.items():
        vidx = {i for _, i in _varying_positions([s for _, s in items], length)}
        if 0 in vidx and len(vidx) >= 2:
            split = {}
            for it in items:
                split.setdefault(section_key(it[1][0]), []).append(it)
            groups.extend(split.values())
        else:
            groups.append(items)

    # Recognized files give extra context
    context = [s for s in (split_sections(f) for f in _last_recognized) if s]

    result = []
    for items in groups:
        length     = len(items[0][1])
        first_key  = section_key(items[0][1][0])
        same_first = all(section_key(s[0]) == first_key for _, s in items)
        ctx = [s for s in context
               if len(s) == length
               and (not same_first or section_key(s[0]) == first_key)]
        all_secs = [s for _, s in items] + ctx

        if length == 1:
            varying, chosen, low = set(), 0, False
        elif len(all_secs) < 2:
            undetected.extend(f for f, _ in items)
            continue
        else:
            vp = _varying_positions(all_secs, length)
            varying = {i for _, i in vp}
            if vp:
                chosen, low = max(vp)[1], False
            else:
                chosen, low = length - 1, True   # differ only by dimension

        dims   = any(has_dimension(f) for f, _ in items)
        sample = items[0][1]
        positions = [{
            "index":   i,
            "label":   f"Section {i + 1}: {sample[i]}",
            "pattern": _build_pattern(sample, i, varying, dims),
            "rows":    _build_rows(items, i),
        } for i in range(length)]

        result.append({
            "id":             len(result),
            "chosen":         chosen,
            "low_confidence": low,
            "file_count":     len(items),
            "positions":      positions,
        })

    return {
        "dry":        _last_dry,
        "groups":     result,
        "undetected": undetected,
        "folders":    get_all_folders(),
    }


def apply_identifiers(items, subsort=True):
    """
    items: [{name, map_to, max_kb, files}]
    Creates folders, moves files, saves identifiers/aliases,
    then sub-sorts and compresses only the newly sorted files.
    """
    global _last_skipped, _last_tree

    if not _last_source or not Path(_last_source).exists():
        print("\n  Error: No source folder. Run File Manager first.\n")
        return {"error": "No source folder"}
    if _last_dry:
        print("\n  Dry Run is ON -- nothing was applied.\n")
        return {"error": "Dry run"}

    source  = Path(_last_source)
    pending = set(_last_skipped)
    entries, final_names, targets = [], set(), set()

    print_header("SMART SORT -- Applying Detected Identifiers")

    for item in items:
        ident  = format_folder_name(item.get("name", ""))
        map_to = (item.get("map_to") or "").strip()
        max_kb = _to_kb(item.get("max_kb"))
        files  = [f for f in item.get("files", []) if f in pending]
        if not files or (not ident and not map_to):
            continue

        target = map_to or ident
        fp = source / target
        fp.mkdir(parents=True, exist_ok=True)
        print(f"\n  {target}/  ({len(files)} file(s))")

        for f in files:
            src = source / f
            if not src.exists():
                continue
            dest = resolve_conflict(fp / f)
            _move(src, dest, source)
            pending.discard(f)
            entries.append({"file": dest.name, "folder": target})
            final_names.add(dest.name)
            targets.add(target)
            print(f"    Moved | {f}")

        if map_to:
            if ident and section_key(ident) != section_key(map_to):
                save_alias(ident, map_to)
                print(f"    Saved alias: {ident} -> {map_to}")
        else:
            save_to_custom_config(ident, max_kb)
            limit = _limit_text(max_kb) if max_kb else "no limit"
            print(f"    Saved folder: {ident} ({limit})")

    _last_skipped = [f for f in _last_skipped if f in pending]

    if entries:
        if subsort:
            run_subsort(source, entries, False)
        if PIL_AVAILABLE:
            run_reducer(source, False, only_folders=targets, only_names=final_names)

    _last_tree = _live_tree(subsort)

    print_divider()
    print(f"  Sorted        : {len(entries)} file(s)")
    print(f"  Still unsorted: {len(_last_skipped)} file(s)")
    print(f"{'='*67}\n")
    return {"moved": len(entries), "still_skipped": list(_last_skipped)}


# ──────────────────────────────────────────────────────────────
#  CUSTOM FOLDER (manual fallback)
# ──────────────────────────────────────────────────────────────

def create_custom_folder(folder_name, max_kb=None, dry_run=None, subsort=True):
    global _last_skipped, _last_tree

    if dry_run is None:
        dry_run = _last_dry
    if not _last_source or not Path(_last_source).exists():
        return {"error": "No source folder. Run File Manager first."}

    source      = Path(_last_source)
    folder_name = format_folder_name(folder_name)
    max_kb      = _to_kb(max_kb)
    if not folder_name:
        return {"error": "Folder name is empty."}

    name_norm = normalize(folder_name)
    matched, still = [], []
    for fname in _last_skipped:
        (matched if fuzzy_match(normalize(fname), name_norm) else still).append(fname)

    if not matched:
        return {"error": f"No unsorted files contain '{folder_name}'",
                "still_skipped": still}

    print_header(f"Custom Folder -- {folder_name}/")
    print(f"  Max size : {_limit_text(max_kb) if max_kb else 'No limit'}")
    print(f"  Matched  : {len(matched)}\n")

    if dry_run:
        for f in matched:
            print(f"  [DRY RUN] | {f} -> {folder_name}/")
        print("\n  Dry Run is ON -- nothing was moved or saved.")
        print(f"{'='*67}\n")
        return {"moved": 0, "files": matched, "folder": folder_name, "dry_run": True}

    save_to_custom_config(folder_name, max_kb)
    fp = source / folder_name
    fp.mkdir(parents=True, exist_ok=True)

    entries, names = [], set()
    for f in matched:
        src = source / f
        if src.exists():
            dest = resolve_conflict(fp / f)
            _move(src, dest, source)
            entries.append({"file": dest.name, "folder": folder_name})
            names.add(dest.name)
            print(f"  Moved     | {f}")

    _last_skipped = still
    print(f"\n  Saved -- {folder_name} will be remembered for future runs.")
    print(f"{'='*67}\n")

    if entries:
        if subsort:
            run_subsort(source, entries, False)
        if PIL_AVAILABLE:
            run_reducer(source, False, only_folders={folder_name}, only_names=names)

    _last_tree = _live_tree(subsort)

    return {"moved": len(entries), "files": [e["file"] for e in entries],
            "folder": folder_name, "max_kb": max_kb, "still_skipped": still}


# ──────────────────────────────────────────────────────────────
#  STEP 3 — SUB-SORT
# ──────────────────────────────────────────────────────────────

def extract_number_pattern(filename, file_path=None):
    nc = strip_ext(filename)
    for p in NUMBER_PATTERNS:
        m = re.search(p, nc, re.IGNORECASE)
        if m:
            return m.group()
    if file_path and PIL_AVAILABLE:
        try:
            if Path(file_path).suffix.lower() in SUPPORTED_FORMATS:
                img  = Image.open(file_path)
                w, h = img.size
                img.close()
                return f"{w}x{h}"
        except Exception:
            pass
    return None


def run_subsort(source, moved_files, dry_run, patterns=None):
    """
    patterns: optional {filename: pattern} from plan_batch. When given,
    the planned patterns are used, so Dry Run and Real Run agree.
    """
    if not moved_files:
        print("\n  No files sorted -- skipping sub-sort.\n")
        return

    fm = {}
    for e in moved_files:
        fm.setdefault(e["folder"], []).append(e["file"])

    print_header("STEP 3 -- Dimension Sub-folder Sort")
    print("  Rule: Only sub-sorts if 2+ different patterns exist\n")

    tm = ts = tn = 0
    for fn, fnames in sorted(fm.items()):
        fp = source / fn
        print(f"  {fn}/  --  {len(fnames)} file(s)")
        print_divider()

        pm = {}
        for f in fnames:
            if patterns is not None and f in patterns:
                pm[f] = patterns[f]
            else:
                pm[f] = extract_number_pattern(f, fp / f)
        up = set(p for p in pm.values() if p)

        if len(up) <= 1:
            r = "no pattern" if not up else f"only 1 pattern '{next(iter(up))}'"
            print(f"  Skipped -- {r}")
            print(f"  {len(fnames)} file(s) stay in {fn}/\n")
            ts += len(fnames)
            continue

        print(f"  {len(up)} patterns ({', '.join(sorted(up))}) -> sub-sorting\n")
        for f in fnames:
            p = pm[f]
            if p:
                sf   = fp / p
                dest = resolve_conflict(sf / f)
                print(f"  {'[DRY RUN]' if dry_run else 'Moved    '} | {f}")
                print(f"            | -> {fn}/{p}/\n")
                if not dry_run:
                    sf.mkdir(parents=True, exist_ok=True)
                    _move(fp / f, dest, source)
                tm += 1
            else:
                print(f"  No pattern | {f}\n")
                tn += 1

    print_divider()
    print(f"  Sub-Moved   : {tm}")
    print(f"  Single/None : {ts}")
    print(f"  No Pattern  : {tn}")
    print(f"{'='*67}\n")


# ──────────────────────────────────────────────────────────────
#  STEP 4 — REDUCE
# ──────────────────────────────────────────────────────────────

def find_size_rule(file_path, source):
    all_rules = get_effective_size_rules()

    # 1. The folder the file sits in (exact match, most reliable)
    try:
        parts = file_path.relative_to(source).parts[:-1]
    except ValueError:
        parts = ()
    for part in parts:
        pk = section_key(part)
        for kw, mb in all_rules.items():
            if section_key(kw) == pk:
                return kw, mb

    # 2. Built-in rules by filename, alias, then parent folder (fuzzy)
    builtin = sorted(SIZE_RULES.items(), key=lambda x: len(x[0]), reverse=True)
    nn = normalize(file_path.name)
    for kw, mb in builtin:
        if fuzzy_match(nn, normalize(kw)):
            return kw, mb
    for alias, folder in ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", nn):
            for kw, mb in builtin:
                if fuzzy_match(normalize(folder), normalize(kw)):
                    return kw, mb
    for part in parts:
        for kw, mb in builtin:
            if fuzzy_match(normalize(part), normalize(kw)):
                return kw, mb

    return None, None


def _compression_plan(rule_path, source, ckb):
    """
    Decide what Step 4 will do with one file. Read-only.
    rule_path: where the file is (or WILL be) inside the source.
    action: 'not_image' | 'png' | 'no_rule' | 'ok' | 'compress'
    """
    ext = rule_path.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        return {"action": "not_image", "rule": None, "limit_kb": None}
    if ext == ".png":
        return {"action": "png", "rule": None, "limit_kb": None}
    kw, mb = find_size_rule(rule_path, source)
    if not kw:
        return {"action": "no_rule", "rule": None, "limit_kb": None}
    if ckb <= mb:
        return {"action": "ok", "rule": kw, "limit_kb": mb}
    return {"action": "compress", "rule": kw, "limit_kb": mb}


def compress_jpg(img, tkb):
    lo, hi, best = 1, 95, None
    for _ in range(20):
        m   = (lo + hi) // 2
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=m, optimize=True)
        d = buf.getvalue()
        if len(d) / 1024 <= tkb:
            best, lo = d, m + 1
        else:
            hi = m - 1
    if best is None:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=1, optimize=True)
        best = buf.getvalue()
    return best


def compress_webp(img, tkb):
    lo, hi, best = 1, 95, None
    for _ in range(20):
        m   = (lo + hi) // 2
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=m)
        d = buf.getvalue()
        if len(d) / 1024 <= tkb:
            best, lo = d, m + 1
        else:
            hi = m - 1
    if best is None:
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=1)
        best = buf.getvalue()
    return best


def _has_transparency(rgba_frames):
    """True if any frame has at least one non-opaque pixel."""
    for fr in rgba_frames:
        if fr.getchannel("A").getextrema()[0] < 255:
            return True
    return False


def compress_gif(img, tkb):
    """
    Compress a GIF (animated or still) towards tkb KB.
    Keeps every frame, each frame's timing, and the original loop
    setting. Never changes dimensions. Returns the smallest result
    found; compress_image decides whether it is worth saving.
    """
    loop = img.info.get("loop")          # None = original plays once
    frames, durations = [], []
    for frame in ImageSequence.Iterator(img):
        frames.append(frame.convert("RGBA"))
        durations.append(frame.info.get("duration", img.info.get("duration", 100)))
    try:
        img.seek(0)
    except EOFError:
        pass

    # Opaque GIFs compress more cleanly as plain RGB
    if not _has_transparency(frames):
        frames = [fr.convert("RGB") for fr in frames]

    save_kw = {
        "format":   "GIF",
        "save_all": True,
        "duration": durations,
        "optimize": True,
        "disposal": 2,
    }
    if loop is not None:
        save_kw["loop"] = loop

    best = None
    for colors in GIF_COLOR_STEPS:
        # method=2 (fast octree) works with RGB and RGBA on all Pillow versions
        q = [fr.quantize(colors=colors, method=2) for fr in frames]
        buf = BytesIO()
        q[0].save(buf, append_images=q[1:], **save_kw)
        data = buf.getvalue()
        if best is None or len(data) < len(best):
            best = data
        if len(data) / 1024 <= tkb:
            return data
    return best


def compress_to_bytes(fp, tkb):
    """
    Compress in memory only. NEVER writes to disk, so it is safe
    for Dry Run. Returns (data, dimensions). Raises on error.
    """
    ext = fp.suffix.lower()
    with Image.open(fp) as src:
        src.load()
        img  = src
        dims = img.size
        if ext in (".jpg", ".jpeg"):
            if img.mode in ("RGBA", "LA", "P"):
                bg   = Image.new("RGB", img.size, (255, 255, 255))
                img  = img.convert("RGBA") if img.mode == "P" else img
                mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
                bg.paste(img, mask=mask)
                img  = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            data = compress_jpg(img, tkb)
        elif ext == ".webp":
            data = compress_webp(img, tkb)
        elif ext == ".gif":
            data = compress_gif(img, tkb)
        else:
            raise ValueError(f"Unsupported '{ext}'")
    return data, dims


def compress_image(fp, tkb):
    """
    Compress fp towards tkb KB and save it, but only if the result
    is actually smaller than the original. Otherwise the original
    is left untouched.
    """
    ext = fp.suffix.lower()
    okb = get_size_kb(fp)
    if ext == ".png":
        return {"success": False, "png_skip": True, "reason": "PNG kept as-is"}
    try:
        data, dims = compress_to_bytes(fp, tkb)
    except Exception as e:
        return {"success": False, "png_skip": False, "reason": str(e)}

    nkb = len(data) / 1024
    if nkb >= okb:
        return {"success": False, "png_skip": False, "unchanged": True,
                "original_kb": okb, "best_kb": nkb,
                "reason": "Could not make it smaller -- original kept"}
    try:
        with open(fp, "wb") as f:
            f.write(data)
    except Exception as e:
        return {"success": False, "png_skip": False, "reason": str(e)}

    return {"success": True, "original_kb": okb, "new_kb": nkb,
            "saved_pct": ((okb - nkb) / okb) * 100 if okb else 0,
            "under_target": nkb <= tkb, "dimensions": dims}


_dry_results = {}   # Dry Run: filename -> exact compression result


def _dry_compress(fp, tkb, okb):
    """
    Dry Run: compress in memory exactly like the real run would,
    but never write. Same decisions as compress_image.
    """
    try:
        data, _ = compress_to_bytes(fp, tkb)
    except Exception as e:
        return {"status": "will_fail", "limit_kb": tkb, "reason": str(e)}
    nkb  = len(data) / 1024
    base = {"limit_kb": tkb, "orig_kb": round(okb, 1), "new_kb": round(nkb, 1)}
    if nkb >= okb:
        return dict(base, status="will_keep", new_kb=None)
    if nkb <= tkb:
        return dict(base, status="will_compress")
    return dict(base, status="will_over")


def run_reducer(source, dry_run, only_folders=None, only_names=None, plan=None):
    """
    plan: optional result of plan_batch. In Dry Run, files have not
    moved yet, so their size rule is looked up at their PLANNED
    location. That makes Dry Run match what the real run will do.
    Live runs record each result for the Completed tree.
    """
    if only_folders:
        files = []
        for t in only_folders:
            folder = source / t
            if folder.exists():
                files += [f for f in folder.rglob("*")
                          if f.is_file() and not f.name.startswith(".")
                          and f.suffix.lower() in SUPPORTED_FORMATS]
        if only_names:
            files = [f for f in files if f.name in only_names]
        files = sorted(files)
    else:
        files = sorted([
            f for f in source.rglob("*")
            if f.is_file() and not f.name.startswith(".")
            and f.suffix.lower() in SUPPORTED_FORMATS
        ])

    redirect = {}
    if plan and dry_run:
        for e in plan["files"]:
            if e["folder"]:
                redirect[source / e["file"]] = source / e["dest"]

    live   = not dry_run
    counts = {k: 0 for k in ["compressed", "over_limit", "already_ok",
                             "untouched", "skipped_png", "failed"]}

    print_header("STEP 4 -- File Size Reduction  (PNG kept as-is)")
    print(f"  Files : {len(files)}\n")

    decisions = []
    for file in files:
        ckb = get_size_kb(file)
        decisions.append((file, ckb,
                          _compression_plan(redirect.get(file, file), source, ckb)))
    to_check = sum(1 for _, _, d in decisions if d["action"] == "compress")
    checked  = 0

    for file, ckb, d in decisions:

        if d["action"] == "png":
            print(f"  PNG      | {file.name} -- {format_kb(ckb)}\n")
            counts["skipped_png"] += 1
            if live:
                _record(file, source, "png")
            continue

        if d["action"] in ("no_rule", "not_image"):
            print(f"  No Rule  | {file.name} -- {format_kb(ckb)}\n")
            counts["untouched"] += 1
            if live:
                _record(file, source, "no_rule")
            continue

        kw, mb = d["rule"], d["limit_kb"]
        lim = _limit_text(mb)
        if d["action"] == "ok":
            print(f"  OK       | {file.name} -- {format_kb(ckb)} <= {lim}\n")
            counts["already_ok"] += 1
            if live:
                _record(file, source, "ok", limit_kb=mb)
            continue

        print(f"  Compress | {file.name}")
        print(f"           | Rule: {kw} -> {lim}  |  Current: {format_kb(ckb)}")
        if dry_run:
            checked += 1
            print(f"           | [DRY RUN] Checking {checked}/{to_check}...")
            r = _dry_compress(file, mb, ckb)
            _dry_results[_rel(file, source) or file.name] = r
            if r["status"] == "will_compress":
                print(f"           | Will be {format_kb(ckb)} -> "
                      f"{format_kb(r['new_kb'])}  Target met\n")
                counts["compressed"] += 1
            elif r["status"] == "will_over":
                print(f"           | Will be {format_kb(ckb)} -> {format_kb(r['new_kb'])}")
                print(f"           | OVER LIMIT: will not reach {lim}\n")
                counts["over_limit"] += 1
            elif r["status"] == "will_keep":
                print("           | OVER LIMIT: cannot make it smaller -- "
                      "original will be kept\n")
                counts["over_limit"] += 1
            else:
                print(f"           | WILL FAIL: {r['reason']}\n")
                counts["failed"] += 1
            continue

        r = compress_image(file, mb)
        if r["success"]:
            okb, nkb = round(r["original_kb"], 1), round(r["new_kb"], 1)
            status = "compressed" if r["under_target"] else "over_limit"
            _record(file, source, status, limit_kb=mb,
                    orig_kb=okb, new_kb=nkb, kb=nkb)
        if r["success"] and r["under_target"]:
            print(f"           | {format_kb(r['original_kb'])} -> "
                  f"{format_kb(r['new_kb'])} ({r['saved_pct']:.1f}% saved) Target met\n")
            counts["compressed"] += 1
        elif r["success"]:
            print(f"           | {format_kb(r['original_kb'])} -> "
                  f"{format_kb(r['new_kb'])} ({r['saved_pct']:.1f}% saved)")
            print(f"           | OVER LIMIT: could not reach {lim}\n")
            counts["over_limit"] += 1
        elif r.get("unchanged"):
            print(f"           | OVER LIMIT: could not make it smaller -- "
                  f"original kept ({format_kb(ckb)})\n")
            counts["over_limit"] += 1
            _record(file, source, "kept", limit_kb=mb, orig_kb=round(ckb, 1))
        else:
            print(f"           | FAILED: {r['reason']}\n")
            counts["failed"] += 1
            _record(file, source, "failed", limit_kb=mb, reason=r["reason"])

    print_divider()
    for k, v in counts.items():
        print(f"  {k:<12}: {v}")
    print(f"{'='*67}\n")


# ──────────────────────────────────────────────────────────────
#  PLAN — what a run WOULD do (read-only)
# ──────────────────────────────────────────────────────────────

def plan_batch(source, subsort=True):
    """
    Work out what a run would do to every file in the source folder.
    READ-ONLY: never moves, creates, writes, or changes app state.
    Real Run, Dry Run and the preview tree all use this.

    Returns:
      {
        "source":   str,
        "subsort":  bool,
        "files": [{
            "file":     "PMAX_1200x1200_V1.jpg",
            "folder":   "PMAX" or None (unsorted),
            "pattern":  "1200x1200" or None (size found; set for every
                        file when sub-sort is on, so the live Smart Sort
                        preview can sub-sort unsorted files too),
            "sub":      "1200x1200" or None (actual size sub-folder),
            "dest":     "PMAX/1200x1200/PMAX_1200x1200_V1.jpg",
            "kb":       412.3,
            "action":   "compress" | "ok" | "png" | "no_rule" | "not_image",
            "rule":     "YT COMP" or None,
            "limit_kb": 100 or None,
        }, ...],
        "folders":  ["PMAX", ...],
        "unsorted": ["mystery.jpg", ...],
      }
    """
    source = Path(source)
    entries = []
    for f in _list_batch(source):
        entries.append({
            "file":    f.name,
            "folder":  find_target_folder(f.name),
            "pattern": None,
            "sub":     None,
            "_kb":     get_size_kb(f),
        })

    # Step 3 rule: sub-sort a folder only if 2+ different patterns exist
    if subsort:
        by_folder = {}
        for e in entries:
            e["pattern"] = extract_number_pattern(e["file"], source / e["file"])
            if e["folder"]:
                by_folder.setdefault(e["folder"], []).append(e)
        for items in by_folder.values():
            if len({e["pattern"] for e in items if e["pattern"]}) > 1:
                for e in items:
                    e["sub"] = e["pattern"]

    # Step 4 decision, judged at the file's planned location
    for e in entries:
        parts = [p for p in (e["folder"], e["sub"]) if p]
        e["dest"] = "/".join(parts + [e["file"]])
        ckb = e.pop("_kb")
        e["kb"] = round(ckb, 1)
        e.update(_compression_plan(source.joinpath(*parts, e["file"]), source, ckb))

    return {
        "source":   str(source),
        "subsort":  bool(subsort),
        "files":    entries,
        "folders":  sorted({e["folder"] for e in entries if e["folder"]}),
        "unsorted": [e["file"] for e in entries if not e["folder"]],
    }


def preview(source_dir, subsort=True):
    """Plan for a folder. Read-only: changes no files and no state."""
    source = _resolve_source(source_dir)
    if not source.is_dir():
        raise FileNotFoundError(f"Folder not found: '{source}'")
    return plan_batch(source, subsort)


def preview_tree(source_dir, subsort=True):
    """Preview in the UI tree's format. Read-only."""
    return _plan_tree(preview(source_dir, subsort), "preview")


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────

def run_all(source_dir, dry_run=False, subsort=True):
    global _last_dry, _last_tree, _batch, _dry_results

    _last_tree   = None
    _dry_results = {}
    source = _resolve_source(source_dir)
    if not source.exists():
        raise FileNotFoundError(f"Folder not found: '{source}'")

    _last_dry = dry_run

    print(f"\n{'#'*67}")
    print(f"  FILE MANAGER  {'-- DRY RUN' if dry_run else ''}")
    print(f"{'#'*67}")
    print(f"  Source   : {source}")
    print(f"  Sub-sort : {'ON' if subsort else 'OFF'}")
    print(f"{'#'*67}")

    plan = plan_batch(source, subsort=subsort)
    if dry_run:
        _batch = {}
    else:
        _start_batch(plan)

    sr = run_sort(source, dry_run, plan)

    if subsort:
        patterns = {e["file"]: e["pattern"] for e in plan["files"] if e["folder"]}
        run_subsort(source, sr["moved"], dry_run, patterns=patterns)
    else:
        print_header("STEP 3 -- Dimension Sub-folder Sort")
        print(f"  Skipped by user choice.\n{'='*67}\n")

    if PIL_AVAILABLE:
        run_reducer(source, dry_run, plan=plan)
    else:
        print("\n  Pillow not installed -- Step 4 skipped.\n")

    _last_tree = _plan_tree(plan, "dry") if dry_run else _live_tree(subsort)

    print(f"{'#'*67}")
    print("  ALL STEPS COMPLETE!")
    if dry_run:
        print("  DRY RUN -- no files were changed.")
    if _last_skipped:
        print(f"  {len(_last_skipped)} unrecognized file(s) -- see Smart Sort panel.")
    print(f"{'#'*67}\n")


# ──────────────────────────────────────────────────────────────
#  SMART SORT — Save identifiers before a live run
# ──────────────────────────────────────────────────────────────

def save_identifiers(items):
    """
    Save confirmed identifiers WITHOUT moving files.
    Used when the user confirms from a Dry Run preview: the
    identifiers are saved, then a normal live run sorts everything.
    If a name was edited, the detected name is saved as an alias
    so files still match it.
    """
    saved = []
    for item in items:
        ident  = format_folder_name(item.get("name", ""))
        orig   = format_folder_name(item.get("detected") or ident)
        map_to = (item.get("map_to") or "").strip()
        max_kb = _to_kb(item.get("max_kb"))
        if map_to:
            for alias in {ident, orig}:
                if alias and section_key(alias) != section_key(map_to):
                    save_alias(alias, map_to)
            saved.append(f"{orig} -> {map_to}")
        elif ident:
            save_to_custom_config(ident, max_kb)
            if orig and section_key(orig) != section_key(ident):
                save_alias(orig, ident)
            saved.append(ident)
    return saved