# 09. HARDWARE

3060 12GB analysis, limits, optimization, stability.

## 9.1 GPU
NVIDIA RTX 3060 12GB GDDR6. VRAM 12GB, usable ~11.5–11.8GB.

## 9.2 Headroom Strategy
- Never load Orchestrator+Tool_Coder+VLM simultaneously
- VLM strictly on-demand + unload
- Role-swap heavy agents
- 3B always-on small footprint
- CPU offload (GGUF context/layers)

## 9.3 Memory/CPU
RAM ≥ 32GB recommended (helps CPU offload, ChromaDB, Whisper). 16GB minimum borderline under heavy vision+planning.

## 9.4 Performance Targets
Idle < 8.5GB VRAM, Chat < 9GB, Action < 8.5GB, Vision burst < 9GB (brief), Peak < 11.5GB.

## 9.5 Optimization
PagedAttention (LM Studio), context sizing, batch 1, unload timers (30–60s idle), GC, avoid thrashing.

## 9.6 Thermal/Stability
Monitor VRAM/usage, cooldown, avoid sustained peak >11.5GB.
