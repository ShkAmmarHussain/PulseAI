# 11. VISION

Screen vision: capture, OCR fallback, VLM grounding, on-demand lazy-load/unload.

## 11.1 Strategy
Read-only capture first, OCR cheap, escalate to VLM only when UI reasoning/action grounding needed. Strict lazy-load + unload.

## 11.2 Stack
- Capture: mss (fast, low overhead)
- OCR: RapidOCR ONNXRuntime (CPU/GPU light, fallback)
- VLM: Qwen2.5-VL-7B-Instruct Q5_K_M (on-demand)

## 11.3 Workflow
Orchestrator flags vision_needed → unload non-essential heavy → load Vision Agent (VLM) → capture(region) → analyze (find elements, describe, coords) → return grounding → Tool_Control acts → verify (optional re-capture) → unload VLM → restore agents.

## 11.4 Grounding
Returns: elements[{text,bbox,role,confidence,clickable,x,y,center}], suggested_actions[], coordinates (pixel). Click targets use element center + safety margin.

## 11.5 Lifecycle
Load→Execute (bounded time, max 10–20s)→Unload (forced). Timeout + fallback OCR.

## 11.6 Privacy
Read-only screen, no upload, processed locally, discarded after task.
