import asyncio
import logging
import os
import queue
import threading
from pathlib import Path

from agents.base import BaseAgent
from core.bus import Event, create_event

logger = logging.getLogger(__name__)

KOKORO_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "JarvisDesktopPet" / "models"


class VoiceTTSAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("voice_tts", bus)
        self._q: "queue.Queue[tuple]" = queue.Queue(maxsize=8)
        self._cancel = threading.Event()
        self._worker = None
        self._kokoro = None
        self._kokoro_error = None
        self._engine = "kokoro"
        self._voice = "af_heart"
        self._speed = 1.0
        self._loop = None
        self._read_cfg()

    def _read_cfg(self):
        vcfg = ((self.cfg or {}).get("config") or {}).get("voice") or {}
        self._engine = str(vcfg.get("tts_engine", "kokoro"))
        self._voice = str(vcfg.get("tts_voice", "af_heart"))
        self._speed = float(vcfg.get("tts_speed", 1.0))

    async def start(self):
        await super().start()
        self.bus.subscribe("voice.say", self.handle)
        self.bus.subscribe("voice.interrupt", self.handle)
        self.bus.subscribe("settings.updated", self.handle)
        self._read_cfg()
        self._loop = asyncio.get_running_loop()
        self._worker = threading.Thread(target=self._run, daemon=True, name="tts-worker")
        self._worker.start()
        if self._engine == "kokoro":
            threading.Thread(target=self._load_kokoro, daemon=True, name="kokoro-load").start()

    async def handle(self, ev: Event):
        if ev.type == "interrupt":
            self._cancel.set()
            return
        if ev.type == "updated":
            self._read_cfg()
            return
        if ev.type == "say":
            text = ev.payload.get("text", "")
            if not text:
                return
            voice = ev.payload.get("voice") or self._voice
            await self.bus.publish(
                create_event("pet.state", "speak", {"text": text}, correlation_id=ev.correlation_id)
            )
            try:
                self._q.put_nowait((text, voice))
            except queue.Full:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    pass
                self._q.put_nowait((text, voice))

    # ---------- kokoro ----------

    def _load_kokoro(self):
        model, voices = KOKORO_DIR / "kokoro-v1.0.onnx", KOKORO_DIR / "voices-v1.0.bin"
        if not (model.exists() and voices.exists()):
            self._kokoro_error = "kokoro model files missing"
            logger.error("kokoro models missing at %s", KOKORO_DIR)
            return
        try:
            from kokoro_onnx import Kokoro

            self._kokoro = Kokoro(str(model), str(voices))
            logger.info("kokoro TTS ready (voice=%s)", self._voice)
        except Exception as e:
            self._kokoro_error = str(e)
            logger.exception("kokoro load failed; falling back to SAPI")

    def _speak_kokoro(self, text: str, voice: str):
        if self._kokoro is None:
            if self._engine == "kokoro" and self._kokoro_error is None:
                self._load_kokoro()
            if self._kokoro is None:
                return False
        import numpy as np
        import sounddevice as sd

        samples, sr = self._kokoro.create(text, voice=voice, speed=self._speed, lang="en-us")
        self._publish_tts(True)
        try:
            with sd.OutputStream(samplerate=sr, channels=1, dtype="float32", blocksize=0) as out:
                chunk = int(sr * 0.08)
                for i in range(0, len(samples), chunk):
                    if self._cancel.is_set():
                        break
                    block = samples[i:i + chunk].astype(np.float32).reshape(-1, 1)
                    out.write(block)
        finally:
            self._publish_tts(False)
        return True

    def _publish_tts(self, speaking: bool):
        if self._loop is None:
            return
        coro = self.bus.publish(create_event("tts_state", "tts_state", {"speaking": speaking}))
        try:
            if not self._loop.is_running():
                raise RuntimeError("event loop not running")
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception:
            coro.close()
            logger.debug("tts_state publish failed")

    # ---------- workers ----------

    def _run(self):
        while True:
            text, voice = self._q.get()
            self._cancel.clear()
            try:
                spoken = False
                if self._engine == "kokoro":
                    try:
                        spoken = self._speak_kokoro(text, voice)
                    except Exception:
                        logger.exception("kokoro speak failed; falling back to SAPI")
                if not spoken:
                    self._speak_sapi(text)
            except Exception:
                logger.exception("tts failed for: %s", text[:60])

    def _speak_sapi(self, text: str):
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        SVSFlagsAsync = 1
        SVSFPurgeBeforeSpeak = 2
        self._publish_tts(True)
        try:
            voice.Speak(text, SVSFlagsAsync)
            while True:
                if self._cancel.is_set():
                    voice.Speak("", SVSFPurgeBeforeSpeak)
                    break
                if voice.WaitUntilDone(150):
                    break
                try:
                    nxt = self._q.get_nowait()
                except queue.Empty:
                    continue
                text, voice_name = nxt
                voice.Speak(text, SVSFlagsAsync | SVSFPurgeBeforeSpeak)
        finally:
            self._publish_tts(False)
            pythoncom.CoUninitialize()
