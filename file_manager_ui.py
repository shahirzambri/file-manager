#!/usr/bin/env python3
"""
File Manager — Desktop App (PyWebView)
Apple-style frosted glass UI. Works on macOS and Windows.
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
        get_last_skipped, create_custom_folder,
        check_folder_exists
    )
    MANAGER_OK = True
except ImportError:
    MANAGER_OK    = False
    PIL_AVAILABLE = False

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
            result = subprocess.run(["netstat", "-ano"],
                                    capture_output=True, text=True)
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


class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        p = self.path.split("?")[0]
        if   p == "/":             self.serve_page()
        elif p == "/poll":         self.serve_poll()
        elif p == "/browse":       self.serve_browse()
        elif p == "/skipped":      self.serve_skipped()
        elif p == "/check-folder": self.serve_check_folder()
        else:                      self.send_error(404)

    def do_POST(self):
        if   self.path == "/run":        self.handle_run()
        elif self.path == "/add-folder": self.handle_add_folder()
        else:                            self.send_error(404)

    def serve_page(self):
        m = ("file_manager.py loaded OK" if MANAGER_OK
             else "ERROR: file_manager.py not found!")
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
        self.respond(200, "application/json",
                     json.dumps({"files": files}).encode())

    def serve_check_folder(self):
        qs   = parse_qs(urlparse(self.path).query)
        name = qs.get("name", [""])[0].strip()
        r    = (check_folder_exists(name) if MANAGER_OK and name
                else {"exists": False, "source": "none", "matched": ""})
        self.respond(200, "application/json", json.dumps(r).encode())

    def serve_browse(self):
        path = ""
        try:
            if WEBVIEW_OK and webview.windows:
                result = webview.windows[0].create_file_dialog(
                    webview.FOLDER_DIALOG)
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
        self.respond(200, "application/json",
                     json.dumps({"path": path}).encode())

    def _parse_post(self):
        n   = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8")
        pp  = {}
        for part in raw.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                pp[k] = unquote_plus(v)
        return pp

    def handle_run(self):
        pp      = self._parse_post()
        folder  = pp.get("folder", "").strip()
        dry     = pp.get("dry", "1") == "1"
        subsort = pp.get("subsort", "1") == "1"
        self.respond(200, "text/plain", b"OK")
        threading.Thread(target=self.task, args=(folder, dry, subsort),
                         daemon=True).start()

    def handle_add_folder(self):
        pp     = self._parse_post()
        name   = pp.get("name", "").strip()
        size   = pp.get("size", "").strip()
        max_kb = int(size) if size.isdigit() else None
        if not name:
            self.respond(400, "application/json",
                         json.dumps({"error": "Name required"}).encode())
            return
        self.respond(200, "text/plain", b"OK")
        threading.Thread(target=self.custom_task, args=(name, max_kb),
                         daemon=True).start()

    def task(self, folder, dry, subsort):
        global _log, _busy
        with _lock:
            _log  = []
            _busy = True
        old, sys.stdout = sys.stdout, Cap()
        try:
            if MANAGER_OK:
                run_all(folder, dry_run=dry, subsort=subsort)
            else:
                print("file_manager.py not found!")
        except Exception as e:
            print(f"\nError: {e}\n")
        finally:
            sys.stdout = old
            with _lock:
                _busy = False

    def custom_task(self, name, max_kb):
        global _busy
        with _lock:
            _busy = True
        old, sys.stdout = sys.stdout, Cap()
        try:
            if MANAGER_OK:
                r = create_custom_folder(name, max_kb, dry_run=False)
                if "error" in r:
                    print(f"\n  Error: {r['error']}\n")
        except Exception as e:
            print(f"\nError: {e}\n")
        finally:
            sys.stdout = old
            with _lock:
                _busy = False

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
  --glass:rgba(255,255,255,.07); --glass2:rgba(255,255,255,.04);
  --stroke:rgba(255,255,255,.12); --stroke2:rgba(255,255,255,.07);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{min-height:100%}
body{
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Helvetica,Arial,sans-serif;
  color:var(--text);
  background:#0a0a12;
  min-height:100vh;
  padding:28px 24px 90px;
  -webkit-font-smoothing:antialiased;
  position:relative;
  overflow-x:hidden;
}
/* Coloured blobs behind the glass */
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
  background:var(--glass);
  border:1px solid var(--stroke);
  border-radius:20px;
  backdrop-filter:blur(30px) saturate(170%);
  -webkit-backdrop-filter:blur(30px) saturate(170%);
  box-shadow:0 10px 40px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.08);
}
.wrap{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:16px}

/* Header */
.hdr{display:flex;align-items:center;gap:14px;padding:18px 22px}
.logo{
  width:44px;height:44px;border-radius:12px;flex-shrink:0;
  background:linear-gradient(145deg,#2b6cff,#6b4dff);
  display:flex;align-items:center;justify-content:center;font-size:22px;
  box-shadow:0 6px 18px rgba(43,108,255,.45), inset 0 1px 0 rgba(255,255,255,.3);
}
.hdr h1{font-size:20px;font-weight:700;letter-spacing:-.02em}
.hdr p{font-size:12.5px;color:var(--text2);margin-top:2px}

/* Section */
.sec{padding:20px 22px}
.lbl{font-size:12px;font-weight:600;color:var(--text2);margin-bottom:10px;letter-spacing:.01em}

/* Folder row */
.row{display:flex;gap:10px}
.fin{
  flex:1;background:rgba(0,0,0,.25);border:1px solid var(--stroke2);
  border-radius:12px;padding:12px 14px;font-size:13px;
  font-family:"SF Mono",Menlo,Consolas,monospace;color:var(--text);outline:none;
  transition:border-color .2s, box-shadow .2s;
}
.fin:focus{border-color:var(--blue);box-shadow:0 0 0 4px rgba(10,132,255,.2)}
.fin::placeholder{color:var(--text3)}
.btn{
  background:rgba(255,255,255,.1);color:var(--text);border:1px solid var(--stroke);
  border-radius:12px;font-size:13px;font-weight:600;padding:0 20px;cursor:pointer;
  font-family:inherit;transition:background .2s, transform .1s;
}
.btn:hover{background:rgba(255,255,255,.16)}
.btn:active{transform:scale(.97)}
.btn:disabled{opacity:.4;cursor:not-allowed}

/* Option rows */
.opt{display:flex;align-items:center;gap:14px;padding:4px 0}
.opt + .note{margin-top:12px}
.sep{height:1px;background:var(--stroke2);margin:16px 0}
.cinfo{flex:1}
.cinfo h3{font-size:14.5px;font-weight:600}
.cinfo p{font-size:12px;color:var(--text2);margin-top:3px}

/* iOS switch */
.sw{position:relative;display:inline-block;width:51px;height:31px;flex-shrink:0;cursor:pointer}
.sw input{opacity:0;width:0;height:0}
.sl{position:absolute;inset:0;background:rgba(120,120,128,.36);border-radius:31px;transition:background .25s}
.sl:before{
  content:"";position:absolute;width:27px;height:27px;left:2px;top:2px;background:#fff;
  border-radius:50%;transition:transform .25s cubic-bezier(.3,.7,.4,1);
  box-shadow:0 3px 8px rgba(0,0,0,.25),0 1px 1px rgba(0,0,0,.15);
}
input:checked + .sl{background:var(--green)}
input:checked + .sl:before{transform:translateX(20px)}

/* Badges */
.bdg{font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px;flex-shrink:0;letter-spacing:.03em}
.bon{background:rgba(48,209,88,.16);color:var(--green)}
.boff{background:rgba(255,69,58,.16);color:var(--red)}

/* Notes */
.note{padding:10px 14px;border-radius:12px;font-size:12.5px}
.nw{background:rgba(255,214,10,.10);color:#ffe066;border:1px solid rgba(255,214,10,.18)}
.nl{background:rgba(255,69,58,.12);color:#ff7a70;border:1px solid rgba(255,69,58,.22)}
.ns{background:rgba(255,255,255,.04);color:var(--text2);border:1px solid var(--stroke2)}

/* Run button — colours set by JS (blue = dry run, red = live) */
#runBtn{
  width:100%;padding:16px;font-size:15px;font-weight:600;letter-spacing:-.01em;
  border-radius:16px;border:none;cursor:pointer;font-family:inherit;color:#fff;
  box-shadow:0 8px 24px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.25);
  transition:filter .2s, transform .1s, background .25s;
}
#runBtn:hover:not(:disabled){filter:brightness(1.1)}
#runBtn:active:not(:disabled){transform:scale(.985)}
#runBtn:disabled{cursor:not-allowed;box-shadow:none}

/* Log */
.ltop{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.ltop .lbl{margin:0}
.smbtn{
  background:rgba(255,255,255,.08);border:none;color:var(--text2);font-size:12px;
  cursor:pointer;padding:5px 12px;border-radius:8px;font-family:inherit;
}
.smbtn:hover{color:var(--text);background:rgba(255,255,255,.14)}
#log{
  background:rgba(0,0,0,.3);border:1px solid var(--stroke2);border-radius:14px;
  padding:16px;height:300px;overflow-y:auto;
  font-family:"SF Mono",Menlo,Consolas,monospace;font-size:11.5px;line-height:1.7;
  white-space:pre-wrap;word-break:break-word;color:rgba(255,255,255,.75);
}

/* Custom folder panel */
#customSection{display:none;padding:20px 22px;border-color:rgba(255,214,10,.3)}
.ct{font-size:14px;font-weight:600;color:#ffe066;margin-bottom:12px}
.sl2{
  background:rgba(0,0,0,.25);border-radius:12px;padding:10px 14px;margin-bottom:16px;
  font-family:"SF Mono",Menlo,Consolas,monospace;font-size:11.5px;color:var(--text2);
  max-height:120px;overflow-y:auto;border:1px solid var(--stroke2);
}
.si{padding:2px 0}
.cf{display:flex;flex-direction:column;gap:14px}
.cf label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:8px}
.ci{
  width:100%;background:rgba(0,0,0,.25);border:1px solid var(--stroke2);border-radius:12px;
  padding:11px 14px;font-size:13px;color:var(--text);outline:none;font-family:inherit;
  transition:border-color .2s, box-shadow .2s;
}
.ci:focus{border-color:var(--amber);box-shadow:0 0 0 4px rgba(255,214,10,.15)}
.ci::placeholder{color:var(--text3)}
.cr{display:flex;gap:10px;align-items:flex-start}
#addBtn{
  background:var(--amber);color:#1c1c1e;border:none;border-radius:12px;font-size:13px;
  font-weight:700;padding:12px 20px;cursor:pointer;font-family:inherit;white-space:nowrap;
  transition:filter .2s;
}
#addBtn:hover:not(:disabled){filter:brightness(1.08)}
#addBtn:disabled{opacity:.4;cursor:not-allowed}
.cn{font-size:11.5px;color:var(--text3);margin-top:6px;line-height:1.5}
#confirmBox{
  display:none;padding:16px;border-radius:14px;background:rgba(10,132,255,.08);
  border:1px solid rgba(10,132,255,.35);font-size:12.5px;line-height:1.6;
}
.cm{margin-bottom:12px}
.cbs{display:flex;gap:8px}
.cy{background:var(--blue);color:#fff;border:none;border-radius:10px;padding:8px 18px;font-weight:600;cursor:pointer;font-size:12.5px;font-family:inherit}
.cn2{background:rgba(255,255,255,.1);color:var(--text);border:none;border-radius:10px;padding:8px 18px;font-weight:600;cursor:pointer;font-size:12.5px;font-family:inherit}
.cy:hover,.cn2:hover{filter:brightness(1.15)}

/* Floating status pill */
.sbar{
  position:fixed;bottom:18px;left:50%;transform:translateX(-50%);
  display:flex;align-items:center;gap:10px;padding:10px 18px;border-radius:30px;
  font-size:12.5px;color:var(--text2);max-width:calc(100% - 40px);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;box-shadow:0 0 10px currentColor}

::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:3px}
</style>
</head>
<body>
<div class="wrap">

  <!-- Header -->
  <div class="glass hdr">
    <div class="logo">&#128230;</div>
    <div>
      <h1>File Manager</h1>
      <p>Create folders &middot; Sort &middot; Sub-sort &middot; Compress</p>
    </div>
  </div>

  <!-- Source folder -->
  <div class="glass sec">
    <div class="lbl">Source Folder</div>
    <div class="row">
      <input class="fin" type="text" id="fi" placeholder="Paste a folder path or click Browse"/>
      <button class="btn" id="bb" onclick="doBrowse()">Browse</button>
    </div>
  </div>

  <!-- Options -->
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

  <!-- Run -->
  <button id="runBtn" style="background:#0A84FF;" onclick="doRun()">
    Run File Manager (Dry Run - Preview only)
  </button>

  <!-- Log -->
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

  <!-- Custom folder panel -->
  <div class="glass" id="customSection">
    <div class="ct">&#9888;&#65039; Unmatched Files &middot; <span id="skipCount">0</span> file(s) not sorted</div>
    <div class="sl2" id="skipList"></div>
    <div class="cf">
      <div>
        <label>Folder Name</label>
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

<!-- Status pill -->
<div class="glass sbar">
  <div class="dot" id="dot" style="background:#30D158;color:#30D158"></div>
  <span id="st">Ready</span>
</div>

<script>
var BLUE="#0A84FF", RED="#FF453A", GREEN="#30D158";
var _dry=true,_subsort=true,_poll=null,_len=0,_pn="",_ps="";

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
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;btn.disabled=false;btn.innerText="Browse";
    if(x.status===200){try{var d=JSON.parse(x.responseText);if(d.path&&d.path.length>0){document.getElementById("fi").value=d.path;setSt("Folder: "+d.path);}else{setSt("No folder selected.");}}catch(e){setSt("Paste the path manually.");}}
  };x.open("GET","/browse",true);x.send();
}
function doClear(){document.getElementById("log").innerText="";_len=0;}
function addLog(t){var e=document.getElementById("log");e.innerText+=t;e.scrollTop=e.scrollHeight;}
function setSt(t){document.getElementById("st").innerText=t||"Ready";}
function setDot(c){var d=document.getElementById("dot");d.style.background=c;d.style.color=c;}
function checkSkipped(){
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4||x.status!==200)return;
    var d;try{d=JSON.parse(x.responseText);}catch(e){return;}
    var f=d.files||[],s=document.getElementById("customSection"),l=document.getElementById("skipList"),c=document.getElementById("skipCount");
    if(f.length>0){s.style.display="block";c.innerText=f.length;var h="";for(var i=0;i<f.length;i++){h+="<div class='si'>&bull; "+f[i]+"</div>";}l.innerHTML=h;}
    else{s.style.display="none";}
  };x.open("GET","/skipped",true);x.send();
}
function showConfirm(n,s,m){
  _pn=n;_ps=s;document.getElementById("confirmMsg").innerHTML=m;
  document.getElementById("confirmYes").onclick=function(){submitFolder(_pn,_ps);};
  document.getElementById("confirmBox").style.display="block";
}
function hideConfirm(){document.getElementById("confirmBox").style.display="none";_pn="";_ps="";}
function submitFolder(name,sv){
  hideConfirm();var btn=document.getElementById("addBtn");btn.disabled=true;btn.innerText="Creating...";setSt("Creating: "+name+"...");
  var b="name="+encodeURIComponent(name)+"&size="+encodeURIComponent(sv);
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;btn.disabled=false;btn.innerText="Create & Sort";
    if(x.status===200){
      document.getElementById("customName").value="";document.getElementById("customSize").value="";
      addLog("\nCreating: "+name+"...\n");
      var pt=setInterval(function(){
        var px=new XMLHttpRequest();
        px.onreadystatechange=function(){
          if(px.readyState!==4||px.status!==200)return;var pd;try{pd=JSON.parse(px.responseText);}catch(e){return;}
          if(pd.log&&pd.log.length>_len){addLog(pd.log.substring(_len));_len=pd.log.length;}
          if(!pd.busy){clearInterval(pt);setSt("Folder created!");setDot(GREEN);checkSkipped();}
        };px.open("GET","/poll",true);px.send();
      },700);
    }
  };x.open("POST","/add-folder",true);x.setRequestHeader("Content-Type","application/x-www-form-urlencoded");x.send(b);
}
function doAddFolder(){
  var name=document.getElementById("customName").value.trim(),sv=document.getElementById("customSize").value.trim();
  hideConfirm();if(!name){alert("Please enter a folder name.");return;}setSt("Checking...");
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;if(x.status!==200){submitFolder(name,sv);return;}
    var d;try{d=JSON.parse(x.responseText);}catch(e){submitFolder(name,sv);return;}setSt("");
    if(d.exists){addLog("\nFolder \""+d.matched+"\" found in "+(d.source==="custom"?"custom list":"built-in list")+". Proceeding...\n");submitFolder(name,sv);}
    else{var m="<strong style=\"color:#ff7a70\">\""+name+"\" is not in the folder list.</strong><br><br>This will create the folder, move matching files into it, and save it permanently.<br><br>Create anyway?";showConfirm(name,sv,m);}
  };x.open("GET","/check-folder?name="+encodeURIComponent(name),true);x.send();
}
function doPoll(){
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4||x.status!==200)return;var d;try{d=JSON.parse(x.responseText);}catch(e){return;}
    if(d.log&&d.log.length>_len){addLog(d.log.substring(_len));_len=d.log.length;}
    if(d.busy===false&&_poll!==null){clearInterval(_poll);_poll=null;setBusy(false);setDot(GREEN);setSt(_dry?"Dry run done. Turn off Dry Run to apply.":"Done! All files processed.");checkSkipped();}
  };x.open("GET","/poll",true);x.send();
}
function setBusy(on){
  var btn=document.getElementById("runBtn");btn.disabled=on;
  if(on){btn.style.background="rgba(255,255,255,.1)";btn.style.color="rgba(255,255,255,.45)";btn.innerText="Running...";setDot(BLUE);}
  else{btn.style.background=_dry?BLUE:RED;btn.style.color="#fff";updBtn();}
}
function doRun(){
  var f=document.getElementById("fi").value.trim();
  if(!f.length){alert("Please select a folder first.");return;}
  if(!_dry&&!confirm("Dry Run is OFF.\n\nFiles will be MOVED and COMPRESSED.\nThis cannot be undone.\n\nProceed?"))return;
  doClear();_len=0;hideConfirm();document.getElementById("customSection").style.display="none";
  setBusy(true);setSt("Running...");
  addLog((_dry?"DRY RUN":"LIVE RUN")+" - "+f+"\nSub-sort: "+(_subsort?"ON":"OFF")+"\n\n");
  var b="folder="+encodeURIComponent(f)+"&dry="+(_dry?"1":"0")+"&subsort="+(_subsort?"1":"0");
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4)return;
    if(x.status===200){_poll=setInterval(doPoll,700);}
    else{addLog("Error: server did not respond.\n");setBusy(false);setSt("Error");setDot(RED);}
  };x.open("POST","/run",true);x.setRequestHeader("Content-Type","application/x-www-form-urlencoded");x.send(b);
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
        width            = 860,
        height           = 780,
        min_size         = (720, 600),
        resizable        = True,
        background_color = "#0a0a12",
    )
    webview.start(debug=False)
    print("\n  File Manager closed. Goodbye!\n")


if __name__ == "__main__":
    main()
