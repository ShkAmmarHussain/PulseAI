import asyncio
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TMP = Path(r"D:\Personal_projects\2\Personal_AI")
SR = 16000
BLK = 1280


def load_float(path):
    w = wave.open(str(path), "rb")
    sr, n = w.getframerate(), w.getnframes()
    data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if w.getnchannels() > 1:
        data = data.reshape(-1, w.getnchannels()).mean(axis=1)
    w.close()
    if sr != SR:
        idx = np.linspace(0, len(data) - 1, int(len(data) * SR / sr))
        data = np.interp(idx, np.arange(len(data)), data).astype(np.float32)
    return data


def frames(audio):
    return [audio[i:i + BLK] for i in range(0, len(audio) - BLK + 1, BLK)]


async def main():
    from backend.app import App
    from core.bus import create_event

    app = App()
    await app.start()
    v = app.voice
    v._close_stream()  # deterministic: drive frames manually, no live mic

    events = []

    async def cap(ev):
        events.append((ev.topic, dict(ev.payload)))

    for t in ("ui.voice_state", "tts_state", "ui.chat", "audio.input.voice", "voice.say"):
        app.bus.subscribe(t, cap)

    for _ in range(150):
        if v._wake_model is not None or v._wake_error:
            break
        await asyncio.sleep(0.1)
    assert v._wake_model is not None, f"wake model failed: {v._wake_error}"
    print("1) wake model ready")

    # A: negative clip must NOT trigger
    v._set_mode("wake")
    for blk in frames(load_float(TMP / "wake_neg.wav")):
        if v._mode == "wake":
            v._wake_frame(blk)
    assert v._mode == "wake", "false trigger on negative clip!"
    print("2) negative clip: no trigger")

    # B: positive clip triggers wake -> captures rest -> silence finalizes
    v._set_mode("wake")
    pos = frames(load_float(TMP / "wake_pos.wav"))
    for blk in pos:
        if v._mode == "wake":
            v._wake_frame(blk)
        elif v._mode == "listen":
            v._capture_frame(blk)
    assert v._mode == "listen", "wake word did not trigger!"
    print("3) wake triggered, state:", v._state)

    silence = np.zeros(SR * 2, dtype=np.float32)
    for blk in frames(silence):
        if v._mode == "listen":
            v._capture_frame(blk)
        else:
            break

    # wait for transcript -> orchestrator -> reply -> TTS
    end = asyncio.get_event_loop().time() + 60
    transcript = None
    reply = None
    tts_states = []
    while asyncio.get_event_loop().time() < end and not (reply and "speaking" in str(tts_states)):
        await asyncio.sleep(0.3)
        for topic, p in events:
            if topic == "audio.input.voice" and not transcript:
                transcript = p.get("text")
            if topic == "ui.chat" and p.get("role") == "assistant" and not reply:
                reply = p.get("text")
            if topic == "tts_state":
                if not tts_states or tts_states[-1] != p.get("speaking"):
                    tts_states.append(p.get("speaking"))
        if reply and tts_states and tts_states[0] is True:
            break

    print("4) transcript:", repr(transcript))
    assert transcript and "time" in transcript.lower(), f"bad transcript: {transcript!r}"
    print("5) reply:", (reply or "")[:90])
    assert reply, "no assistant reply"
    print("6) tts_states:", tts_states)
    assert True in tts_states, "TTS never reported speaking (kokoro playback?)"
    final_state = v._state
    print("7) final state (stream was closed by test):", final_state)
    assert final_state in ("wake", "idle"), f"unexpected: {final_state}"

    # 8) runtime wake toggle re-opens the mic and returns to wake state
    v.set_wake_enabled(False)
    await asyncio.sleep(0.3)
    assert v._state == "idle" and v._stream is None, "wake off failed"
    v.set_wake_enabled(True)
    for _ in range(50):
        if v._state == "wake":
            break
        await asyncio.sleep(0.1)
    assert v._state == "wake" and v._stream is not None, f"wake on failed: {v._state}"
    print("8) wake toggle off/on OK, state:", v._state)
    v._close_stream()
    print("WAKE E2E PASS")


asyncio.run(main())
