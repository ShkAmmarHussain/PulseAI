# 33. SPECIFICATION: BESPOKE TITLEBAR, MULTI-PROVIDER LLM ENGINE & LUXURY UI REFINEMENT

**Document:** `docs/33-CUSTOM-TITLEBAR-CLOUD-MODELS-AND-UI-POLISH.md`  
**Target Agent:** `opencode` / `Claude Code`  
**Purpose:** Implementation blueprint to:
1. Replace the default OS window title bar with a **Bespoke Frameless Window Titlebar** (integrated draggable header, Mochi icon, sleek window controls).
2. Support **OpenAI and Anthropic (Claude) cloud API keys** alongside LM Studio (single API key entry, zero manual endpoint configuration).
3. Implement an **Intelligent Auto-Model Selector** (dynamically selecting the best tier for orchestrator, planner, tool execution, and vision).
4. Fix all visual defects from recent inspection captures (blinding white memory inputs, harsh orange rectangular buttons, debug dumps in onboarding, and replacing legacy orange Saturn orbs with the Mochi mascot).  
**Parent Documentation:** [08-MODELS.md](file:///d:/Personal_projects/2/Personal_AI/docs/08-MODELS.md), [15-CONFIG.md](file:///d:/Personal_projects/2/Personal_AI/docs/15-CONFIG.md), [27-UI-REVAMP.md](file:///d:/Personal_projects/2/Personal_AI/docs/27-UI-REVAMP.md), [31-2D-3D-PET-SWITCHER-AND-UI-POLISH.md](file:///d:/Personal_projects/2/Personal_AI/docs/31-2D-3D-PET-SWITCHER-AND-UI-POLISH.md), [32-TASKS-MEMORY-AND-PRODUCT-SURFACES.md](file:///d:/Personal_projects/2/Personal_AI/docs/32-TASKS-MEMORY-AND-PRODUCT-SURFACES.md)

---

## 1. Executive Summary & User Feedback Analysis

### 1.1 The User's Direct Feedback
> *"Look at the UI, its broken at so many places. Also, can you make it so that it can use openai key or claude key instead of Lm studio too, just the key should be entered. Also, is it auto choosing models for the best possible actions? and look at the top window bar, its default window UI I want it specilized for this app."*

### 1.2 Detailed Visual Defect Breakdown (From Attached Screenshots)

```
┌───────────────────────────────────────┬───────────────────────────────────────┬───────────────────────────────────────┐
│       DEFECT 1: WINDOW TITLEBAR       │       DEFECT 2: MEMORY FORM THEME     │       DEFECT 3: ONBOARDING & ORB LOGO │
├───────────────────────────────────────┼───────────────────────────────────────┼───────────────────────────────────────┤
│ • Window has default Windows 11 title │ • Unthemed native <select> & <textarea>│ • Modal header & sidebar brand still  │
│   bar (blue dot icon, white caption). │   render as blinding WHITE boxes with │   display legacy orange Saturn sphere │
│ • Clashes with the custom dark UI.    │   unreadable light text!              │   instead of the Mochi mascot.        │
│ • Needs frameless window with sleek   │ • Harsh orange rectangular buttons    │ • Step 3 dumps raw unformatted debug  │
│   custom Minimize, Maximize, Close.   │   with zero padding and sharp corners.│   string of 5 comma-separated models. │
└───────────────────────────────────────┴───────────────────────────────────────┴───────────────────────────────────────┘
```

---

## 2. Component 1: Bespoke Frameless Window Titlebar

### 2.1 Tauri Window Configuration (`ui_pet/src-tauri/tauri.conf.json`)
Set `decorations: false` on the main window:
```json
{
  "label": "main",
  "title": "Jarvis",
  "url": "index.html",
  "width": 1100,
  "height": 760,
  "minWidth": 760,
  "minHeight": 560,
  "resizable": true,
  "decorations": false,
  "center": true,
  "visible": true
}
```

### 2.2 Custom Titlebar Markup (`ui_pet/src/index.html`)
Prepend a dedicated custom titlebar spanning the top of the application:
```html
<header id="window-titlebar" data-tauri-drag-region>
  <div class="titlebar-left" data-tauri-drag-region>
    <div class="titlebar-brand" data-tauri-drag-region>
      <svg class="mochi-mini-logo" aria-hidden="true"><use href="#i-mochi"/></svg>
      <span class="titlebar-app-name">Jarvis</span>
      <span class="titlebar-version-pill">v0.2</span>
    </div>
  </div>
  <div class="titlebar-center" data-tauri-drag-region>
    <!-- Draggable space -->
  </div>
  <div class="titlebar-right">
    <button class="win-btn" id="win-min" title="Minimize" aria-label="Minimize">
      <svg viewBox="0 0 12 12"><line x1="2" y1="6" x2="10" y2="6"/></svg>
    </button>
    <button class="win-btn" id="win-max" title="Maximize" aria-label="Maximize">
      <svg viewBox="0 0 12 12"><rect x="2.5" y="2.5" width="7" height="7" fill="none"/></svg>
    </button>
    <button class="win-btn close" id="win-close" title="Close" aria-label="Close">
      <svg viewBox="0 0 12 12"><line x1="2.5" y1="2.5" x2="9.5" y2="9.5"/><line x1="9.5" y1="2.5" x2="2.5" y2="9.5"/></svg>
    </button>
  </div>
</header>
```

### 2.3 Window Controls Logic (`ui_pet/src/main.ts` or `ui_pet/src/titlebar.js`)
Wire native Tauri window API:
```javascript
(function initTitlebar() {
  const ta = window.__TAURI__;
  const win = ta && ta.window ? ta.window.appWindow : null;
  if (!win) return;

  document.getElementById("win-min")?.addEventListener("click", () => win.minimize());
  document.getElementById("win-max")?.addEventListener("click", async () => {
    const isMax = await win.isMaximized();
    if (isMax) win.unmaximize();
    else win.maximize();
  });
  document.getElementById("win-close")?.addEventListener("click", () => win.close());
})();
```

### 2.4 Styling (`ui_pet/src/app.css`)
```css
#window-titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  background: rgba(18, 19, 23, 0.98);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  user-select: none;
  z-index: 999;
}
.titlebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 14px;
}
.titlebar-brand .mochi-mini-logo {
  width: 18px;
  height: 18px;
}
.titlebar-app-name {
  font-size: 12.5px;
  font-weight: 700;
  color: #eceef4;
  letter-spacing: 0.02em;
}
.titlebar-version-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #a0a4b8;
}
.titlebar-right {
  display: flex;
  height: 100%;
}
.win-btn {
  width: 44px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #8b8f9f;
  cursor: pointer;
  transition: all 120ms ease;
}
.win-btn svg {
  width: 11px;
  height: 11px;
  stroke: currentColor;
  stroke-width: 1.25;
}
.win-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}
.win-btn.close:hover {
  background: #e11d48;
  color: #ffffff;
}
```

---

## 3. Component 2: Multi-Provider LLM Engine (OpenAI, Claude, LM Studio)

Users must be able to simply select their provider and enter their API key without configuring custom URLs.

### 3.1 Updated Configuration Schema (`config/config.yaml`)
```yaml
llm:
  provider: "lm_studio" # Options: "lm_studio" | "openai" | "anthropic"
  auto_routing: true    # Automatically selects optimal model per task tier

  # LM Studio (Local Default)
  lm_studio:
    base_url: "http://127.0.0.1:1234/v1"
    api_key: "lm-studio"

  # OpenAI Cloud
  openai:
    api_key: ""         # e.g. "sk-proj-..."
    base_url: "https://api.openai.com/v1"

  # Anthropic Cloud (Claude)
  anthropic:
    api_key: ""         # e.g. "sk-ant-..."
    base_url: "https://api.anthropic.com/v1"
```

### 3.2 Unified Multi-Provider Client in `core/llm.py`
Support standard OpenAI API, direct OpenAI SDK usage for OpenAI/LM Studio, and native `httpx` Messages API for Anthropic Claude:

```python
import httpx
from openai import OpenAI

def get_provider(cfg: dict) -> str:
    llm_cfg = (cfg.get("config") or {}).get("llm") or {}
    return llm_cfg.get("provider") or "lm_studio"

async def chat_anthropic(api_key: str, model: str, messages: list, temperature: float, max_tokens: int) -> str:
    system_prompt = ""
    claude_msgs = []
    for m in messages:
        if m.get("role") == "system":
            system_prompt += m.get("content", "") + "\n"
        else:
            claude_msgs.append({"role": m.get("role"), "content": m.get("content")})

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": claude_msgs,
    }
    if system_prompt:
        payload["system"] = system_prompt.strip()

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
```

---

## 4. Component 3: Intelligent Auto-Model Router

Users should not have to manually research and assign model names to orchestrators and planners. Jarvis should **auto-choose the best model for the action**.

### 4.1 Routing Tiers by Provider (`core/model_router.py`)

| Role / Action | OpenAI Tier | Anthropic (Claude) Tier | LM Studio (Local Auto-Detect) |
| :--- | :--- | :--- | :--- |
| **Planner & Tools** (Complex tasks, coding, shell) | `gpt-4o` | `claude-3-7-sonnet-latest` | Best loaded coding model (e.g. `qwen2.5-coder`) |
| **Vision** (Screen analysis, OCR) | `gpt-4o` | `claude-3-5-sonnet-latest` | Best loaded VL model (e.g. `qwen2.5-vl`) |
| **Orchestrator** (Conversational core) | `gpt-4o` | `claude-3-5-sonnet-latest` | Primary loaded instruct model |
| **Memory & Quick Answers** (Fast recall, classification) | `gpt-4o-mini` | `claude-3-5-haiku-latest` | Fast lightweight model (e.g. `llama-3.2-3b`) |

### 4.2 LM Studio Dynamic Detection
When running with LM Studio, Jarvis queries `/v1/models`:
* If a model with `coder` or `code` is loaded $\rightarrow$ assigned to `planner` and `tool_control`.
* If a model with `vl` or `vision` is loaded $\rightarrow$ assigned to `vision`.
* If only 1 model is loaded $\rightarrow$ seamlessly shared across all roles without failing.

---

## 5. Component 4: Onboarding & Settings Overhaul

### 5.1 Onboarding Step 3: Provider Selector
Update `ui_pet/src/index.html` (Modal Step 3):
1. **Provider Tabs:** `[ LM Studio (Local) | OpenAI | Anthropic Claude ]`
2. **Dynamic Input:**
   - When **OpenAI** is selected: Single input: `OpenAI API Key` (`type="password"`).
   - When **Claude** is selected: Single input: `Anthropic API Key` (`type="password"`).
   - When **LM Studio** is selected: `Endpoint URL` (`http://127.0.0.1:1234/v1`).
3. **Clean Connection Badge:**
   - Replace the ugly raw dump of 5 model names with a formatted card:
   ```html
   <div class="model-connect-card success">
     <div class="mcc-head"><span class="mcc-dot"></span> Provider Ready</div>
     <div class="mcc-detail">Auto-routed: Heavy tasks (GPT-4o / Sonnet) • Fast responses (Mini / Haiku)</div>
   </div>
   ```

### 5.2 Replace Legacy Saturn Orbs with Mochi Avatar
* In the sidebar brand header (`#sidebar .brand .logo`), replace `<div class="logo orb">` with the animated `<svg class="mochi-logo"><use href="#i-mochi"/></svg>`.
* In the sidebar footer (`.pet-mini .pet-orb`), replace the orange sphere with `<svg class="mochi-mini"><use href="#i-mochi"/></svg>`.
* In the Onboarding modal hero (`.onboard-hero-orb`), replace the orange sphere with the charming **2D Mochi illustration**.

---

## 6. Component 5: Complete Dark Theme & Memory Studio Polish

### 6.1 Fix Blinding White Inputs (`app.css`)
Ensure all inputs, selects, and textareas inherit the application's sleek dark palette:
```css
.memory-add-form select,
.memory-add-form textarea {
  background: #14151a !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  color: #eceef4 !important;
  border-radius: 10px !important;
  padding: 10px 14px !important;
  font-family: inherit;
  font-size: 13.5px;
  outline: none;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.memory-add-form select:focus,
.memory-add-form textarea:focus {
  border-color: #f59e0b !important;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2) !important;
}

.memory-add-form select option {
  background: #1a1b22;
  color: #eceef4;
}
```

### 6.2 Button Styling Polish
Replace the harsh rectangular orange blocks with sleek pill-shaped controls:
```css
button.primary,
.memory-add-actions button.primary,
#memory-add-btn {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border: none;
  border-radius: 999px;
  color: #121316;
  font-weight: 700;
  padding: 8px 18px;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(245, 158, 11, 0.25);
  transition: all 140ms ease;
}
button.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35);
}
```

---

## 7. Implementation Checklist for `opencode`

| Order | Subsystem | Target Files | Key Actions |
| :---: | :--- | :--- | :--- |
| **1** | **Bespoke Titlebar** | `src-tauri/tauri.conf.json`<br>`ui_pet/src/index.html`<br>`ui_pet/src/app.css` | Set `decorations: false`, add `#window-titlebar` with Mochi logo & window controls (`win-min`, `win-max`, `win-close`). |
| **2** | **Multi-Provider LLM** | `core/llm.py`<br>`config/config.yaml`<br>`core/config.py` | Add OpenAI and Anthropic Claude clients; accept API keys directly without endpoint hurdles. |
| **3** | **Auto-Model Router** | `core/model_router.py`<br>`agents/orchestrator.py` | Automatically map tasks to Fast tier (`mini`/`haiku`) vs Heavy tier (`gpt-4o`/`sonnet`) vs Vision tier. |
| **4** | **Onboarding & Settings** | `ui_pet/src/index.html`<br>`ui_pet/src/onboarding.js`<br>`ui_pet/src/settings.js` | Add provider tabs (`LM Studio`, `OpenAI`, `Claude`) in Onboarding Step 3 & Settings; format connection badge. |
| **5** | **Mochi Logo Everywhere** | `ui_pet/src/index.html`<br>`ui_pet/src/app.css` | Replace legacy orange Saturn sphere orbs with the `#i-mochi` mascot icon. |
| **6** | **Memory Form Dark Theme** | `ui_pet/src/app.css` | Style `.memory-add-form select` and `textarea` in dark mode (`#14151a`); pill-shaped buttons. |

---

## 8. Verification & Acceptance Criteria

1. **Titlebar:** Main window has no default OS window border; custom titlebar allows dragging, minimizing, maximizing, and closing with smooth hover effects.
2. **Provider Key Input:** Entering an OpenAI key (`sk-...`) or Claude key (`sk-ant-...`) validates connection immediately without entering endpoints.
3. **Auto-Model Selection:** Complex prompts automatically use the Heavy tier (`gpt-4o` or `sonnet`), while memory recall and quick answers automatically use the Fast tier (`gpt-4o-mini` or `haiku`).
4. **No White Input Boxes:** Memory Studio `<select>` and `<textarea>` render cleanly with dark backgrounds and warm amber focus rings.
5. **Mochi Presence:** The Mochi mascot replaces the generic orange Saturn sphere in the sidebar and onboarding modal.

---

## 9. As-Built Notes (implemented)

### 9.1 What shipped

- **Titlebar:** `tauri.conf.json` main window `decorations: false`; `index.html` gained `#window-titlebar` (Mochi logo, "Jarvis" title, `v0.2` pill, `win-min`/`win-max`/`win-close`). `titlebar.js` binds the controls; draggable regions are marked with `data-tauri-drag-region` on the titlebar children (Tauri only honors the exact event target). `#app` got `margin-top: 36px` + `height: calc(100vh - 36px)` so content never slides under the fixed bar.
- **LLM engine:** `core/llm.py` now serves three providers (`openai`, `anthropic`, `lm_studio`) from one config block; key-only entry for cloud providers (no custom endpoints required). Verified live: LM Studio returns 5 models; empty OpenAI key fails gracefully with *"Enter an OpenAI API key (sk-...) to test."*; a bogus Anthropic key surfaces the upstream `401 authentication_error`.
- **Auto-router:** new `core/model_router.py` — `route(cfg, tier)` picks Fast/Heavy/Vision models per provider (`lm_models()` caches `/v1/models` for 45 s; local picks regex-classify vision/code/small models), and `route_query()` heuristics (word count, code blocks, heavy keywords) choose the tier.
- **Config:** new top-level `llm:` block (`provider`, `auto_routing`, `openai.api_key`, `anthropic.api_key`). The legacy top-level `lm_studio:` block was **kept intact** (still read by `backend/app.py` and `core/llm.py`); Settings reads/writes `llm.*` only. `settings.js collect()` clones the current config so `runtime.first_run` and `llm` survive `save_settings`' full-yaml replace.
- **Settings UI:** `#sec-models` gained a Model Provider card — `#provider-seg` segmented picker (LM Studio / OpenAI / Claude), per-provider fields (`#prov-lm-field`, `#prov-openai-field`, `#prov-anthropic-field`), Test connection (`#test`), and a DOM-built `.model-connect-card` result (`ws.js renderConnectCard`, max 8 models). Cloud key fields auto-test (debounced 900 ms) as you type; everything marks the form dirty.
- **Onboarding Step 3:** renamed "Model connection" with the same three-way picker (`#ob-provider-seg`), per-provider fields, `Check connection` + `#ob-connect-card`. Finish persists `llm` provider/keys (skip-save logic extended so provider changes still trigger save).
- **Dark inputs fix (verification finding):** the `.field input` dark-theme selector covered `type="text"`/`type="number"` but **not** `type="password"` — the cloud key inputs rendered white in the real window. Added `input[type="password"]` to the selector plus a `:-webkit-autofill` override (dark inset shadow + text color) so browser-saved keys can't white-wash the field. Rebuilt and re-captured.

### 9.2 Deviations from the spec

- **Legacy `lm_studio:` top-level config block kept** instead of migrating readers — lower blast radius; new code only touches `llm:`.
- **Router wired at the three real LLM call sites** (`memory_agent._answer` → `route_query`, `tool_control._summarize_file` → `route(cfg,"heavy")`, `screen_vision._vision_model` → `route(cfg,"vision")`) rather than inside `agents/orchestrator.py`, which has no direct `llm` calls.
- **`test_lm_studio` carries `provider` + `api_key`** through the WS bridge (`ws.js testLm(url, provider, api_key)`), so Test connection validates the *selected* provider, not always LM Studio.

### 9.3 Build gotchas (reproducible)

- **Do not wrap build commands in vcvars** in this shell — the vcvars chain fails silently and leaves a stale exe. Working forms:
  - PyInstaller: `& .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean jarvis-backend.spec` (in `jarvis-desktop-pet`, ~80 s).
  - Tauri shell: `cmd /c 'cargo build --release'` (in `ui_pet/src-tauri`, ~10 s).
- After copying into `test_install`, **verify `Get-FileHash -Algorithm MD5`** matches `target\release\jarvis-pet.exe` — one deploy round shipped a stale binary (23:06 build, pre-`llm.py` edits) and the WS probe caught it.
- Frontend assets are embedded at cargo build time; editing `ui_pet/src/*` requires a cargo rebuild + exe redeploy before the app reflects it.
- The app is WS-only (`GET /` 404s are normal); health checks go through `ws://127.0.0.1:8765/ws`. Settings replies use type `settings` with **no** `correlation_id`; `test_lm_studio` echoes its `correlation_id`.

### 9.4 UI automation note (verification tooling)

- Headless **mirror tabs** (9334) go stale on screenshot (occluded tab) and their viewport differs (1416×808 vs the real 1100×760) — verify mirror state via `Runtime.evaluate` DOM dumps, not screenshots.
- The real window's sub-nav responds to physical clicks after a rebuild; during one pre-rebuild session the "Models & Connection" row ignored `mouse_event` while siblings worked. Windows UI Automation (`comtypes` + `IUIAutomationInvokePattern.Invoke()`, found via `ElementFromPoint` → walk up to `BrowserRootView` → `FindAll` by name) drives the real WebView2 DOM reliably and is the recommended capture driver for `inspect_ui.ps1` evidence.

### 9.5 Verification evidence

- `py_compile` (llm, model_router, memory_agent, tool_control, screen_vision, ws_bridge) and `node --check` (settings, onboarding, ws, titlebar) clean.
- Router/LLM probes: `ALL LLM/ROUTER PROBES PASS` — live LM Studio picks vision=`qwen2.5-vl-7b`, heavy=`qwen2.5-coder-7b`, fast=`llama-3.2-3b`.
- WS probe on the frozen app: settings carry `llm`, lm_studio test ok (5 models), OpenAI/Anthropic error paths as in §9.1.
- `inspect_states` 16/16; captures: frameless titlebar, dark inputs (incl. the password fix), provider picker LM Studio ↔ OpenAI toggling fields + Save/dirty state, Models & Connection reachable by real mouse click.
- **Quality gates: 15/15 PASS** (`fast_router` 71/71, `vocab` 17/17, `injector` 17/17, `dictation_flow` 15/15, `dictation_ui` 27/27, `audio_cache` ALL, `phase1_earcons` 12/12, `approval_flow` 9/9, `revamp2_check`, `revamp2_interact` 56/56, `hotkey_e2e`, `hook_e2e` 37/37, `phase5_e2e` 14/14, `phase5_dock` 27/27, `phase5_visual` 28/28). Two run-of-record issues were environmental, not code: a prior interrupted earcons run had persisted `voice.ui_sounds: false` (test expects default unmuted — config reset to `true`, the documented default), and the earcons target picker selected `dock.html` when the CDP target list reordered (picker now requires `index.html`).
