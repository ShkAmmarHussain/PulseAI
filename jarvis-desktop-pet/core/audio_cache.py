"""Pre-rendered Kokoro acknowledgment cache (spec 29, section 3.1).

High-frequency stock acknowledgments ("Working on that now.", "Done.", ...)
are rendered once with Kokoro and stored as plain WAVs. Playback reads the
file and streams it straight to the audio device, bypassing neural TTS
synthesis entirely (target: < 35ms to audible start vs ~1400ms synthesis).
"""

import logging
import os
import re
import threading
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

PRE_RENDERED_VOCAL_RESPONSES = {
    "ack.working": "Working on that now.",
    "ack.done": "Done.",
    "ack.listening": "Listening.",
    "ack.stopped": "Stopped.",
    "ack.denied": "Action denied. Nothing was changed.",
    "ack.error": "Something went wrong.",
    "ack.approval": "I need your approval to proceed.",
    "ack.confused": "Could you say that again?",
    "ack.wake": "Hey there.",
    "ack.dictation_start": "Transcribing...",
    "ack.dictation_stop": "Transcribed.",
}

_RENDER_LOCK = threading.Lock()
_RENDERING: set = set()
# text (normalized) -> clip path, built lazily per voice/speed
_INDEX: dict = {}
_INDEX_KEY = None

# how much of the wav header/read cost sits in the playback budget
READ_CHUNK_S = 0.08


def tts_cache_dir() -> Path:
    """Writable clip directory.

    Order: explicit env override -> <cwd>/cache/tts (repo/dev layout, spec 29)
    -> %APPDATA%/JarvisDesktopPet/cache/tts (installed app, cwd may be
    read-only e.g. Program Files).
    """
    env = os.environ.get("JARVIS_TTS_CACHE")
    if env:
        d = Path(env)
        d.mkdir(parents=True, exist_ok=True)
        return d
    try:
        dev = Path.cwd() / "cache" / "tts"
        probe = dev / ".write_test"
        dev.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok")
        probe.unlink()
        return dev
    except OSError:
        d = Path(os.environ.get("APPDATA", str(Path.home()))) / "JarvisDesktopPet" / "cache" / "tts"
        d.mkdir(parents=True, exist_ok=True)
        return d


def normalize(text: str) -> str:
    """Case/punctuation-insensitive form used for stock-phrase matching."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text).lower())).strip()


def _voice_dir(voice: str, speed: float) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(voice or "default"))
    return tts_cache_dir() / f"{safe}_{speed:g}"


def clip_path(key: str, voice: str, speed: float) -> Path:
    return _voice_dir(voice, speed) / f"{key}.wav"


def _norm_index(voice: str, speed: float) -> dict:
    """normalized phrase -> clip path for every fully-rendered stock clip."""
    global _INDEX, _INDEX_KEY
    ik = (voice, speed)
    if _INDEX_KEY == ik and _INDEX:
        return _INDEX
    idx = {}
    vdir = _voice_dir(voice, speed)
    for key, phrase in PRE_RENDERED_VOCAL_RESPONSES.items():
        p = vdir / f"{key}.wav"
        if p.exists():
            idx[normalize(phrase)] = p
    _INDEX, _INDEX_KEY = idx, ik
    return idx


def invalidate() -> None:
    global _INDEX, _INDEX_KEY
    _INDEX, _INDEX_KEY = {}, None


def find_clip(text: str, voice: str, speed: float = 1.0):
    """Path of a pre-rendered clip matching this exact stock phrase, else None."""
    if not text:
        return None
    return _norm_index(voice, speed).get(normalize(text))


def ensure_clips(kokoro, voice: str, speed: float = 1.0) -> int:
    """Render any missing stock clips for this voice. Returns clips rendered.

    Safe to call from a background thread; never raises. Kokoro is the
    caller's already-loaded instance so no second model load happens.
    """
    if kokoro is None:
        return 0
    rendered = 0
    for key, phrase in PRE_RENDERED_VOCAL_RESPONSES.items():
        path = clip_path(key, voice, speed)
        if path.exists() or key in _RENDERING:
            continue
        with _RENDER_LOCK:
            if path.exists():
                continue
            _RENDERING.add(key)
            try:
                samples, sr = kokoro.create(phrase, voice=voice, speed=speed, lang="en-us")
                _write_wav(path, samples, sr)
                rendered += 1
                logger.info("tts cache: rendered %s (%s)", key, voice)
            except Exception:
                logger.exception("tts cache: render failed for %s", key)
            finally:
                _RENDERING.discard(key)
    if rendered:
        invalidate()
    return rendered


def ensure_clips_async(kokoro, voice: str, speed: float = 1.0, name: str = "tts-cache") -> None:
    threading.Thread(
        target=ensure_clips, args=(kokoro, voice, speed), daemon=True, name=name
    ).start()


def _write_wav(path: Path, samples, sr: int) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.reshape(-1)
    pcm = np.clip(arr, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    tmp = path.with_suffix(".wav.tmp")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes(pcm.tobytes())
    os.replace(tmp, path)


def play_clip(path: Path, cancel=None) -> bool:
    """Stream a cached WAV to the default output device.

    Reads PCM16 frames and writes float32 blocks to sounddevice in small
    chunks so playback starts within a few milliseconds of the call.
    Returns True if audio was streamed.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception:
        logger.debug("sounddevice unavailable; cannot play %s", path)
        return False
    try:
        with wave.open(str(path), "rb") as w:
            sr = w.getframerate()
            ch = w.getnchannels()
            width = w.getsampwidth()
            block_frames = max(1, int(sr * READ_CHUNK_S))
            with sd.OutputStream(samplerate=sr, channels=ch, dtype="float32", blocksize=0) as out:
                while True:
                    if cancel is not None and cancel.is_set():
                        break
                    raw = w.readframes(block_frames)
                    if not raw:
                        break
                    _write_block(out, raw, width, ch)
        return True
    except Exception:
        logger.exception("cached clip playback failed: %s", path)
        return False


def _write_block(out, raw: bytes, width: int, ch: int) -> None:
    import numpy as np

    if width == 2:
        arr = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 1:
        arr = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 4:
        arr = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 128.0
    out.write(arr.reshape(-1, ch))
