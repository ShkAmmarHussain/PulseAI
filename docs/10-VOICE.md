# 10. VOICE (Wake Word, STT, TTS)

Jarvis voice pipeline: "Hey Jarvis" → hear → understand → speak (emotion-aware).

## 10.1 Stack
- Wake Word: openWakeWord (CPU, ONNX, custom "Hey Jarvis")
- VAD: Silero VAD (streaming)
- STT: faster-whisper (small/base, local, low VRAM)
- TTS: Kokoro 82M (natural, emotion/prosody)

## 10.2 Audio Flow
Mic → VAD → WakeWord detect → Streaming STT → Utterance → Pipeline → Response → Kokoro TTS (chunks, interruptible) → Speakers

## 10.3 Latency Targets
Wake detect < 50–150ms, STT first token < 300–600ms, TTS first chunk < 250–500ms, End-to-end wake→speech < 1.0–1.5s.

## 10.4 Kokoro (TTS)
82M, emotion-aware (tone match mood), voice selection, streaming, CPU/GPU <400MB.

## 10.5 Configuration
Sample rate 16kHz, VAD aggressiveness, sensitivity, cooldown, interrupt on new input.

## 10.6 Interruptibility
Can stop speech mid-chunk on new wake/input (natural conversation).
