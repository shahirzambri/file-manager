#!/usr/bin/env python3
"""
File Manager — Desktop UI using PyWebView
Opens as a proper desktop window — no browser needed.
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

try:
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
except Exception:
    pass

# ── Import core script ───────────────────────────────────────
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

# ── Import PyWebView ─────────────────────────────────────────
try:
    import webview
    WEBVIEW_OK = True
except ImportError:
    WEBVIEW_OK = False
    print("PyWebView not installed. Run: pip3 install pywebview")

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
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if parts:
                        try:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", parts[-1]],
                                capture_output=True
                            )
                        except Exception:
                            pass
        else:
            result = subprocess.run(
                ["lsof", "-ti", ":" + str(port)],
                capture_output=True, text=True
            )
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


# ──────────────────────────────────────────────────────────────
#  OUTPUT CAPTURE
# ──────────────────────────────────────────────────────────────

class Cap:
    def write(self, t):
        with _lock:
            _log.append(str(t))
    def flush(self):
        pass


# ──────────────────────────────────────────────────────────────
#  SERVER
# ──────────────────────────────────────────────────────────────

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
        self.respond(200, "text/html; charset=utf-8",
                     page.encode("utf-8"))

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
        r    = (check_folder_exists(name)
                if MANAGER_OK and name
                else {"exists": False, "source": "none", "matched": ""})
        self.respond(200, "application/json", json.dumps(r).encode())

    def serve_browse(self):
        """
        Open native folder picker.
        Uses PyWebView dialog if available — cleaner than osascript.
        Falls back to osascript on Mac and PowerShell on Windows.
        """
        path = ""
        try:
            if WEBVIEW_OK:
                # PyWebView native folder picker
                result = webview.windows[0].create_file_dialog(
                    webview.FOLDER_DIALOG
                )
                if result and len(result) > 0:
                    path = result[0]
            elif sys.platform == "win32":
                ps = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "$f.Description = 'Select your source folder'; "
                    "if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath }"
                )
                r = subprocess.run(
                    ["powershell", "-Command", ps],
                    capture_output=True, text=True, timeout=120
                )
                path = r.stdout.strip()
            else:
                r = subprocess.run(
                    ["osascript", "-e",
                     "POSIX path of (choose folder with prompt "
                     "\"Select your source folder:\")"],
                    capture_output=True, text=True, timeout=120
                )
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
        threading.Thread(
            target=self.task,
            args=(folder, dry, subsort),
            daemon=True
        ).start()

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
        threading.Thread(
            target=self.custom_task,
            args=(name, max_kb),
            daemon=True
        ).start()

    def task(self, folder, dry, subsort):
        global _log, _busy
        with _lock:
            _log  = []
            _busy = True
        old        = sys.stdout
        sys.stdout = Cap()
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
        old        = sys.stdout
        sys.stdout = Cap()
        try:
            if MANAGER_OK:
                r = create_custom_folder(name, max_kb, dry_run=False)
                if "error" in r:
                    print(f"\n  Error: {r['error']}\n")
            else:
                print("file_manager.py not found!")
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
#  HTML PAGE
# ──────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>File Manager</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;background:#16161e;color:#c0caf5;min-height:100vh;padding-bottom:54px}
.hdr{background:#1f2335;padding:22px 20px;text-align:center;border-bottom:1px solid #292e42;-webkit-app-region:drag}
.hdr h1{font-size:22px;font-weight:700;margin-bottom:5px}
.hdr p{font-size:12px;color:#565f89}
.wrap{max-width:740px;margin:0 auto;padding:24px 20px}
.lbl{font-size:11px;font-weight:700;color:#7aa2f7;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.sub{font-size:12px;color:#565f89;margin-bottom:10px}
.row{display:flex;gap:8px;margin-bottom:18px}
.fin{flex:1;background:#1f2335;border:1px solid #292e42;border-radius:8px;padding:11px 14px;font-size:13px;font-family:"Menlo",monospace;color:#c0caf5;outline:none}
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
#log{background:#1f2335;border:1px solid #292e42;border-radius:10px;padding:16px;height:300px;overflow-y:auto;font-family:"Menlo",monospace;font-size:11.5px;line-height:1.7;white-space:pre-wrap;word-break:break-word;color:#a9b1d6}
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
<div class="hdr">
  <h1>&#128230; File Manager</h1>
  <p>Auto-create folders &nbsp;&middot;&nbsp; Sort &nbsp;&middot;&nbsp; Sub-sort &nbsp;&middot;&nbsp; Compress</p>
</div>
<div class="wrap">
  <div class="lbl">Source Folder</div>
  <div class="sub">Click Browse to pick your folder, or paste the path</div>
  <div class="row">
    <input class="fin" type="text" id="fi" placeholder="Paste folder path here, or click Browse..."/>
    <button class="btn" id="bb" onclick="doBrowse()">Browse</button>
  </div>
  <div class="card">
    <div class="crow">
      <label class="sw"><input type="checkbox" id="dc" checked onchange="onDry()"><span class="sl"></span></label>
      <div class="cinfo"><h3>Dry Run</h3><p>Preview only - nothing will be moved or compressed</p></div>
      <span class="bdg bon" id="bdg">ON</span>
    </div>
    <div class="note nw" id="nt">Dry Run is ON - safe to run, no files will change</div>
    <div class="divrow">
      <div class="crow">
        <label class="sw"><input type="checkbox" id="sc" checked onchange="onSubsort()"><span class="sl"></span></label>
        <div class="cinfo"><h3>Sub-sort by Dimensions</h3><p>Group files into sub-folders by image size e.g. 1200x628/</p></div>
        <span class="bdg bon" id="sbdg">ON</span>
      </div>
      <div class="note ns" id="snt">Sub-sort is ON - files will be grouped by image dimensions</div>
    </div>
  </div>
  <button id="runBtn" style="background:#7aa2f7;color:#16161e;" onclick="doRun()">
    Run File Manager (Dry Run - Preview only)
  </button>
  <div class="ltop">
    <div class="lbl" style="margin:0">Output Log</div>
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

Options:
  Dry Run  - preview without changing anything
  Sub-sort - toggle dimension sub-folder grouping
</div>
  <div id="customSection">
    <div class="ct">&#9888; Unmatched Files - <span id="skipCount">0</span> file(s) not sorted</div>
    <div class="sl2" id="skipList"></div>
    <div class="cf">
      <div>
        <label>Folder Name</label>
        <input class="ci" type="text" id="customName" placeholder="e.g. XYZ BRAND"/>
        <div class="cn">Files whose names contain this keyword will be moved into this folder. Saved permanently.</div>
      </div>
      <div>
        <label>Max File Size in KB - optional</label>
        <div class="cr">
          <div style="flex:1">
            <input class="ci" type="number" id="customSize" placeholder="Leave blank = no size limit"/>
            <div class="cn">500=500KB | 1024=1MB | blank=keep original</div>
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
<div class="sbar">
  <div class="dot" id="dot" style="background:#9ece6a"></div>
  <span id="st">Ready</span>
</div>
<script>
var _dry=true,_subsort=true,_poll=null,_len=0,_pn="",_ps="";
function onDry(){
  _dry=document.getElementById("dc").checked;
  var b=document.getElementById("bdg"),n=document.getElementById("nt"),btn=document.getElementById("runBtn");
  if(_dry){b.className="bdg bon";b.innerText="ON";n.className="note nw";n.innerText="Dry Run is ON - safe to run, no files will change";btn.style.background="#7aa2f7";btn.style.color="#16161e";}
  else{b.className="bdg boff";b.innerText="OFF";n.className="note nl";n.innerText="Dry Run is OFF - files WILL be moved and compressed!";btn.style.background="#f7768e";btn.style.color="#16161e";}
  updBtn();
}
function onSubsort(){
  _subsort=document.getElementById("sc").checked;
  var b=document.getElementById("sbdg"),n=document.getElementById("snt");
  if(_subsort){b.className="bdg bon";b.innerText="ON";n.innerText="Sub-sort is ON - files grouped by dimensions";}
  else{b.className="bdg boff";b.innerText="OFF";n.innerText="Sub-sort is OFF - files stay in parent folder";}
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
    if(x.status===200){try{var d=JSON.parse(x.responseText);if(d.path&&d.path.length>0){document.getElementById("fi").value=d.path;setSt("Folder: "+d.path);}else{setSt("No folder selected. Paste the path manually.");}}catch(e){setSt("Paste the path manually.");}}
  };x.open("GET","/browse",true);x.send();
}
function doClear(){document.getElementById("log").innerText="";_len=0;}
function addLog(t){var e=document.getElementById("log");e.innerText+=t;e.scrollTop=e.scrollHeight;}
function setSt(t){document.getElementById("st").innerText=t;}
function setDot(c){document.getElementById("dot").style.background=c;}
function checkSkipped(){
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4||x.status!==200)return;
    var d;try{d=JSON.parse(x.responseText);}catch(e){return;}
    var f=d.files||[],s=document.getElementById("customSection"),l=document.getElementById("skipList"),c=document.getElementById("skipCount");
    if(f.length>0){s.style.display="block";c.innerText=f.length;var h="";for(var i=0;i<f.length;i++){h+="<div class='si'>- "+f[i]+"</div>";}l.innerHTML=h;}
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
          if(!pd.busy){clearInterval(pt);setSt("Folder created!");setDot("#9ece6a");checkSkipped();}
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
    else{var m="<strong style=\"color:#f7768e\">\""+name+"\" is not in the folder list.</strong><br><br>This will:<br>- Create folder \""+name+"\"<br>- Move matching files<br>- Save permanently<br><br>Create anyway?";showConfirm(name,sv,m);}
  };x.open("GET","/check-folder?name="+encodeURIComponent(name),true);x.send();
}
function doPoll(){
  var x=new XMLHttpRequest();
  x.onreadystatechange=function(){
    if(x.readyState!==4||x.status!==200)return;var d;try{d=JSON.parse(x.responseText);}catch(e){return;}
    if(d.log&&d.log.length>_len){addLog(d.log.substring(_len));_len=d.log.length;}
    if(d.busy===false&&_poll!==null){clearInterval(_poll);_poll=null;setBusy(false);setDot("#9ece6a");setSt(_dry?"Dry run done. Turn off Dry Run to apply.":"Done! All files processed.");checkSkipped();}
  };x.open("GET","/poll",true);x.send();
}
function setBusy(on){
  var btn=document.getElementById("runBtn");btn.disabled=on;
  if(on){btn.style.background="#292e42";btn.style.color="#565f89";btn.innerText="Running...";setDot("#7aa2f7");}
  else{btn.style.background=_dry?"#7aa2f7":"#f7768e";btn.style.color="#16161e";updBtn();}
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
    else{addLog("Error: server did not respond.\n");setBusy(false);setSt("Error");setDot("#f7768e");}
  };x.open("POST","/run",true);x.setRequestHeader("Content-Type","application/x-www-form-urlencoded");x.send(b);
}
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
#  MAIN — PyWebView Desktop Window
# ──────────────────────────────────────────────────────────────

def start_server():
    """Start HTTP server in background thread."""
    free_port(PORT)
    for _ in range(10):
        if port_free(PORT):
            break
        time.sleep(0.5)
    server = Server(("", PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def wait_for_server(port, timeout=10):
    """Wait until server is actually responding."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1)
            s.close()
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    try:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
    except Exception:
        pass

    if not WEBVIEW_OK:
        print("PyWebView not installed.")
        print("Run: pip3 install pywebview")
        sys.exit(1)

    url = f"http://localhost:{PORT}"

    print("")
    print("  File Manager starting...")
    print("  " + "-" * 40)

    # Start server in background
    start_server()

    # Wait for server to be ready
    if not wait_for_server(PORT):
        print("  ERROR: Server failed to start.")
        sys.exit(1)

    print("  Server ready. Opening desktop window...")
    print("  " + "-" * 40 + "\n")

    # Create desktop window using PyWebView
    window = webview.create_window(
        title          = "File Manager",
        url            = url,
        width          = 820,
        height         = 700,
        min_size       = (720, 600),
        resizable      = True,
        on_top         = False,
        shadow         = True,
        background_color = "#16161e",
    )

    # Start PyWebView — this blocks until window is closed
    webview.start(debug=False)

    print("\n  File Manager closed. Goodbye!\n")


if __name__ == "__main__":
    main()
