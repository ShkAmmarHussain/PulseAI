import asyncio
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

WAV = Path(r"D:\Personal_projects\2\Personal_AI\tmp_voice.wav")

# --- STT test: SAPI speech -> wav -> transcribe ---
ps = (
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    f'$s.SetOutputToWaveFile("{WAV}"); '
    '$s.Speak("Hello Jarvis, what time is it today?"); '
    "$s.Dispose()"
)
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
if r.returncode != 0:
    raise SystemExit("TTS wav failed: " + r.stderr[:300])
w = wave.open(str(WAV), "rb")
sr, n = w.getframerate(), w.getnframes()
data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
if sr != 16000:
    idx = np.linspace(0, len(data) - 1, int(len(data) * 16000 / sr))
    data = np.interp(idx, np.arange(len(data)), data).astype(np.float32)
print("wav:", sr, "Hz,", round(len(data) / 16000, 2), "s")

from faster_whisper import WhisperModel

m = WhisperModel("base", device="cpu", compute_type="int8")
segs, _ = m.transcribe(data, vad_filter=True)
txt = " ".join(s.text for s in segs).strip()
print("STT:", repr(txt))
assert "time" in txt.lower() or "jarvis" in txt.lower(), "STT mismatch"

# --- TTS test ---
from core.bus import MessageBus, create_event
from agents.voice_tts import VoiceTTSAgent


async def t():
    bus = MessageBus()
    a = VoiceTTSAgent(bus)
    await a.start()
    bus.start()
    await bus.publish(create_event("voice.say", "say", {"text": "Voice system online. Hello."}))
    await asyncio.sleep(4)


asyncio.run(t())
print("TTS played (audio out)")

# --- voice input pipeline: audio.input.voice -> ui.chat ---
from core.config import load_config
from backend.app import App


async def p():
    app = App()
    await app.start()
    got = []

    async def listen(ev):
        if ev.topic == "ui.chat":
            got.append(ev.payload)

    app.bus.subscribe("ui.chat", listen)
    await app.bus.publish(create_event("audio.input.voice", "voice", {"text": "hello there"}, source="voice"))
    await asyncio.sleep(25)
    roles = [(g.get("role"), (g.get("text") or "")[:60]) for g in got]
    print("PIPELINE:", roles)
    assert any(r[0] == "user" for r in roles), "no user echo"
    assert any(r[0] == "assistant" for r in roles), "no assistant reply"
    return roles


asyncio.run(p())
print("ALL OK")
