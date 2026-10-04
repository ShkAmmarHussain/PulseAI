"""Phase 1 acceptance tests for the pre-rendered TTS acknowledgment cache
(spec 29, section 3.1). Plain script (no pytest), exit code 0 on success."""

import os
import shutil
import sys
import tempfile
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TMP = Path(tempfile.mkdtemp(prefix="jarvis_tts_cache_"))
os.environ["JARVIS_TTS_CACHE"] = str(TMP)

import numpy as np  # noqa: E402

from core import audio_cache  # noqa: E402

fails = []


def check(name, ok, extra=""):
    if ok:
        print("PASS " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (" | " + str(extra) if extra else ""))


class FakeKokoro:
    def create(self, text, voice="af_heart", speed=1.0, lang="en-us"):
        sr = 24000
        t = np.linspace(0, 0.2, int(sr * 0.2), endpoint=False)
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr


def main():
    # 1. cache dir honors env override
    check("cache dir honors JARVIS_TTS_CACHE", audio_cache.tts_cache_dir() == TMP)

    # 2. normalization matches stock phrases regardless of case/punctuation
    checks = [
        ("Working on that now.", "working on that now"),
        ("Done.", "done"),
        ("  ACTION DENIED. Nothing was changed!! ", "action denied nothing was changed"),
        ("Transcribing...", "transcribing"),
    ]
    for text, want in checks:
        got = audio_cache.normalize(text)
        check("normalize(%r)" % text, got == want, got)

    # 3. no clips rendered yet -> no match for a stock phrase
    check("find_clip misses before rendering",
          audio_cache.find_clip("Done.", "af_heart", 1.0) is None)

    # 4. ensure_clips renders every stock clip exactly once
    n1 = audio_cache.ensure_clips(FakeKokoro(), "af_heart", 1.0)
    total = len(audio_cache.PRE_RENDERED_VOCAL_RESPONSES)
    check("renders all %d stock clips" % total, n1 == total, n1)
    n2 = audio_cache.ensure_clips(FakeKokoro(), "af_heart", 1.0)
    check("second run renders nothing", n2 == 0, n2)
    vdir = audio_cache.tts_cache_dir() / "af_heart_1"
    check("wav files on disk", len(list(vdir.glob("*.wav"))) == total)

    # 5. every stock phrase now resolves to its clip (case-insensitive)
    ok = True
    for key, phrase in audio_cache.PRE_RENDERED_VOCAL_RESPONSES.items():
        p = audio_cache.find_clip(phrase.upper() + "??", "af_heart", 1.0)
        if p is None or p.name != key + ".wav":
            ok = False
            break
    check("all stock phrases resolve to clips", ok)

    # 6. non-stock text never matches (dynamic replies keep normal TTS)
    check("dynamic text does not match",
          audio_cache.find_clip("I opened notepad for you.", "af_heart", 1.0) is None)
    check("substring does not match",
          audio_cache.find_clip("Done. And more words after.", "af_heart", 1.0) is None)

    # 7. voice isolation: other voice has no clips yet
    check("other voice not rendered",
          audio_cache.find_clip("Done.", "af_bella", 1.0) is None)

    # 8. clip is a valid 24k mono PCM16 wav
    clip = audio_cache.clip_path("ack.done", "af_heart", 1.0)
    with wave.open(str(clip), "rb") as w:
        check("clip format 24k mono 16-bit",
              w.getframerate() == 24000 and w.getnchannels() == 1 and w.getsampwidth() == 2)

    # 9. playback streams the clip (skip gracefully if no audio device)
    t0 = time.time()
    try:
        played = audio_cache.play_clip(clip)
        dt = (time.time() - t0) * 1000
        check("play_clip streams audio", played is True, "%.0fms" % dt)
    except Exception as e:
        print("SKIP play_clip (no audio device): %s" % e)

    # 10. read/open overhead of a cache hit is far below the 50ms budget
    t0 = time.time()
    for _ in range(50):
        audio_cache.find_clip("Working on that now.", "af_heart", 1.0)
    per = (time.time() - t0) * 1000 / 50
    check("find_clip < 2ms per lookup", per < 2.0, "%.3fms" % per)

    shutil.rmtree(TMP, ignore_errors=True)
    print("== %s ==" % ("ALL PASS" if not fails else "%d FAIL: %s" % (len(fails), fails)))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
