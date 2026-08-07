#!/usr/bin/env python3
"""Local-AI Kokoro Text-to-Speech (Text Out Loud) Module"""

import os, re, subprocess, sys, threading

CFG_DIR = os.path.expanduser("~/.config/local-ai")
VOICE_FILE = os.path.expanduser("~/.config/koko_current_voice")

try:
    import agent_core as core
except ImportError:
    core = None


def stop_tts() -> None:
    subprocess.run("pkill -9 -f 'pw-play|koko'", shell=True, stderr=subprocess.DEVNULL)


def is_tts_enabled() -> bool:
    if core:
        return core.get_state().get("tts_enabled", False)
    return False


def speak_text(text: str) -> None:
    if not text: return
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    clean = re.sub(r'```.*?```', 'code block omitted', clean, flags=re.DOTALL)
    clean = re.sub(r'[*_#`~>\[\]()|]', '', clean).strip()
    if not clean: return

    def _run():
        stop_tts()
        voice = "am_echo"
        if os.path.exists(VOICE_FILE):
            try:
                with open(VOICE_FILE, "r", encoding="utf-8") as f:
                    if v := f.read().strip(): voice = v
            except OSError: pass

        wav_path = "/dev/shm/tts.wav"
        escaped_text = clean.replace('"', '\\"')
        cmd = f'OMP_NUM_THREADS=6 koko --style "{voice}" --speed 1.15 text "{escaped_text}" -o {wav_path} && pw-play {wav_path}'
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    threading.Thread(target=_run, daemon=True).start()


def speak_response(text: str) -> None:
    if is_tts_enabled():
        speak_text(text)


def toggle_tts() -> bool:
    new_state = not is_tts_enabled()
    if not new_state:
        stop_tts()
    if core:
        core.save_state("tts_enabled", new_state)
    return new_state
