import asyncio
import logging
import re
import threading
import time

import numpy as np

from core.bus import create_event
from core.stt import apply_vocabulary
from tools.dictation_injector import append_history as append_dictation_history
from tools.dictation_injector import inject as inject_dictation_text

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BLOCK_SAMPLES = 1280  # 80 ms - openWakeWord frame multiple

# spec 29 section 3.2: voice activation / deactivation of dictate-to-cursor
_DICTATION_START_PHRASE = re.compile(
    r"^\s*(?:hey\s+jarvis[,!\s]*)?(?:transcribe|dictate(?:\s+this)?|dictation)\b", re.IGNORECASE
)
_DICTATION_STOP_PHRASE = re.compile(
    r"^\s*(?:stop|end|finish)\s+(?:the\s+)?(?:transcription|transcribing|dictation|dictating|dictate)\b",
    re.IGNORECASE,
)


class VoiceService:
    """Persistent mic stream: wake -> listening -> transcribing -> wake (or manual push-to-talk)."""

    def __init__(self, bus, cfg):
        self.bus = bus
        self.loop = asyncio.get_running_loop()
        self._read_cfg(cfg)

        self._stream = None
        self._wake_model = None
        self._wake_loading = False
        self._wake_error = None
        self._mode = "off"  # wake | listen | transcribe | off
        self._state = "idle"
        self._armed = True
        self._cooldown_until = 0.0
        self._suppress = False
        self._busy = False
        self._stopping = False

        self._lock = threading.Lock()
        self._frames: list = []
        self._speech_started = False
        self._silent_blocks = 0
        self._model = None
        self._level_t = 0.0
        self._test_until = 0.0
        self._test_max = 0.0
        self._test_level = 0.0
        self._test_pub_t = 0.0
        self._noise_floor = 0.004
        self._gain = 1.0
        self._gain_rms = 0.0
        self._dictating = False
        self._dictate_end_pending = False

    def _read_cfg(self, cfg=None):
        if cfg is not None:
            self._cfg = cfg
        vcfg = ((self._cfg or {}).get("config") or {}).get("voice") or {}
        self.enabled = bool(vcfg.get("enabled", True))
        wcfg = vcfg.get("wake") or {}
        self.wake_enabled = bool(wcfg.get("enabled", True))
        self.wake_threshold = float(wcfg.get("threshold", 0.35))
        self.stt_model_name = str(vcfg.get("stt_model", "base"))
        self.language = vcfg.get("language") or None
        self.vad_threshold = float(vcfg.get("vad_threshold", 0.012))
        self.silence_sec = float(vcfg.get("silence_sec", 1.2))
        self.max_sec = float(vcfg.get("max_sec", 15.0))
        self.device = vcfg.get("device") or None
        self.agc = bool(vcfg.get("agc", True))
        self.noise_gate = bool(vcfg.get("noise_gate", True))
        self.gain_max = float(vcfg.get("gain_max", 10.0))

    # ---------- state ----------

    def _set_state(self, state: str, error: str = ""):
        if state == self._state and not error:
            return
        self._state = state
        payload = {"state": state}
        if error:
            payload["error"] = error
        asyncio.run_coroutine_threadsafe(
            self.bus.publish(create_event("ui.voice_state", "voice_state", payload, source="voice")),
            self.loop,
        )

    @property
    def state(self):
        return self._state

    # ---------- lifecycle ----------

    async def start(self):
        self.bus.subscribe("tts_state", self._on_tts)
        self.bus.subscribe("settings.updated", self._on_settings)
        if self.enabled and self.wake_enabled:
            self._load_wake_async()
            self._open_stream("wake")

    async def _on_tts(self, ev):
        if ev.type == "tts_state":
            speaking = bool(ev.payload.get("speaking"))
            if speaking != self._suppress:
                logger.info("tts_state speaking=%s (mic suppress %s)", speaking, "on" if speaking else "off")
            self._suppress = speaking

    async def _on_settings(self, ev):
        was_wake = self.wake_enabled
        old_device = self.device
        self._read_cfg(ev.payload)
        if not self.enabled:
            self._close_stream()
            self._set_state("disabled")
            return
        if self.wake_enabled and not was_wake:
            self._load_wake_async()
            if self._stream is None:
                self._open_stream("wake")
            elif self._mode in ("off", "transcribe"):
                self._set_mode("wake")
        elif not self.wake_enabled and was_wake:
            if self._mode == "wake":
                self._close_stream()
                self._set_state("idle")
        if self._stream is not None and self.device != old_device:
            logger.info("mic device changed (%s -> %s): reopening stream", old_device, self.device)
            mode = "listen" if self._mode == "listen" else "wake"
            self._close_stream()
            if self.wake_enabled or mode == "listen":
                self._open_stream(mode)

    def set_wake_enabled(self, on: bool):
        self.wake_enabled = bool(on)
        if on:
            self._load_wake_async()
            if self._stream is None and not self._busy:
                self._open_stream("wake")
            elif self._mode == "off":
                self._set_mode("wake")
        else:
            if self._mode == "wake":
                self._close_stream()
                self._set_state("idle")

    # ---------- public API (ws_bridge) ----------

    async def set_listening(self, on: bool) -> None:
        if not self.enabled:
            self._set_state("disabled")
            return
        if on:
            if self._busy or self._state == "listening":
                return
            await self.bus.publish(create_event("voice.interrupt", "interrupt", {}, source="voice"))
            if self._stream is None:
                if not self._open_stream("listen"):
                    return
            else:
                self._set_mode("listen")
            self._reset_capture()
            self._set_state("listening")
        else:
            if self._mode == "listen" and not self._busy:
                await self._finish_capture(force_idle=True)

    # ---------- dictation (spec 29, section 3.2) ----------

    @property
    def is_dictating(self) -> bool:
        return self._dictating

    async def set_dictation(self, on: bool) -> bool:
        """Toggle system-wide dictate-to-cursor mode."""
        if not self.enabled:
            self._set_state("disabled")
            return False
        if on:
            if self._dictating:
                return True
            if self._busy or self._state == "test" or self._stopping:
                return False
            await self.bus.publish(create_event("voice.interrupt", "interrupt", {}, source="voice"))
            if self._stream is None:
                if not self._open_stream("listen"):
                    return False
            else:
                self._set_mode("listen")
            await self._begin_dictation("hotkey")
            return True
        if not self._dictating:
            return False
        with self._lock:
            has_audio = self._speech_started or len(self._frames) >= SAMPLE_RATE // 8
        if has_audio and not self._busy:
            # transcribe + inject whatever was already spoken, then end there
            self._dictate_end_pending = True
            await self._finish_capture(force_idle=False)
            return True
        await self._end_dictation()
        return True

    async def apply_dictation_text(self, text: str) -> dict:
        """Dictionary replacement + injection + history + dictation.result event.

        Shared by the transcription pipeline and the ws 'dictation' command.
        """
        text = apply_vocabulary((text or "").strip())
        if not text:
            return {"ok": False, "error": "empty", "text": ""}
        res = await asyncio.to_thread(inject_dictation_text, text)
        entry = {
            "ts": time.time(),
            "text": text,
            "app": res.get("app", ""),
            "injected": bool(res.get("injected")),
        }
        await asyncio.to_thread(append_dictation_history, entry)
        await self.bus.publish(
            create_event(
                "dictation.result",
                "dictation",
                {"text": text, "injected": bool(res.get("injected")), "app": res.get("app", "")},
                source="voice",
            )
        )
        return {"ok": True, "text": text, "injected": bool(res.get("injected")), "app": res.get("app", "")}

    async def _begin_dictation(self, source: str):
        self._dictating = True
        self._dictate_end_pending = False
        self._reset_capture()
        if self._stream is None:
            self._open_stream("listen")
        else:
            self._set_mode("listen")
        self._set_state("listening")
        await self.bus.publish(
            create_event("dictation.start", "dictation", {"target": "cursor", "mode": "system_wide"}, source="voice")
        )
        logger.info("dictation started (%s)", source)

    def _resume_dictation(self):
        """Back to capturing the next dictation utterance."""
        self._dictate_end_pending = False
        self._reset_capture()
        if self._stream is None:
            self._open_stream("listen")
        else:
            self._set_mode("listen")
        self._set_state("listening")

    async def _end_dictation(self):
        if not self._dictating and not self._dictate_end_pending:
            return
        self._dictating = False
        self._dictate_end_pending = False
        await self.bus.publish(create_event("dictation.stop", "dictation", {}, source="voice"))
        if self.wake_enabled and self._stream is not None:
            self._return_after_capture()
        else:
            self._close_stream()
            self._set_state("idle")
        logger.info("dictation stopped")

    async def _dictation_finalize(self, text: str, end_requested: bool):
        if _DICTATION_STOP_PHRASE.match(text or ""):
            await self._end_dictation()
            return
        if text:
            await self.apply_dictation_text(text)
        if end_requested:
            await self._end_dictation()

    # ---------- wake test (user-facing mic/wake diagnostics) ----------

    def start_wake_test(self, seconds: float = 8.0) -> bool:
        """Score live mic audio against the wake model for N seconds and report."""
        if self._busy or self._state == "listening":
            return False
        seconds = max(3.0, min(20.0, float(seconds or 8.0)))
        if self._wake_model is None:
            self._load_wake_async()
        if self._stream is None and not self._open_stream("test"):
            self._publish_wake_test({"phase": "done", "detected": False, "error": "mic unavailable"})
            return False
        self._mode = "test"
        self._test_until = time.monotonic() + seconds
        self._test_max = 0.0
        self._test_level = 0.0
        self._test_pub_t = 0.0
        logger.info(
            "wake test started (%.0fs, threshold=%.2f, device=%s)",
            seconds, self.wake_threshold, self.current_device(),
        )
        self._publish_wake_test(
            {
                "phase": "start",
                "seconds": seconds,
                "threshold": self.wake_threshold,
                "device": self.current_device(),
                "model_ready": self._wake_model is not None,
            }
        )
        return True

    def _test_frame(self, block: np.ndarray):
        rms = float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0
        self._test_level = max(self._test_level, rms)
        score = 0.0
        m = self._wake_model
        if m is not None:
            pcm = (np.clip(block, -1.0, 1.0) * 32767.0).astype(np.int16)
            try:
                preds = m.predict(pcm)
                score = max(preds.values()) if preds else 0.0
            except Exception:
                logger.exception("wake test predict failed")
        self._test_max = max(self._test_max, score)
        now = time.monotonic()
        if now - self._test_pub_t >= 0.15:
            self._test_pub_t = now
            self._publish_wake_test(
                {
                    "phase": "run",
                    "score": round(score, 3),
                    "max": round(self._test_max, 3),
                    "level": round(rms, 4),
                    "threshold": self.wake_threshold,
                }
            )
        if now >= self._test_until:
            self._finish_wake_test()

    def _finish_wake_test(self):
        detected = self._test_max >= self.wake_threshold
        logger.info(
            "wake test finished: detected=%s max=%.3f level=%.4f threshold=%.2f",
            detected, self._test_max, self._test_level, self.wake_threshold,
        )
        if self._wake_model is not None:
            try:
                self._wake_model.reset()
            except Exception:
                pass
        if self.wake_enabled and self._stream is not None:
            self._set_mode("wake")
        else:
            self._close_stream()
        self._publish_wake_test(
            {
                "phase": "done",
                "detected": detected,
                "max_score": round(self._test_max, 3),
                "level": round(self._test_level, 4),
                "threshold": self.wake_threshold,
                "device": self.current_device(),
                "model_ready": self._wake_model is not None,
            }
        )

    def _publish_wake_test(self, payload: dict):
        asyncio.run_coroutine_threadsafe(
            self.bus.publish(create_event("ui.wake_test", "wake_test", payload, source="voice")),
            self.loop,
        )

    # ---------- wake model ----------

    def _load_wake_async(self):
        if self._wake_model is not None or self._wake_loading:
            return
        self._wake_loading = True
        threading.Thread(target=self._load_wake, daemon=True, name="wake-load").start()

    def _load_wake(self):
        try:
            from openwakeword.model import Model

            m = Model(
                wakeword_models=["hey jarvis"],
                vad_threshold=0.5,
                inference_framework="onnx",
            )
            m.predict(np.zeros(BLOCK_SAMPLES, dtype=np.int16))  # warm-up
            self._wake_model = m
            self._wake_error = None
            logger.info("wake word model ready (threshold=%.2f)", self.wake_threshold)
            if self._mode == "wake":
                self._set_state("wake")
        except Exception as e:
            self._wake_error = str(e)
            logger.exception("wake word model failed to load")
            if self._mode == "wake":
                self._set_state("error", error=f"Wake word unavailable: {e}")
        finally:
            self._wake_loading = False

    # ---------- device selection ----------

    def _resolve_device(self):
        """Configured device name -> sounddevice index, or None for system default."""
        if not self.device:
            return None
        import sounddevice as sd

        for i, d in enumerate(sd.query_devices()):
            if d.get("max_input_channels", 0) > 0 and d.get("name") == self.device:
                return i
        logger.warning("configured mic '%s' not found, using system default", self.device)
        return None

    @staticmethod
    def list_devices() -> list:
        """Connected + usable capture mics: Windows-active endpoints that PortAudio
        can open at 16 kHz, excluding virtual/duplicate entries."""
        import sounddevice as sd

        VIRTUAL = ("microsoft sound mapper", "primary sound capture driver", "midi (wave)")
        norm = lambda s: " ".join(str(s or "").split())
        out, seen = [], set()

        live_names = []
        try:
            from pycaw.pycaw import AudioUtilities

            for d in AudioUtilities.GetAllDevices(data_flow=1, device_state=1):
                n = norm(d.FriendlyName)
                if n and n.lower() not in VIRTUAL:
                    live_names.append(n)
        except Exception:
            logger.exception("windows endpoint enumeration failed; falling back to portaudio")

        sd_ins = [
            (i, norm(d["name"]), int(d.get("default_samplerate") or 0))
            for i, d in enumerate(sd.query_devices())
            if d.get("max_input_channels", 0) > 0
        ]
        try:
            default_idx = sd.default.device[0]
            default_name = norm(sd.query_devices()[default_idx]["name"]) if default_idx is not None and default_idx >= 0 else ""
        except Exception:
            default_name = ""

        def usable(idx):
            try:
                sd.check_input_settings(device=idx, samplerate=SAMPLE_RATE, channels=1, dtype="float32")
                return True
            except Exception:
                return False

        if live_names:
            for name in live_names:
                if name in seen:
                    continue
                match = next((s for s in sd_ins if s[1].lower() == name.lower()), None)
                if match is None:
                    match = next(
                        (s for s in sd_ins if name.lower() in s[1].lower() or s[1].lower() in name.lower()),
                        None,
                    )
                if match is None or not usable(match[0]):
                    continue
                seen.add(name)
                out.append(
                    {
                        "name": name,
                        "index": match[0],
                        "rate": match[2],
                        "default": bool(default_name) and name.lower() == default_name.lower(),
                    }
                )
        else:
            for idx, name, rate in sd_ins:
                if name in seen or name.lower() in VIRTUAL or not usable(idx):
                    continue
                seen.add(name)
                out.append({"name": name, "index": idx, "rate": rate, "default": name == default_name})

        if not out:
            for idx, name, rate in sd_ins:
                if name in seen:
                    continue
                seen.add(name)
                out.append({"name": name, "index": idx, "rate": rate, "default": name == default_name})
        return out

    def set_device(self, name) -> bool:
        """Switch capture device; reopens the live stream when it changes."""
        name = (name or "").strip() or None
        if name == self.device:
            return self._stream is not None
        self.device = name
        if self._stream is None:
            return True
        mode = "listen" if self._mode == "listen" else "wake"
        self._close_stream()
        if not self.enabled or (mode == "wake" and not self.wake_enabled):
            return True
        return self._open_stream(mode)

    def current_device(self) -> str:
        import sounddevice as sd

        if self.device:
            return self.device
        try:
            return str(sd.query_devices(kind="input").get("name") or "default")
        except Exception:
            return "default"

    # ---------- stream ----------

    def _open_stream(self, mode: str) -> bool:
        if self._stream is not None:
            self._set_mode(mode)
            return True
        import sounddevice as sd

        try:
            dev_idx = self._resolve_device()
            dev = sd.query_devices(dev_idx) if dev_idx is not None else sd.query_devices(kind="input")
            logger.info(
                "mic device: '%s' (idx=%s, native rate=%s, ch=%s), opening @%d/%d",
                dev.get("name"), dev_idx, dev.get("default_samplerate"),
                dev.get("max_input_channels"), SAMPLE_RATE, BLOCK_SAMPLES,
            )
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=BLOCK_SAMPLES,
                device=dev_idx,
                callback=self._callback,
            )
            self._stream.start()
            self._noise_floor = 0.004
            self._gain = 1.0
            self._gain_rms = 0.0
            logger.info("mic stream opened (actual rate=%s)", self._stream.samplerate)
        except Exception as e:
            self._stream = None
            logger.exception("mic open failed")
            self._set_state("error", error=f"Mic unavailable: {e}")
            return False
        self._set_mode(mode)
        return True

    def _close_stream(self):
        stream, self._stream = self._stream, None
        self._set_mode("off")
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                logger.exception("mic close failed")

    def _set_mode(self, mode: str):
        self._mode = mode
        if mode == "wake":
            if self._wake_model is not None:
                self._set_state("wake")
            elif not self._wake_loading:
                self._set_state("error", error=f"Wake word unavailable: {self._wake_error or 'not loaded'}")
        elif mode == "off":
            self._set_state("idle")

    # ---------- audio routing ----------

    def _callback(self, indata, frames, time_info, status):
        block = self._process(indata[:, 0])
        self._publish_level(block)
        if self._suppress:
            return
        mode = self._mode
        if mode == "wake":
            self._wake_frame(block)
        elif mode == "test":
            self._test_frame(block)
        elif mode == "listen":
            self._capture_frame(block)
        # transcribe/off: drop

    def _process(self, block: np.ndarray) -> np.ndarray:
        """Noise gate + slow automatic gain so quiet mics arrive clear and loud.

        Output is fed to wake model, VAD and whisper - one consistent signal.
        """
        rms = float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0
        # adaptive noise floor: only follows quiet signal, never rises with speech
        if rms < self._noise_floor * 1.6:
            self._noise_floor = max(1e-5, self._noise_floor * 0.995 + rms * 0.005)
        gate = max(self._noise_floor * 2.5, 0.0015)

        g = 1.0
        if self.noise_gate and rms < gate:
            g = min(1.0, max(0.06, rms / gate if gate else 1.0)) ** 2

        if self.agc:
            self._gain_rms = self._gain_rms * 0.9 + rms * 0.1
            if self._gain_rms >= gate:
                desired = min(0.10 / max(self._gain_rms, 0.004), self.gain_max)
            else:
                desired = 1.0
            self._gain += (desired - self._gain) * 0.06
            g *= self._gain

        if g == 1.0:
            return block
        return np.clip(block * g, -1.0, 1.0)

    def _publish_level(self, block):
        """Throttled live input level -> UI (level meter + mic diagnostics)."""
        now = time.monotonic()
        if now - self._level_t < 0.1:
            return
        self._level_t = now
        rms = float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0
        peak = float(np.abs(block).max()) if block.size else 0.0
        payload = {
            "level": round(rms, 4),
            "peak": round(float(np.abs(block).max()) if block.size else 0.0, 4),
            "gain": round(self._gain, 2),
            "device": self.current_device(),
            "active": not self._suppress and self._mode in ("wake", "listen", "test"),
        }
        asyncio.run_coroutine_threadsafe(
            self.bus.publish(create_event("ui.mic_level", "mic_level", payload, source="voice")),
            self.loop,
        )

    def _wake_frame(self, block: np.ndarray):
        m = self._wake_model
        if m is None:
            return
        rms = float(np.sqrt(np.mean(np.square(block))))
        pcm = (np.clip(block, -1.0, 1.0) * 32767.0).astype(np.int16)
        try:
            preds = m.predict(pcm)
        except Exception:
            logger.exception("wake predict failed")
            return
        score = max(preds.values()) if preds else 0.0
        now = time.monotonic()
        if not hasattr(self, "_dbg"):
            self._dbg = {"max": 0.0, "rms": 0.0, "t": now, "key": ""}
        self._dbg["max"] = max(self._dbg["max"], score)
        self._dbg["rms"] = max(self._dbg["rms"], rms)
        if preds:
            self._dbg["key"] = max(preds, key=preds.get)
        if now - self._dbg["t"] >= 1.0:
            logger.info(
                "wake live: score_max=%.3f rms=%.4f key=%s armed=%s suppress=%s",
                self._dbg["max"], self._dbg["rms"], self._dbg["key"],
                self._armed, self._suppress,
            )
            self._dbg["max"] = 0.0
            self._dbg["rms"] = 0.0
            self._dbg["t"] = now
        if score < self.wake_threshold * 0.5:
            self._armed = True
        if self._armed and score >= self.wake_threshold and now >= self._cooldown_until:
            self._on_wake()

    def _on_wake(self):
        self._armed = False
        self._cooldown_until = time.monotonic() + 2.0
        self._reset_capture()
        self._mode = "listen"
        self._set_state("listening")
        asyncio.run_coroutine_threadsafe(
            self.bus.publish(create_event("voice.interrupt", "interrupt", {}, source="voice")),
            self.loop,
        )
        logger.info("wake word detected -> listening")

    # ---------- utterance capture ----------

    def _reset_capture(self):
        with self._lock:
            self._frames = []
            self._speech_started = False
            self._silent_blocks = 0

    def _capture_frame(self, block: np.ndarray):
        rms = float(np.sqrt(np.mean(np.square(block))))
        finalize = False
        with self._lock:
            if not self._speech_started:
                if rms >= self.vad_threshold:
                    self._speech_started = True
                    self._frames.append(block.copy())
                return
            self._frames.append(block.copy())
            if rms < self.vad_threshold:
                self._silent_blocks += 1
            else:
                self._silent_blocks = 0
            dur = len(self._frames) * BLOCK_SAMPLES / SAMPLE_RATE
            if dur >= self.max_sec or self._silent_blocks * BLOCK_SAMPLES / SAMPLE_RATE >= self.silence_sec:
                finalize = True
        if finalize:
            asyncio.run_coroutine_threadsafe(self._finish_capture(), self.loop)

    async def _finish_capture(self, force_idle: bool = False):
        if self._busy or self._stopping:
            return
        self._stopping = True
        try:
            with self._lock:
                audio = np.concatenate(self._frames) if self._frames else np.zeros(0, dtype=np.float32)
                self._frames = []
                self._speech_started = False
                self._silent_blocks = 0
            end_requested = self._dictate_end_pending
            was_dictating = self._dictating
            if force_idle or audio.size < SAMPLE_RATE // 4:  # <250ms of speech
                if self._dictating:
                    if end_requested or force_idle:
                        await self._end_dictation()
                    else:
                        self._resume_dictation()
                    return
                self._return_after_capture(force_close=force_idle)
                return
            self._mode = "transcribe"
            self._busy = True
            self._set_state("transcribing")
            try:
                text = await asyncio.to_thread(self._transcribe, audio)
            except Exception as e:
                logger.exception("stt failed")
                self._set_state("error", error=f"Transcription failed: {e}")
                if self._dictating:
                    if end_requested:
                        await self._end_dictation()
                    else:
                        self._resume_dictation()
                return
            finally:
                self._busy = False
            text = apply_vocabulary((text or "").strip())
            if was_dictating:
                await self._dictation_finalize(text, end_requested or not self._dictating)
            elif text and _DICTATION_START_PHRASE.match(text):
                await self._begin_dictation("voice")
            elif text:
                await self.bus.publish(
                    create_event("audio.input.voice", "voice", {"text": text}, source="voice")
                )
            if self._dictating:
                self._resume_dictation()
            elif not was_dictating:
                # normal path: session started here or never ran
                if self.wake_enabled and self._stream is not None:
                    self._return_after_capture()
                else:
                    self._close_stream()
                    self._set_state("idle")
            # was_dictating and not dictating anymore: _end_dictation already
            # returned the mic to wake/idle
        finally:
            self._stopping = False

    def _return_after_capture(self, force_close: bool = False):
        if self.wake_enabled and self._stream is not None and not force_close:
            if self._wake_model is not None:
                try:
                    self._wake_model.reset()
                except Exception:
                    pass
            self._armed = True
            self._set_mode("wake")
        else:
            self._close_stream()
            self._set_state("idle")

    # ---------- STT ----------

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info("loading whisper model '%s' (cpu/int8)...", self.stt_model_name)
            self._model = WhisperModel(self.stt_model_name, device="cpu", compute_type="int8")
        return self._model

    def _transcribe(self, audio: np.ndarray) -> str:
        model = self._get_model()
        segments, _info = model.transcribe(audio, language=self.language, vad_filter=True)
        return " ".join(seg.text for seg in segments).strip()
