import asyncio
import logging
import threading
import time

import numpy as np

from core.bus import create_event

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BLOCK_SAMPLES = 1280  # 80 ms - openWakeWord frame multiple


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

    def _read_cfg(self, cfg=None):
        if cfg is not None:
            self._cfg = cfg
        vcfg = ((self._cfg or {}).get("config") or {}).get("voice") or {}
        self.enabled = bool(vcfg.get("enabled", True))
        wcfg = vcfg.get("wake") or {}
        self.wake_enabled = bool(wcfg.get("enabled", True))
        self.wake_threshold = float(wcfg.get("threshold", 0.5))
        self.stt_model_name = str(vcfg.get("stt_model", "base"))
        self.language = vcfg.get("language") or None
        self.vad_threshold = float(vcfg.get("vad_threshold", 0.012))
        self.silence_sec = float(vcfg.get("silence_sec", 1.2))
        self.max_sec = float(vcfg.get("max_sec", 15.0))

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

    # ---------- stream ----------

    def _open_stream(self, mode: str) -> bool:
        if self._stream is not None:
            self._set_mode(mode)
            return True
        import sounddevice as sd

        try:
            dev = sd.query_devices(kind="input")
            logger.info(
                "mic device: '%s' (native rate=%s, ch=%s), opening @%d/%d",
                dev.get("name"), dev.get("default_samplerate"),
                dev.get("max_input_channels"), SAMPLE_RATE, BLOCK_SAMPLES,
            )
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=BLOCK_SAMPLES,
                callback=self._callback,
            )
            self._stream.start()
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
        if self._suppress:
            return
        block = indata[:, 0]
        mode = self._mode
        if mode == "wake":
            self._wake_frame(block)
        elif mode == "listen":
            self._capture_frame(block)
        # transcribe/off: drop

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
            if force_idle or audio.size < SAMPLE_RATE // 4:  # <250ms of speech
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
                return
            finally:
                self._busy = False
            text = (text or "").strip()
            if text:
                await self.bus.publish(
                    create_event("audio.input.voice", "voice", {"text": text}, source="voice")
                )
            if self.wake_enabled and self._stream is not None:
                self._return_after_capture()
            else:
                self._close_stream()
                self._set_state("idle")
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
