# 08. MODELS

LM Studio models, quantization, role-split, VRAM, best possible case.

## 8.1 Recommended Models (Exact)

| Agent(s) | Model | Quant | VRAM (GGUF) | Purpose |
|---|---|---|---|---|
| Orchestrator, Planner | Qwen3-8B-GGUF | Q5_K_M | ~5.8–6.1 GB | Reasoning, planning, decomposition |
| Tool_Control | Qwen2.5-Coder-7B-Instruct-GGUF | Q5_K_M | ~4.7–5.0 GB | Tool/function calling (structured JSON) – most reliable for PC control |
| Vision (on-demand) | Qwen2.5-VL-7B-Instruct-GGUF | Q5_K_M | ~6.0–6.2 GB | UI grounding/VLM, lazy-load/unload |
| Pet_UX, Perception, Memory, Safety, Spawner | Llama-3.2-3B-Instruct-GGUF | Q5_K_M | ~2.4–2.6 GB | Fast, always-on, classification |
| Voice | Kokoro (separate, non-LLM) | N/A | <400 MB GPU or CPU | TTS (natural) |
| STT | faster-whisper (separate) | small/base | <500 MB | Speech-to-text |

## 8.2 Why These
- Qwen3-8B: strong agentic reasoning
- Qwen2.5-Coder-7B: best tool-calling reliability
- Qwen2.5-VL-7B: solid UI grounding
- Llama-3.2-3B: low overhead, stable always-on

## 8.3 VRAM Budget & Strategy

| State | Models Loaded | Est. VRAM | Headroom (12GB) |
|---|---|---|---|
| Idle (minimal) | Orchestrator + 3B set | ~6.0 + 2.5 = ~8.5 GB | ~3.5 GB |
| Chat only | Orchestrator + 3B | ~8.5 GB | Safe |
| PC Control (active) | Tool_Coder + 3B (role-swap) | ~5.0 + 2.5 = ~7.5 GB (preferred) or Orchestrator+Tool tight | Better to avoid both heavy simultaneously |
| Vision Task (on-demand) | VLM only (+3B minimal if needed) | ~6.1 + 2.5 = ~8.6 GB max, loaded briefly | Safe, reclaimed after unload |
| Peak (transient) | Worst case brief | <11.5 GB | <0.5 cushion (acceptable with CPU offload) |

**Mitigations:** Role-swapping, lazy-load VLM, single active executor, model offload to RAM, unload non-essential.

## 8.4 LM Studio Config
API: OpenAI-compatible http://localhost:1234/v1, no auth. Context: 4096–8192 (start 8192 for planning, reduce if tight). Temperature 0.1–0.2 for tools, 0.3–0.4 for personality.

## 8.5 Quantization Notes
Q5_K_M sweet spot 3060 12GB. Q4_K_M saves VRAM but loses some tool reliability. Avoid Q6+ for 7–8B under multi-agent load.
