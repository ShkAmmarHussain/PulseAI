import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

APPDATA = Path(os.environ["APPDATA"]) / "JarvisDesktopPet"
MODELS = APPDATA / "models"
WAKE = APPDATA / "wakeword_models"
TMP = Path(r"D:\Personal_projects\2\Personal_AI")

# ---------- 1. Kokoro synthesis ----------
t0 = time.time()
from kokoro_onnx import Kokoro

k = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
t_load = time.time() - t0
t0 = time.time()
samples, sr = k.create("Good day. How may I assist you today?", voice="af_heart", speed=1.0, lang="en-us")
t_gen = time.time() - t0
print(f"KOKORO: load={t_load:.2f}s gen={t_gen:.2f}s dur={len(samples)/sr:.2f}s sr={sr}")

# sanity: not silence
rms = float(np.sqrt(np.mean(np.square(samples))))
print("KOKORO rms:", round(rms, 4), "OK" if rms > 0.01 else "SILENT!")

wav_path = TMP / "kokoro_test.wav"
with wave.open(str(wav_path), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())
print("wrote", wav_path)

# validate candidate voices for the settings picker
candidates = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_alloy",
    "am_michael", "am_fenrir", "am_puck", "am_echo", "am_onyx", "am_adam",
    "bf_emma", "bm_george", "bm_lewis",
]
ok_v = []
for v in candidates:
    try:
        s, _sr = k.create("hi", voice=v, lang="en-us")
        if len(s) > 100:
            ok_v.append(v)
    except Exception as e:
        print("voice fail:", v, str(e)[:60])
print("VOICES OK:", ok_v)

# ---------- 2. SAPI clips for wake tests ----------
def sapi_wav(text, path):
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f'$s.SetOutputToWaveFile("{path}"); '
        f'$s.Speak("{text}"); $s.Dispose()'
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("sapi failed: " + r.stderr[:300])


pos_path = TMP / "wake_pos.wav"
neg_path = TMP / "wake_neg.wav"
sapi_wav("Hey Jarvis, what time is it?", str(pos_path))
sapi_wav("The quick brown fox jumps over the lazy dog again and again", str(neg_path))


def to_16k_int16(path):
    w = wave.open(str(path), "rb")
    sr_, n = w.getframerate(), w.getnframes()
    data = np.frombuffer(w.readframes(n), dtype=np.int16)
    if w.getnchannels() > 1:
        data = data.reshape(-1, w.getnchannels()).mean(axis=1).astype(np.int16)
    if sr_ != 16000:
        idx = np.linspace(0, len(data) - 1, int(len(data) * 16000 / sr_))
        data = np.interp(idx, np.arange(len(data)), data).astype(np.int16)
    w.close()
    return data


# ---------- 3. openWakeWord ----------
from openwakeword.model import Model

t0 = time.time()
m = Model(
    wakeword_models=["hey jarvis"],
    vad_threshold=0.5,
    inference_framework="onnx",
)
print(f"WAKE model load: {time.time()-t0:.2f}s")

pos = to_16k_int16(pos_path)
neg = to_16k_int16(neg_path)

# predict in 1600-sample (100ms) frames like the live service will
def scores(audio):
    out = []
    for i in range(0, len(audio) - 1599, 1600):
        p = m.predict(audio[i:i + 1600])
        out.append(max(p.values()))
    return out


sp = scores(pos)
m.reset()
sn = scores(neg)
print("WAKE pos max score:", round(max(sp), 3), "per-frame:", [round(x, 2) for x in sp])
print("WAKE neg max score:", round(max(sn), 3))
print("VERDICT:", "PASS" if max(sp) >= 0.5 and max(sn) < 0.5 else "NEEDS TUNING")
