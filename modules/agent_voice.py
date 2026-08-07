#!/usr/bin/env python3
"""Local-AI Standalone Voice to Text Module"""

import base64, fcntl, http.server, json, os, re, readline, select, socket, socketserver, ssl, subprocess, sys, termios, threading, time, urllib.request as urlreq
from typing import Tuple

PORT = 9999
CFG_DIR = os.path.expanduser("~/.config/local-ai")
PENDING_FILE = os.path.join(CFG_DIR, ".voice_pending.txt")

try:
    import agent_core as core
except ImportError:
    core = None

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice to Text</title>
    <style>
        body { background: #000; color: #c0caf5; font-family: monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; user-select: none; }
        button { width: 220px; height: 220px; border-radius: 50%; border: 2px solid #7aa2f7; background: #000; color: #7aa2f7; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.2s; outline: none; }
        #status { margin-top: 35px; font-size: 12px; color: #565f89; text-transform: uppercase; letter-spacing: 2px; }
        #result { margin-top: 15px; font-size: 18px; color: #9ece6a; text-align: center; max-width: 85%; min-height: 40px; }
    </style>
</head>
<body>
    <button id="mic-btn">HOLD TO SPEAK</button>
    <div id="status">Ready</div>
    <div id="result"></div>
    <script>
        const btn = document.getElementById('mic-btn'), status = document.getElementById('status'), result = document.getElementById('result');
        let mediaRecorder, audioChunks = [];
        navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                status.innerText = "Transcribing...";
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                audioChunks = [];
                fetch('/upload', { method: 'POST', body: audioBlob }).then(r => r.text()).then(text => {
                    result.innerText = text ? `"${text}"` : "Silence detected.";
                    status.innerText = "Executed.";
                }).catch(() => { status.innerText = "Transmission failed."; });
            };
        }).catch(() => { status.innerText = "Mic Permission Blocked"; btn.style.borderColor = "#f7768e"; });
        btn.addEventListener('pointerdown', e => { e.preventDefault(); if (mediaRecorder?.state === "inactive") { mediaRecorder.start(); status.innerText = "Listening..."; btn.style.background = "#7aa2f7"; btn.style.color = "#000"; } });
        const stopRec = e => { if (e) e.preventDefault(); if (mediaRecorder?.state === "recording") { mediaRecorder.stop(); btn.style.background = "#000"; btn.style.color = "#7aa2f7"; } };
        btn.addEventListener('pointerup', stopRec); btn.addEventListener('pointercancel', stopRec); btn.addEventListener('mouseleave', stopRec);
        btn.addEventListener('contextmenu', e => e.preventDefault());
    </script>
</body>
</html>
"""

_voice_proc = None
_auto_submit = True


def is_bridge_running() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex(("127.0.0.1", PORT)) == 0
    except OSError:
        return False


def load_voice_env() -> None:
    env_path = os.path.join(CFG_DIR, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if (s := line.strip()) and not s.startswith("#") and "=" in s:
                        k, v = s.replace("export ", "", 1).split("=", 1)
                        if k := k.strip():
                            os.environ[k] = v.split(" #")[0].strip().strip('"').strip("'")
        except OSError: pass


def transcribe_gemini(audio_data: bytes) -> str:
    load_voice_env()
    gkey = os.environ.get("GEM_VOICE") or os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEM_MODEL") or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not gkey:
        sys.stderr.write("[error] GEM_VOICE key is not set in ~/.config/local-ai/.env\n"); sys.stderr.flush()
        return ""

    encoded = base64.b64encode(audio_data).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gkey}"
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "audio/webm", "data": encoded}},
                {"text": "Transcribe this audio verbatim. Output ONLY plain text, no commentary or markdown formatting."}
            ]
        }]
    }
    try:
        req = urlreq.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urlreq.urlopen(req, timeout=10) as resp:
            try:
                with open(os.path.join(CFG_DIR, ".request_log"), "a", encoding="utf-8") as lf:
                    lf.write(f"{int(time.time())}|gemini\n")
            except OSError: pass
            res_data = json.loads(resp.read().decode("utf-8"))
            raw = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return re.sub(r'[^a-zA-Z0-9\s?.,!\'-]', '', raw).strip()
    except Exception as e:
        sys.stderr.write(f"[error] Transcription failed: {e}\n"); sys.stderr.flush()
        return ""


def get_prompt_input(symbol: str = "❯") -> str:
    global _auto_submit
    if core:
        _auto_submit = core.get_state().get("voice_auto_submit", True)

    sys.stdout.write(f"\001\033[1;30m\002{symbol}\001\033[0m\002 ")
    sys.stdout.flush()
    while True:
        if os.path.exists(PENDING_FILE) and os.path.getsize(PENDING_FILE) > 0:
            try:
                with open(PENDING_FILE, "r", encoding="utf-8") as vf:
                    if text := vf.read().strip():
                        os.remove(PENDING_FILE)
                        if _auto_submit:
                            sys.stdout.write(f"{text}\n"); sys.stdout.flush()
                            return text
                        else:
                            try: readline.set_startup_hook(lambda: readline.insert_text(text))
                            except Exception: pass
                            sys.stdout.write("\r\033[K")
                            return input(f"\001\033[1;30m\002{symbol}\001\033[0m\002 ").strip()
            except OSError: pass
        if select.select([sys.stdin], [], [], 0.1)[0]:
            return sys.stdin.readline().strip()


class VoiceHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def do_POST(self):
        try:
            if self.path == "/upload":
                length = int(self.headers.get("Content-Length", 0))
                audio_data = self.rfile.read(length)
                query = transcribe_gemini(audio_data) if audio_data else ""
                if query:
                    sys.stderr.write(f"[sys] Transcribed: {query}\n"); sys.stderr.flush()
                    with open(PENDING_FILE, "w", encoding="utf-8") as f:
                        f.write(query)

                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(query.encode("utf-8"))
        except Exception as e:
            sys.stderr.write(f"[error] Server error: {e}\n"); sys.stderr.flush()
            self.send_response(500); self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode("utf-8"))


def run_server() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("8.8.8.8", 80)); local_ip = s.getsockname()[0]
    except Exception: local_ip = "127.0.0.1"
    finally: s.close()

    cert_path = os.path.join(CFG_DIR, "server.pem")
    if not os.path.exists(cert_path):
        subprocess.run(f'openssl req -new -x509 -keyout "{cert_path}" -out "{cert_path}" -days 365 -nodes -subj "/CN={local_ip}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), VoiceHandler) as httpd:
        if os.path.exists(cert_path):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=cert_path)
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

        print(f"[ok] Voice to Text active: https://{local_ip}:{PORT}")
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\n[sys] Server stopped.")


def toggle_voice_bridge(auto_toggle: bool = False) -> Tuple[bool, bool]:
    global _voice_proc, _auto_submit
    if core:
        _auto_submit = core.get_state().get("voice_auto_submit", True)

    is_running = is_bridge_running()

    if auto_toggle and is_running:
        _auto_submit = not _auto_submit
        if core: core.save_state("voice_auto_submit", _auto_submit)
        return True, _auto_submit

    if is_running:
        if _voice_proc:
            try: _voice_proc.terminate()
            except OSError: pass
        subprocess.run(["pkill", "-f", "agent_voice.py"], stderr=subprocess.DEVNULL)
        _voice_proc = None
        return False, _auto_submit
    else:
        mod_path = os.path.abspath(__file__)
        _voice_proc = subprocess.Popen(
            [sys.executable, mod_path, "--server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True, _auto_submit


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        run_server()
    else:
        toggle_voice_bridge()
