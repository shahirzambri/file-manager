#!/usr/bin/env python3
"""
File Manager — Desktop App (PyWebView)
Apple-style frosted glass UI with Smart Sort panel.
Works on macOS and Windows.
"""

import signal as _sig
try:
    _sig.signal(_sig.SIGHUP, _sig.SIG_IGN)
except Exception:
    pass

import http.server
import socketserver
import threading
import json
import sys
import os
import signal
import socket
import time
import subprocess
from pathlib import Path
from urllib.parse import unquote_plus, urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).parent))
try:
    from file_manager import (
        run_all, PIL_AVAILABLE,
        get_last_skipped, create_custom_folder, check_folder_exists,
        detect_identifiers, apply_identifiers, save_identifiers,
    )
    MANAGER_OK = True
except ImportError as _e:
    MANAGER_OK    = False
    PIL_AVAILABLE = False
    print("Import error:", _e)

try:
    import webview
    WEBVIEW_OK = True
except ImportError:
    WEBVIEW_OK = False

PORT  = 8765
_log  = []
_busy = False
_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────
#  PORT HELPERS
# ──────────────────────────────────────────────────────────────

def free_port(port):
    try:
        if sys.platform == "win32":
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if parts:
                        subprocess.run(["taskkill", "/F", "/PID", parts[-1]],
                                       capture_output=True)
        else:
            result = subprocess.run(["lsof", "-ti", ":" + str(port)],
                                    capture_output=True, text=True)
            for pid in result.stdout.strip().splitlines():
                try:
                    os.kill(int(pid.strip()), signal.SIGKILL)
                except Exception:
                    pass
        time.sleep(1.0)
    except Exception:
        pass


def port_free(port):
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=1)
        s.close()
        return False
    except Exception:
        return True


def wait_for_server(port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1)
            s.close()
            return True
        except Exception:
            time.sleep(0.3)
    return False


# ──────────────────────────────────────────────────────────────
#  OUTPUT CAPTURE + SERVER
# ──────────────────────────────────────────────────────────────

class Cap:
    def write(self, t):
        with _lock:
            _log.append(str(t))
    def flush(self):
        pass


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads      = True


def _set_busy(value, reset_log=False):
    global _busy, _log
    with _lock:
        _busy = value
        if reset_log:
            _log = []


class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        p = self.path.split("?")[0]
        if   p == "/":             self.serve_page()
        elif p == "/poll":         self.serve_poll()
        elif p == "/browse":       self.serve_browse()
        elif p == "/skipped":      self.serve_skipped()
        elif p == "/check-folder": self.serve_check_folder()
        elif p == "/detect":       self.serve_detect()
        else:                      self.send_error(404)

    def do_POST(self):
        if   self.path == "/run":               self.handle_run()
        elif self.path == "/add-folder":        self.handle_add_folder()
        elif self.path == "/apply-identifiers": self.handle_apply()
        elif self.path == "/save-and-run":      self.handle_save_run()
        else:                                   self.send_error(404)

    # ── GET ──────────────────────────────────────────────────

    def serve_page(self):
        m = ("file_manager.py loaded OK" if MANAGER_OK
             else "ERROR: file_manager.py not found or outdated!")
        p = ("Pillow installed - compression enabled" if PIL_AVAILABLE
             else "Pillow NOT installed. Fix: pip3 install Pillow")
        page = HTML.replace("__M__", m).replace("__P__", p)
        self.respond(200, "text/html; charset=utf-8", page.encode("utf-8"))

    def serve_poll(self):
        with _lock:
            d = {"busy": _busy, "log": "".join(_log)}
        self.respond(200, "application/json", json.dumps(d).encode())

    def serve_skipped(self):
        files = get_last_skipped() if MANAGER_OK else []
        self.respond(200, "application/json", json.dumps({"files": files}).encode())

    def serve_check_folder(self):
        qs   = parse_qs(urlparse(self.path).query)
        name = qs.get("name", [""])[0].strip()
        r    = (check_folder_exists(name) if MANAGER_OK and name
                else {"exists": False, "source": "none", "matched": ""})
        self.respond(200, "application/json", json.dumps(r).encode())

    def serve_detect(self):
        empty = {"dry": True, "groups": [], "undetected": [], "folders": []}
        try:
            d = detect_identifiers() if MANAGER_OK else empty
        except Exception as e:
            d = dict(empty, error=str(e))
        self.respond(200, "application/json", json.dumps(d).encode())

    def serve_browse(self):
        path = ""
        try:
            if WEBVIEW_OK and webview.windows:
                result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
                if result and len(result) > 0:
                    path = result[0]
            elif sys.platform == "win32":
                ps = ("Add-Type -AssemblyName System.Windows.Forms; "
                      "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                      "if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath }")
                r = subprocess.run(["powershell", "-Command", ps],
                                   capture_output=True, text=True, timeout=120)
                path = r.stdout.strip()
            else:
                r = subprocess.run(
                    ["osascript", "-e",
                     "POSIX path of (choose folder with prompt "
                     "\"Select your source folder:\")"],
                    capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    path = r.stdout.strip()
        except Exception:
            pass
        self.respond(200, "application/json", json.dumps({"path": path}).encode())

    # ── POST ─────────────────────────────────────────────────

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n).decode("utf-8")

    def _parse_form(self):
        pp = {}
        for part in self._read_body().split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                pp[k] = unquote_plus(v)
        return pp

    def handle_run(self):
        pp      = self._parse_form()
        folder  = pp.get("folder", "").strip()
        dry     = pp.get("dry", "1") == "1"
        subsort = pp.get("subsort", "1") == "1"
        _set_busy(True, reset_log=True)
        self.respond(200, "text/plain", b"OK")
        threading.Thread(target=self.task, args=(folder, dry, subsort), daemon=True).start()

    def handle_add_folder(self):
        pp      = self._parse_form()
        name    = pp.get("name", "").strip()
        size    = pp.get("size", "").strip()
        subsort = pp.get("subsort", "1") == "1"
        max_kb  = int(size) if size.isdigit() else None
        if not name:
            self.respond(400, "application/json",
                         json.dumps({"error": "Name required"}).encode())
            return
        _set_busy(True)
        self.respond(200, "text/plain", b"OK")
        threading.Thread(target=self.custom_task, args=(name, max_kb, subsort),
                         daemon=True).start()

    def handle_apply(self):
        try:
            data = json.loads(self._read_body() or "{}")
        except Exception:
            data = {}
        items   = data.get("items", [])
        subsort = bool(data.get("subsort", True))
        _set_busy(True)
        self.respond(200, "text/plain", b"OK")
        threading.Thread(target=self.apply_task, args=(items, subsort), daemon=True).start()

    # ── Background tasks ─────────────────────────────────────

    def handle_save_run(self):
        try:
            data = json.loads(self._read_body() or "{}")
        except Exception:
            data = {}
        items   = data.get("items", [])
        folder  = str(data.get("folder", "")).strip()
        subsort = bool(data.get("subsort", True))
        _set_busy(True, reset_log=True)
        self.respond(200, "text/plain", b"OK")
        def go():
            saved = save_identifiers(items)
            print("\n  Saved identifiers: " + (", ".join(saved) if saved else "none"))
            print("  Dry Run turned OFF -- running for real...\n")
            run_all(folder, dry_run=False, subsort=subsort)
        threading.Thread(target=self._run_captured, args=(go,), daemon=True).start()

    def _run_captured(self, fn):
        old, sys.stdout = sys.stdout, Cap()
        try:
            fn()
        except Exception as e:
            print(f"\nError: {e}\n")
        finally:
            sys.stdout = old
            _set_busy(False)

    def task(self, folder, dry, subsort):
        def go():
            if MANAGER_OK:
                run_all(folder, dry_run=dry, subsort=subsort)
            else:
                print("file_manager.py not found!")
        self._run_captured(go)

    def custom_task(self, name, max_kb, subsort):
        def go():
            r = create_custom_folder(name, max_kb, subsort=subsort)
            if "error" in r:
                print(f"\n  Error: {r['error']}\n")
        self._run_captured(go)

    def apply_task(self, items, subsort):
        self._run_captured(lambda: apply_identifiers(items, subsort=subsort))

    def respond(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type",   ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control",  "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


# ──────────────────────────────────────────────────────────────
#  HTML — Apple-style frosted glass
# ──────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>File Manager</title>
<style>
:root{
  --blue:#0A84FF; --red:#FF453A; --green:#30D158; --amber:#FFD60A;
  --text:rgba(255,255,255,.92); --text2:rgba(255,255,255,.55); --text3:rgba(255,255,255,.32);
  --glass:rgba(255,255,255,.07); --stroke:rgba(255,255,255,.12); --stroke2:rgba(255,255,255,.07);
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Helvetica,Arial,sans-serif;
  color:var(--text);background:#0a0a12;min-height:100vh;padding:28px 24px 90px;
  -webkit-font-smoothing:antialiased;position:relative;overflow-x:hidden;
}
body::before{
  content:"";position:fixed;inset:-20%;z-index:-1;
  background:
    radial-gradient(40% 35% at 15% 10%, rgba(10,132,255,.45), transparent 70%),
    radial-gradient(35% 30% at 90% 20%, rgba(191,90,242,.35), transparent 70%),
    radial-gradient(40% 35% at 70% 95%, rgba(48,209,88,.22), transparent 70%),
    radial-gradient(30% 30% at 5% 85%, rgba(255,159,10,.18), transparent 70%);
  filter:blur(40px);
}
.glass{
  background:var(--glass);border:1px solid var(--stroke);border-radius:20px;
  backdrop-filter:blur(30px) saturate(170%);-webkit-backdrop-filter:blur(30px) saturate(170%);
  box-shadow:0 10px 40px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.08);
}
.wrap{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
.hdr{display:flex;align-items:center;gap:14px;padding:18px 22px}
.logo{width:44px;height:44px;border-radius:12px;flex-shrink:0;background:linear-gradient(145deg,#2b6cff,#6b4dff);
  display:flex;align-items:center;justify-content:center;font-size:22px;
  box-shadow:0 6px 18px rgba(43,108,255,.45), inset 0 1px 0 rgba(255,255,255,.3)}
.hdr h1{font-size:20px;font-weight:700;letter-spacing:-.02em}
.hdr p{font-size:12.5px;color:var(--text2);margin-top:2px}
.sec{padding:20px 22px}
.lbl{font-size:12px;font-weight:600;color:var(--text2);margin-bottom:10px}
.row{display:flex;gap:10px}
.fin{flex:1;background:rgba(0,0,0,.25);border:1px solid var(--stroke2);border-radius:12px;padding:12px 14px;font-size:13px;
  font-family:"SF Mono",Menlo,Consolas,monospace;color:var(--text);outline:none;transition:border-color .2s,box-shadow .2s}
.fin:focus{border-color:var(--blue);box-shadow:0 0 0 4px rgba(10,132,255,.2)}
.fin::placeholder{color:var(--text3)}
.btn{background:rgba(255,255,255,.1);color:var(--text);border:1px solid var(--stroke);border-radius:12px;font-size:13px;
  font-weight:600;padding:0 20px;cursor:pointer;font-family:inherit;transition:background .2s}
.btn:hover{background:rgba(255,255,255,.16)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.opt{display:flex;align-items:center;gap:14px;padding:4px 0}
.opt + .note{margin-top:12px}
.sep{height:1px;background:var(--stroke2);margin:16px 0}
.cinfo{flex:1}
.cinfo h3{font-size:14.5px;font-weight:600}
.cinfo p{font-size:12px;color:var(--text2);margin-top:3px}
.sw{position:relative;display:inline-block;width:51px;height:31px;flex-shrink:0;cursor:pointer}
.sw input{opacity:0;width:0;height:0}
.sl{position:absolute;inset:0;background:rgba(120,120,128,.36);border-radius:31px;transition:background .25s}
.sl:before{content:"";position:absolute;width:27px;height:27px;left:2px;top:2px;background:#fff;border-radius:50%;
  transition:transform .25s cubic-bezier(.3,.7,.4,1);box-shadow:0 3px 8px rgba(0,0,0,.25)}
input:checked + .sl{background:var(--green)}
input:checked + .sl:before{transform:translateX(20px)}
.bdg{font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px;flex-shrink:0}
.bon{background:rgba(48,209,88,.16);color:var(--green)}
.boff{background:rgba(255,69,58,.16);color:var(--red)}
.note{padding:10px 14px;border-radius:12px;font-size:12.5px}
.nw{background:rgba(255,214,10,.10);color:#ffe066;border:1px solid rgba(255,214,10,.18)}
.nl{background:rgba(255,69,58,.12);color:#ff7a70;border:1px solid rgba(255,69,58,.22)}
.ns{background:rgba(255,255,255,.04);color:var(--text2);border:1px solid var(--stroke2)}
#runBtn{width:100%;padding:16px;font-size:15px;font-weight:600;border-radius:16px;border:none;cursor:pointer;
  font-family:inherit;color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.25);
  transition:filter .2s,background .25s}
#runBtn:hover:not(:disabled){filter:brightness(1.1)}
#runBtn:disabled{cursor:not-allowed;box-shadow:none}
.ltop{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.ltop .lbl{margin:0}
.smbtn{background:rgba(255,255,255,.08);border:none;color:var(--text2);font-size:12px;cursor:pointer;padding:5px 12px;border-radius:8px;font-family:inherit}
.smbtn:hover{color:var(--text);background:rgba(255,255,255,.14)}
#log{background:rgba(0,0,0,.3);border:1px solid var(--stroke2);border-radius:14px;padding:16px;height:300px;overflow-y:auto;
  font-family:"SF Mono",Menlo,Consolas,monospace;font-size:11.5px;line-height:1.7;white-space:pre-wrap;word-break:break-word;color:rgba(255,255,255,.75)}

/* Smart Sort panel */
#idSection{display:none;padding:20px 22px;border-color:rgba(10,132,255,.4)}
.idhead{font-size:15px;font-weight:600;margin-bottom:6px}
.idsub{font-size:12px;color:var(--text2);margin-bottom:14px;line-height:1.5}
.idgrp{background:rgba(0,0,0,.18);border:1px solid var(--stroke2);border-radius:14px;padding:14px;margin-bottom:12px}
.idgt{font-size:12px;font-weight:600;color:var(--text2);margin-bottom:8px}
.idpat{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:11.5px;color:var(--text2);margin-bottom:10px;word-break:break-all}
.idpat b{color:#7cc0ff;font-weight:600}
.lowc{display:inline-block;font-size:11px;font-weight:600;color:#ffe066;background:rgba(255,214,10,.12);
  border:1px solid rgba(255,214,10,.25);padding:3px 10px;border-radius:20px;margin-bottom:10px}
.idsecrow{display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:12px;color:var(--text2)}
.sel{background:rgba(0,0,0,.3);border:1px solid var(--stroke2);color:var(--text);border-radius:10px;padding:7px 10px;
  font-size:12.5px;font-family:inherit;outline:none;max-width:220px}
.idrow{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--stroke2);flex-wrap:wrap}
.idrow input[type=checkbox]{width:18px;height:18px;accent-color:var(--blue);flex-shrink:0}
.idname{flex:1;min-width:140px;font-weight:600}
.idcount{font-size:12px;color:var(--text3);min-width:52px}
.idlbl{font-size:12px;color:var(--text3)}
.idkb{width:110px}
.idinh{font-size:11.5px;color:var(--text3)}
.warn{font-size:11.5px;color:#ffe066}
.idbtns{display:flex;gap:8px;margin-top:6px;flex-wrap:wrap}

/* Manual panel */
#customSection{display:none;padding:20px 22px;border-color:rgba(255,214,10,.3)}
.ct{font-size:14px;font-weight:600;color:#ffe066;margin-bottom:12px}
.sl2{background:rgba(0,0,0,.25);border-radius:12px;padding:10px 14px;margin-bottom:16px;font-family:"SF Mono",Menlo,Consolas,monospace;
  font-size:11.5px;color:var(--text2);max-height:120px;overflow-y:auto;border:1px solid var(--stroke2)}
.si{padding:2px 0}
.cf{display:flex;flex-direction:column;gap:14px}
.cf label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:8px}
.ci{width:100%;background:rgba(0,0,0,.25);border:1px solid var(--stroke2);border-radius:12px;padding:10px 14px;font-size:13px;
  color:var(--text);outline:none;font-family:inherit;transition:border-color .2s,box-shadow .2s}
.ci:focus{border-color:var(--amber);box-shadow:0 0 0 4px rgba(255,214,10,.15)}
.ci::placeholder{color:var(--text3)}
.idrow .ci{width:auto}
.cr{display:flex;gap:10px;align-items:flex-start}
#addBtn{background:var(--amber);color:#1c1c1e;border:none;border-radius:12px;font-size:13px;font-weight:700;padding:12px 20px;cursor:pointer;font-family:inherit;white-space:nowrap}
#addBtn:disabled{opacity:.4;cursor:not-allowed}
.cn{font-size:11.5px;color:var(--text3);margin-top:6px;line-height:1.5}
#confirmBox{display:none;padding:16px;border-radius:14px;background:rgba(10,132,255,.08);border:1px solid rgba(10,132,255,.35);font-size:12.5px;line-height:1.6}
.cm{margin-bottom:12px}
.cbs{display:flex;gap:8px}
.cy,.cn2,.cg{border:none;border-radius:10px;padding:9px 18px;font-weight:600;cursor:pointer;font-size:12.5px;font-family:inherit}
.cy{background:var(--blue);color:#fff}
.cg{background:var(--green);color:#0b1f10}
.cn2{background:rgba(255,255,255,.1);color:var(--text)}
.cy:hover,.cn2:hover,.cg:hover{filter:brightness(1.15)}
.cy:disabled,.cg:disabled{opacity:.4;cursor:not-allowed;filter:none}

.sbar{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:10px;padding:10px 18px;
  border-radius:30px;font-size:12.5px;color:var(--text2);max-width:calc(100% - 40px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;box-shadow:0 0 10px currentColor}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:3px}
</style>
</head>
<body>
<div class="wrap">

  <div class="glass hdr">
    <div class="logo">&#128230;</div>
    <div>
      <h1>File Manager</h1>
      <p>Create folders &middot; Sort &middot; Sub-sort &middot; Compress</p>
    </div>
  </div>

  <div class="glass sec">
    <div class="lbl">Source Folder</div>
    <div class="row">
      <input class="fin" type="text" id="fi" placeholder="Paste a folder path or click Browse"/>
      <button class="btn" id="bb" onclick="doBrowse()">Browse</button>
    </div>
  </div>

  <div class="glass sec">
    <div class="opt">
      <div class="cinfo"><h3>Dry Run</h3><p>Preview only. Nothing will be moved or compressed.</p></div>
      <span class="bdg bon" id="bdg">ON</span>
      <label class="sw"><input type="checkbox" id="dc" checked onchange="onDry()"><span class="sl"></span></label>
    </div>
    <div class="note nw" id="nt">Dry Run is ON - safe to run, no files will change</div>
    <div class="sep"></div>
    <div class="opt">
      <div class="cinfo"><h3>Sub-sort by Dimensions</h3><p>Group files into sub-folders by image size, e.g. 1200x628</p></div>
      <span class="bdg bon" id="sbdg">ON</span>
      <label class="sw"><input type="checkbox" id="sc" checked onchange="onSubsort()"><span class="sl"></span></label>
    </div>
    <div class="note ns" id="snt">Sub-sort is ON - files will be grouped by image dimensions</div>
  </div>

  <button id="runBtn" style="background:#0A84FF;" onclick="doRun()">Run File Manager (Dry Run - Preview only)</button>

  <div class="glass sec">
    <div class="ltop">
      <div class="lbl">Output Log</div>
      <button class="smbtn" onclick="doClear()">Clear</button>
    </div>
    <div id="log">File Manager ready!

__M__
__P__

How to use:
  1. Click Browse and select your folder
  2. Keep Dry Run ON and click Run to preview
  3. Check the output log looks correct
  4. Turn off Dry Run and click Run to apply for real
</div>
  </div>

  <!-- Smart Sort panel -->
  <div class="glass" id="idSection">
    <div class="idhead" id="idHead"></div>
    <div class="idsub">Untick anything you don't want, edit names, or map an identifier to an existing folder. Nothing is created until you click Confirm.</div>
    <div class="note nw" id="idDry" style="display:none;margin-bottom:12px">Dry Run is ON - this is a preview. Clicking Accept All or Confirm will turn Dry Run off and run for real.</div>
    <div id="idGroups"></div>
    <div class="cn" id="idUnd" style="display:none;margin-bottom:10px"></div>
    <div class="idbtns">
      <button class="cy" id="idAccept" onclick="acceptAll()">Accept All</button>
      <button class="cn2" onclick="skipAll()">Skip All</button>
      <button class="cg" id="idConfirm" onclick="doConfirmIds()">Confirm</button>
    </div>
  </div>

  <!-- Manual fallback panel -->
  <div class="glass" id="customSection">
    <div class="ct">&#9888;&#65039; Unsorted Files &middot; <span id="skipCount">0</span> file(s)</div>
    <div class="sl2" id="skipList"></div>
    <div class="cf">
      <div>
        <label>Manual Folder Name</label>
        <input class="ci" type="text" id="customName" placeholder="e.g. XYZ BRAND"/>
        <div class="cn">Files containing this keyword will be moved into this folder. Saved permanently.</div>
      </div>
      <div>
        <label>Max File Size in KB (optional)</label>
        <div class="cr">
          <div style="flex:1">
            <input class="ci" type="number" id="customSize" placeholder="Leave blank for no limit"/>
            <div class="cn">500 = 500 KB &middot; 1024 = 1 MB &middot; blank = keep original</div>
          </div>
          <button id="addBtn" onclick="doAddFolder()">Create &amp; Sort</button>
        </div>
      </div>
      <div id="confirmBox">
        <div class="cm" id="confirmMsg"></div>
        <div class="cbs">
          <button class="cy" id="confirmYes">Yes, Create It</button>
          <button class="cn2" onclick="hideConfirm()">Cancel</button>
        </div>
      </div>
    </div>
  </div>

</div>

<div class="glass sbar">
  <div class="dot" id="dot" style="background:#30D158;color:#30D158"></div>
  <span id="st">Ready</span>
</div>

<script>
var BLUE="#0A84FF", RED="#FF453A", GREEN="#30D158";
var _dry=true,_subsort=true,_poll=null,_len=0,_pn="",_ps="",_det=null;

/* ── Helpers ─────────────────────────────── */
function xhr(method,url,body,ctype,cb){
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){if(x.readyState!==4)return;cb(x.status,x.responseText);};
  x.open(method,url,true);
  if(ctype)x.setRequestHeader("Content-Type",ctype);
  x.send(body||null);
}
function el(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;}
function doClear(){document.getElementById("log").innerText="";_len=0;}
function addLog(t){var e=document.getElementById("log");e.innerText+=t;e.scrollTop=e.scrollHeight;}
function setSt(t){document.getElementById("st").innerText=t||"Ready";}
function setDot(c){var d=document.getElementById("dot");d.style.background=c;d.style.color=c;}
function pollUntilDone(done){
  var t=setInterval(function(){
    xhr("GET","/poll",null,null,function(s,txt){
      if(s!==200)return;var d;try{d=JSON.parse(txt);}catch(e){return;}
      if(d.log&&d.log.length>_len){addLog(d.log.substring(_len));_len=d.log.length;}
      if(!d.busy){clearInterval(t);done();}
    });
  },700);
}

/* ── Toggles ─────────────────────────────── */
function onDry(){
  _dry=document.getElementById("dc").checked;
  var b=document.getElementById("bdg"),n=document.getElementById("nt"),btn=document.getElementById("runBtn");
  if(_dry){b.className="bdg bon";b.innerText="ON";n.className="note nw";n.innerText="Dry Run is ON - safe to run, no files will change";btn.style.background=BLUE;}
  else{b.className="bdg boff";b.innerText="OFF";n.className="note nl";n.innerText="Dry Run is OFF - files WILL be moved and compressed!";btn.style.background=RED;}
  updBtn();
}
function onSubsort(){
  _subsort=document.getElementById("sc").checked;
  var b=document.getElementById("sbdg"),n=document.getElementById("snt");
  if(_subsort){b.className="bdg bon";b.innerText="ON";n.innerText="Sub-sort is ON - files will be grouped by image dimensions";}
  else{b.className="bdg boff";b.innerText="OFF";n.innerText="Sub-sort is OFF - files stay in their parent folder";}
}
function updBtn(){
  var btn=document.getElementById("runBtn");
  if(btn.disabled)return;
  btn.innerText=_dry?"Run File Manager (Dry Run - Preview only)":"Run File Manager (LIVE - files will change!)";
}
function doBrowse(){
  var btn=document.getElementById("bb");btn.disabled=true;btn.innerText="Opening...";setSt("Opening folder picker...");
  xhr("GET","/browse",null,null,function(s,txt){
    btn.disabled=false;btn.innerText="Browse";
    if(s!==200)return;
    try{var d=JSON.parse(txt);if(d.path){document.getElementById("fi").value=d.path;setSt("Folder: "+d.path);}else{setSt("No folder selected.");}}
    catch(e){setSt("Paste the path manually.");}
  });
}

/* ── Unsorted files ──────────────────────── */
function checkSkipped(){
  xhr("GET","/skipped",null,null,function(s,txt){
    if(s!==200)return;var d;try{d=JSON.parse(txt);}catch(e){return;}
    var f=d.files||[],sec=document.getElementById("customSection");
    if(!f.length){sec.style.display="none";document.getElementById("idSection").style.display="none";return;}
    sec.style.display="block";
    document.getElementById("skipCount").innerText=f.length;
    var l=document.getElementById("skipList");l.innerHTML="";
    for(var i=0;i<f.length;i++){l.appendChild(el("div","si","\u2022 "+f[i]));}
    loadDetect();
  });
}

/* ── Smart Sort ──────────────────────────── */
function loadDetect(){
  xhr("GET","/detect",null,null,function(s,txt){
    if(s!==200)return;try{_det=JSON.parse(txt);}catch(e){return;}
    for(var i=0;i<_det.groups.length;i++){_det.groups[i].def=_det.groups[i].chosen;}
    renderDetect();
  });
}
function renderDetect(){
  var sec=document.getElementById("idSection"),box=document.getElementById("idGroups");
  box.innerHTML="";
  if(!_det||!_det.groups||!_det.groups.length){sec.style.display="none";return;}
  sec.style.display="block";
  var multi=_det.groups.length>1;
  _det.groups.forEach(function(g,gi){
    var pos=g.positions[g.chosen];
    var wrap=el("div","idgrp");
    if(multi)wrap.appendChild(el("div","idgt","Group "+(gi+1)+" \u00b7 "+g.file_count+" file(s)"));

    var pat=el("div","idpat");pat.appendChild(document.createTextNode("Pattern: "));
    var bits=pos.pattern.split("[IDENTIFIER]");
    for(var b=0;b<bits.length;b++){pat.appendChild(document.createTextNode(bits[b]));if(b<bits.length-1)pat.appendChild(el("b",null,"[IDENTIFIER]"));}
    wrap.appendChild(pat);

    if(g.low_confidence&&g.chosen===g.def)wrap.appendChild(el("div","lowc","Low confidence, please check"));

    if(g.positions.length>1){
      var sr=el("div","idsecrow");sr.appendChild(el("span",null,"Identifier section:"));
      var sel=el("select","sel");
      g.positions.forEach(function(p){var o=new Option(p.label,p.index);if(p.index===g.chosen)o.selected=true;sel.appendChild(o);});
      sel.onchange=function(){g.chosen=parseInt(sel.value,10);renderDetect();};
      sr.appendChild(sel);wrap.appendChild(sr);
    }

    g._rows=[];
    pos.rows.forEach(function(r){
      var row=el("div","idrow");
      var cb=document.createElement("input");cb.type="checkbox";cb.checked=true;
      var nm=el("input","ci idname");nm.type="text";nm.value=r.name;
      var cnt=el("span","idcount",r.files.length+(r.files.length===1?" file":" files"));cnt.title=r.files.join("\n");
      var mp=el("select","sel");mp.appendChild(new Option("New folder",""));
      (_det.folders||[]).forEach(function(f){var o=new Option(f,f);if(f===r.suggest)o.selected=true;mp.appendChild(o);});
      var kb=el("input","ci idkb");kb.type="number";kb.placeholder="Max KB";
      var inh=el("span","idinh","");
      var warn=el("span","warn",r.short?"\u26a0 Short name":"");
      var sync=function(){if(mp.value){kb.style.display="none";inh.textContent="uses "+mp.value+" limit";}else{kb.style.display="";inh.textContent="";}};
      mp.onchange=sync;nm.oninput=updateHeadline;
      row.appendChild(cb);row.appendChild(nm);row.appendChild(cnt);
      row.appendChild(el("span","idlbl","Map to"));row.appendChild(mp);
      row.appendChild(kb);row.appendChild(inh);row.appendChild(warn);
      sync();
      wrap.appendChild(row);
      g._rows.push({cb:cb,name:nm,map:mp,size:kb,files:r.files,orig:r.name});
    });
    box.appendChild(wrap);
  });

  var und=_det.undetected||[],un=document.getElementById("idUnd");
  un.textContent=und.length?(und.length+" file(s) couldn't be analysed. Use the manual option below."):"";
  un.style.display=und.length?"block":"none";

  document.getElementById("idDry").style.display=_det.dry?"block":"none";
  setIdBusy(false);
  updateHeadline();
}
function updateHeadline(){
  var names=[];
  if(_det&&_det.groups){_det.groups.forEach(function(g){(g._rows||[]).forEach(function(r){var n=r.name.value.trim().toUpperCase();if(n)names.push(n);});});}
  var h;
  if(!names.length)h="No identifiers detected.";
  else if(names.length===1)h="1 unique identifier was detected: "+names[0]+".";
  else if(names.length===2)h="2 unique identifiers were detected: "+names[0]+" and "+names[1]+".";
  else h=names.length+" unique identifiers were detected: "+names.slice(0,-1).join(", ")+", and "+names[names.length-1]+".";
  document.getElementById("idHead").textContent=h;
}
function setIdBusy(on){
  var c=document.getElementById("idConfirm"),a=document.getElementById("idAccept");
  c.disabled=on;a.disabled=on;c.innerText=on?"Applying...":"Confirm";
}
function doConfirmIds(){
  if(!_det)return;
  var items=[],shorts=[];
  _det.groups.forEach(function(g){(g._rows||[]).forEach(function(r){
    if(!r.cb.checked)return;
    var name=r.name.value.trim(),map=r.map.value;
    if(!name&&!map)return;
    if(!map&&name.replace(/[^A-Za-z0-9]/g,"").length<3)shorts.push(name);
    items.push({name:name,map_to:map,max_kb:map?"":r.size.value.trim(),files:r.files,detected:r.orig});
  });});
  if(!items.length){alert("No identifiers selected.");return;}
  if(shorts.length&&!confirm("These names are very short and may match other files by mistake:\n"+shorts.join(", ")+"\n\nSave anyway?"))return;
  if(_det.dry){
    if(!confirm("Dry Run is ON.\n\nTo apply, File Manager will turn Dry Run OFF and run for real:\n- save these identifiers\n- sort ALL files into folders\n- sub-sort and compress\n\nThis cannot be undone. Continue?"))return;
    saveAndRun(items);return;
  }
  setIdBusy(true);setSt("Applying identifiers...");setDot(BLUE);
  xhr("POST","/apply-identifiers",JSON.stringify({items:items,subsort:_subsort}),"application/json",function(s){
    if(s!==200){setIdBusy(false);setSt("Error applying identifiers.");setDot(RED);return;}
    pollUntilDone(function(){
      setIdBusy(false);setSt("Identifiers applied and saved!");setDot(GREEN);
      document.getElementById("idSection").style.display="none";
      checkSkipped();
    });
  });
}
function saveAndRun(items){
  var f=document.getElementById("fi").value.trim();
  if(!f.length){alert("Please select a folder first.");return;}
  document.getElementById("dc").checked=false;onDry();
  doClear();_len=0;
  document.getElementById("idSection").style.display="none";
  document.getElementById("customSection").style.display="none";
  setBusy(true);setSt("Saving identifiers and running...");
  xhr("POST","/save-and-run",JSON.stringify({items:items,folder:f,subsort:_subsort}),"application/json",function(s){
    if(s!==200){setBusy(false);setSt("Error");setDot(RED);return;}
    pollUntilDone(function(){setBusy(false);setDot(GREEN);setSt("Done! All files processed.");checkSkipped();});
  });
}
function acceptAll(){
  if(!_det)return;
  _det.groups.forEach(function(g){(g._rows||[]).forEach(function(r){r.cb.checked=true;});});
  doConfirmIds();
}
function skipAll(){
  document.getElementById("idSection").style.display="none";
  addLog("\nDetected identifiers skipped for this run. Files stay unsorted.\n");
  setSt("Identifiers skipped.");
}

/* ── Manual fallback ─────────────────────── */
function showConfirm(n,s,m){
  _pn=n;_ps=s;document.getElementById("confirmMsg").innerHTML=m;
  document.getElementById("confirmYes").onclick=function(){submitFolder(_pn,_ps);};
  document.getElementById("confirmBox").style.display="block";
}
function hideConfirm(){document.getElementById("confirmBox").style.display="none";_pn="";_ps="";}
function submitFolder(name,sv){
  hideConfirm();
  var btn=document.getElementById("addBtn");btn.disabled=true;btn.innerText="Creating...";setSt("Creating: "+name+"...");
  var b="name="+encodeURIComponent(name)+"&size="+encodeURIComponent(sv)+"&subsort="+(_subsort?"1":"0");
  xhr("POST","/add-folder",b,"application/x-www-form-urlencoded",function(s){
    if(s!==200){btn.disabled=false;btn.innerText="Create & Sort";setSt("Failed.");return;}
    document.getElementById("customName").value="";document.getElementById("customSize").value="";
    pollUntilDone(function(){btn.disabled=false;btn.innerText="Create & Sort";setSt("Done - check the log.");setDot(GREEN);checkSkipped();});
  });
}
function doAddFolder(){
  var name=document.getElementById("customName").value.trim(),sv=document.getElementById("customSize").value.trim();
  hideConfirm();if(!name){alert("Please enter a folder name.");return;}setSt("Checking...");
  xhr("GET","/check-folder?name="+encodeURIComponent(name),null,null,function(s,txt){
    var d;try{d=JSON.parse(txt);}catch(e){submitFolder(name,sv);return;}
    setSt("");
    if(d.exists){addLog("\nFolder \""+d.matched+"\" found in "+(d.source==="custom"?"custom list":"built-in list")+". Proceeding...\n");submitFolder(name,sv);}
    else{showConfirm(name,sv,"<strong style=\"color:#ff7a70\">This name is not in the folder list.</strong><br><br>This will create the folder, move matching files into it, and save it permanently.<br><br>Create anyway?");}
  });
}

/* ── Run ─────────────────────────────────── */
function setBusy(on){
  var btn=document.getElementById("runBtn");btn.disabled=on;
  if(on){btn.style.background="rgba(255,255,255,.1)";btn.style.color="rgba(255,255,255,.45)";btn.innerText="Running...";setDot(BLUE);}
  else{btn.style.background=_dry?BLUE:RED;btn.style.color="#fff";updBtn();}
}
function doRun(){
  var f=document.getElementById("fi").value.trim();
  if(!f.length){alert("Please select a folder first.");return;}
  if(!_dry&&!confirm("Dry Run is OFF.\n\nFiles will be MOVED and COMPRESSED.\nThis cannot be undone.\n\nProceed?"))return;
  doClear();_len=0;hideConfirm();
  document.getElementById("customSection").style.display="none";
  document.getElementById("idSection").style.display="none";
  setBusy(true);setSt("Running...");
  addLog((_dry?"DRY RUN":"LIVE RUN")+" - "+f+"\nSub-sort: "+(_subsort?"ON":"OFF")+"\n\n");
  var b="folder="+encodeURIComponent(f)+"&dry="+(_dry?"1":"0")+"&subsort="+(_subsort?"1":"0");
  xhr("POST","/run",b,"application/x-www-form-urlencoded",function(s){
    if(s!==200){addLog("Error: server did not respond.\n");setBusy(false);setSt("Error");setDot(RED);return;}
    pollUntilDone(function(){
      setBusy(false);setDot(GREEN);
      setSt(_dry?"Dry run done. Turn off Dry Run to apply.":"Done! All files processed.");
      checkSkipped();
    });
  });
}
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────

def start_server():
    free_port(PORT)
    for _ in range(10):
        if port_free(PORT):
            break
        time.sleep(0.5)
    server = Server(("", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    if not WEBVIEW_OK:
        print("PyWebView not installed. Run: pip3 install pywebview")
        sys.exit(1)

    print("\n  File Manager starting...")
    start_server()
    if not wait_for_server(PORT):
        print("  ERROR: Server failed to start.")
        sys.exit(1)

    webview.create_window(
        title            = "File Manager",
        url              = f"http://localhost:{PORT}",
        width            = 900,
        height           = 820,
        min_size         = (720, 600),
        resizable        = True,
        background_color = "#0a0a12",
    )
    webview.start(debug=False)
    print("\n  File Manager closed. Goodbye!\n")


if __name__ == "__main__":
    main()
