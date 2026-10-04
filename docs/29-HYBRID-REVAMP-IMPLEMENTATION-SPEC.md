# Hybrid Revamp Specification: Implementing Coucou & Hey Jev Strengths into PulseAI (Jarvis)

**Document:** 29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md  
**Status:** Approved Architecture & Implementation Blueprint  
**Target Platform:** Windows 10/11 (Primary), Linux, macOS (Cross-Platform Core)  
**Parent References:** [27-UI-REVAMP.md](file:///d:/Personal_projects/2/Personal_AI/docs/27-UI-REVAMP.md), [28-COMPETITIVE-COMPARISON-COUCOU-HEYJEV.md](file:///d:/Personal_projects/2/Personal_AI/docs/28-COMPETITIVE-COMPARISON-COUCOU-HEYJEV.md)

---

## 1. Executive Vision: The Sovereign Desktop Powerhouse

PulseAI (Jarvis) is an autonomous, local-first companion with real multi-agent planning, PC control, and safety guardrails. However, comparative analysis against **Coucou** and **Hey Jev** reveals key areas where user experience, developer workflow, and voice responsiveness can be dramatically improved.

This specification blueprints the architecture to:
1. **Adopt all positive strengths** from Coucou (developer coding agent hooks, live diff ticker, file drag-and-drop onto pet, edge docking, tactile audio cues, credential manager security).
2. **Adopt all positive strengths** from Hey Jev (sub-50ms pre-cached voice acknowledgments, system-wide cursor dictation, phonetic pronunciation replacement dictionary, zero-LLM fast deterministic intent routing, compound voice command splitting).
3. **Fix existing limitations in Jarvis** (cold-start voice latency, VRAM friction, voice isolated only inside chat input, lack of awareness of CLI coding agents, absence of tactile earcons/chimes).
4. **Strictly avoid the flaws of both competitors** (Coucou's complete lack of autonomy/voice and cloud API costs; Hey Jev's strict macOS lock-in, reliance on 3 paid cloud APIs, hardcoded AppleScript limitations, and complete absence of safety approval gates).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              THE UNIFIED JARVIS ARCHITECTURE                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  SURFACE LAYER (Tauri + Three.js + WebSockets)                                         │
│  • 3D Living Pet (Movable, Physics, Moods)  • Retractable Top-Edge Dock ("Dynamic Island")│
│  • Full 1100x760 Command Center             • Floating Dictation Waveform Bubble       │
│  • Drag-and-Drop Ingestion Target            • Human-in-the-Loop Approval Cards        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  FAST-PATH ROUTER & AUDIO ENGINE (Sub-50ms Voice)                                      │
│  • Pre-Rendered Kokoro TTS Cache (`cache/tts/`) for instant voice confirmations         │
│  • Deterministic Intent Router (Volume, Spotify, Apps, Timers, Power - 0ms LLM wait)   │
│  • Global Dictate-to-Cursor Engine (Direct Windows SendInput / OS text injection)      │
│  • Phonetic Correction Dictionary (`vocabulary.json` pre-transcription map)            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  DEVELOPER & AGENT BRIDGE (`jarvis-hook`)                                              │
│  • Named Pipe (Windows) / Unix Socket Relay for Claude Code, Cursor, Codex, Agy        │
│  • Live File Diff Ticker (+N, -M lines) & In-Notch / In-Pet Terminal Approval Cards    │
│  • Terminal Focus & PID Jumping (Instantly brings active coding agent console to top)  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  SOVEREIGN CORE & SAFETY MOAT (Preserved & Protected)                                  │
│  • 100% Local Inference (LM Studio OpenAI-compatible SSE API)                          │
│  • Dynamic VRAM Lifecycle Manager (On-demand model loading, 60s idle-unload)           │
│  • Orchestrator / Planner / Tool Execution / Vision Agents                             │
│  • Pre-Execution Risk Evaluator (1-10) with Armed Correlation-ID Anti-Duplicate Gating │
│  • Persistent Local Memory (SQLite + ChromaDB Vector Recall)                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Synthesis Matrix: What to Adopt, Fix, and Avoid

| Domain | What We Adopt from Coucou | What We Adopt from Hey Jev | What We Fix in Jarvis | What We Strictly Avoid (Competitor Flaws) |
| :--- | :--- | :--- | :--- | :--- |
| **Voice & Speech** | Audio sound design / chimes (earcons for states) | • Pre-cached TTS audio clips (<50ms latency)<br>• Global Dictate-to-Cursor<br>• Phonetic dictionary (`vocabulary.json`) | Eliminates the 1.5s neural TTS generation delay on standard acknowledgments | • Avoid Hey Jev's cloud-only Fish Audio and OpenAI dictation APIs (keep 100% local)<br>• Avoid Coucou's zero-voice limitation |
| **Developer Tools** | • Agent hook bridge for Claude Code, Cursor, agy<br>• Live file diff ticker (+N, -M)<br>• Terminal session jump | Fast compound voice commands ("build project and open browser") | Enables Jarvis to supervise terminal coding tools instead of operating in an isolated silo | Avoid Coucou's lack of execution capability (Jarvis can both supervise AND autonomously act) |
| **Desktop UX & Form Factor** | • Retractable top-edge dock mode<br>• File drag-and-drop onto pet<br>• Drag pet onto window for visual context | Floating dictation waveform bubble at bottom of screen | Solves 300x240 pet window getting in the way of workspace clicks | • Avoid Coucou's macOS-only notch lock-in (provide screen-edge docking on Windows/Linux)<br>• Avoid Hey Jev's lack of 3D visual character |
| **PC Automation & Speed** | Credential Manager DPAPI security | Fast-path deterministic intent parser (instant media, volume, apps, timers) | Bypasses slow multi-step LLM planner for obvious 1-turn commands | • Avoid Hey Jev's brittle, Mac-only AppleScript scripts (use robust Win32/cross-platform APIs)<br>• Avoid Hey Jev's zero-safety direct execution |
| **Safety & Privacy** | Non-blocking hook timeouts (fallback to terminal) | Transparent privacy disclosures | Clarifies timeout visual cues and auto-sync across windows | Avoid Hey Jev's total absence of human-in-the-loop safety approvals for destructive commands |
| **Hardware & Performance** | Extremely low idle footprint | Local Whisper for basic command parsing | Optimizes model loading so consumer 8GB/12GB GPUs don't stutter | Avoid Coucou's reliance on recurring cloud subscription keys (Anthropic / OpenAI) |

---

## 3. Module 1: The Fast-Path Voice & Audio Engine

### 3.1 Pre-Rendered Kokoro Neural TTS Cache
**Problem in Jarvis:** When Jarvis is asked to do something, synthesizing *"Working on it"* or *"Done"* through Kokoro-82M requires 800ms–1800ms on CPU/GPU, creating awkward pauses before actions begin.  
**Solution (from Hey Jev):** Pre-generate high-frequency static voice responses using Kokoro during initial setup and cache them as raw uncompressed WAVs in `jarvis-desktop-pet/cache/tts/`.

#### Implementation:
- **Pre-rendered Clips Dictionary:**
  ```python
  PRE_RENDERED_VOCAL_RESPONSES = {
      "ack.working": "Working on that now.",
      "ack.done": "Done.",
      "ack.listening": "Listening.",
      "ack.stopped": "Stopped.",
      "ack.denied": "Action denied. Nothing was changed.",
      "ack.error": "Something went wrong.",
      "ack.approval": "I need your approval to proceed.",
      "ack.confused": "Could you say that again?",
      "ack.wake": "Hey there.",
      "ack.dictation_start": "Transcribing...",
      "ack.dictation_stop": "Transcribed."
  }
  ```
- **Playback Architecture:**
  - On startup or voice style switch in Settings, a background generator renders any missing WAVs at 24kHz using the selected Kokoro voice ID.
  - When the orchestrator emits a standard acknowledgment, `core.audio_player` bypasses the Kokoro inference thread entirely and directly streams the pre-cached WAV into `sounddevice.OutputStream`.
  - **Latency:** Drops from ~1400ms to **< 35ms**.

### 3.2 Global "Dictate-to-Cursor" Mode
**Problem in Jarvis:** Voice input is currently trapped inside the Jarvis main window textarea. If the user is writing an email in Outlook, typing in VS Code, or commenting on GitHub, they cannot speak to type.  
**Solution (from Hey Jev):** A system-wide dictation mode activated by hotkey or voice command that pipes transcribed speech directly into whatever window holds cursor focus.

#### Implementation:
1. **Activation:**
   - **Hotkey:** Global `Ctrl+Alt+D` (configurable in Settings).
   - **Voice:** Say *"Hey Jarvis, transcribe"* or *"Hey Jarvis, dictate"*.
2. **UX Presentation:**
   - A floating waveform pill (`#dictation-bubble`) appears near the bottom-center of the screen with a live visualizer (using the existing `ui.mic_level` stream).
   - The 3D pet switches to `listening` mood with an antenna pulse.
3. **Deactivation & Text Injection:**
   - Press hotkey again or say *"stop transcribing"*.
   - The audio segment is transcribed locally using `faster-whisper`.
   - **Text Injection Strategy (Windows):**
     - Primary: Windows `SendInput` API via `ctypes` (or `pyautogui.write()`) to type text directly into the focused control.
     - Fallback / Large Block: Copies transcribed text to the clipboard and sends `Ctrl+V`, restoring previous clipboard contents after 100ms.
4. **History Log:**
   - Appends all dictations with timestamp and active application title to `%LOCALAPPDATA%\Jarvis\dictation_history.jsonl`.

### 3.3 Phonetic Vocabulary Replacement Dictionary (`vocabulary.json`)
**Problem in Jarvis:** Local Whisper models often mishear technical acronyms, developer handles, or foreign names (e.g. hearing "clawed code" instead of "Claude Code", "cube control" instead of "kubectl").  
**Solution (from Hey Jev):** A lightweight pre/post-transcription dictionary mapping user-defined misrecognitions to canonical words.

#### Schema (`config/vocabulary.json`):
```json
{
  "mappings": [
    {
      "word": "kubectl",
      "heard_as": ["cube control", "cube ctl", "koob ctl", "cube cuddle"]
    },
    {
      "word": "Claude Code",
      "heard_as": ["cloud code", "clawed code", "claud code"]
    },
    {
      "word": "LM Studio",
      "heard_as": ["element studio", "lm studio", "ellen studio"]
    },
    {
      "word": "Antigravity",
      "heard_as": ["anti gravity", "anti-gravity", "agy"]
    }
  ]
}
```
- **Settings UI:** A dedicated **Dictionary** table in the Settings view allowing users to add/edit custom mappings.
- **Engine:** Intercepts raw Whisper output, evaluates whole-word token matches and regex patterns, and replaces them before passing text to the Orchestrator or Dictation injector.

### 3.4 Zero-LLM Fast Deterministic Intent Router
**Problem in Jarvis:** Asking Jarvis to *"turn up volume"* or *"pause Spotify"* sends the prompt into the full Orchestrator $\rightarrow$ Planner $\rightarrow$ LM Studio LLM pipeline, taking 2–4 seconds for a 5-millisecond task.  
**Solution (from Hey Jev):** A deterministic regex/speculative intent router that handles frequent media, volume, application, timer, and power commands instantly without invoking the LLM.

#### Capabilities & Execution Mapping:
| Trigger Pattern | Action Executed (Windows Native) | Latency |
| :--- | :--- | :--- |
| `volume (up|down|mute|max|\d+)` | Windows CoreAudio API (`pycaw`) | < 10ms |
| `(pause|play|next|previous) spotify` | Windows Virtual Keycodes (`VK_MEDIA_PLAY_PAUSE`, `VK_MEDIA_NEXT_TRACK`) | < 5ms |
| `open (app name)` | Fuzzy match against Start Menu / App directory (`apps.json`) | < 50ms |
| `(lock|sleep|shutdown) pc` | `LockWorkStation()` / `SetSuspendState()` (Subject to Approval gate if shutdown) | < 15ms |
| `set timer for (\d+) (seconds|minutes)` | Local background asyncio timer with alert chime | < 5ms |

- **Compound Command Splitting:** Detects compound conjunctions (e.g., *"pause spotify and turn down volume"*). Splits into two fast-path actions executed sequentially with zero LLM overhead.
- **Fallback:** If no deterministic pattern matches with $\ge 90\%$ confidence, the prompt transparently falls back to the Orchestrator/Planner LLM.

---

## 4. Module 2: The Developer & Coding Agent Bridge (`jarvis-hook`)

### 4.1 CLI Agent Relay Architecture
**Problem in Jarvis:** Developers frequently run CLI agents (Claude Code, Cursor, Codex, Gemini CLI, Antigravity `agy`) in their terminal. Jarvis has no awareness of these sessions and cannot assist or observe them.  
**Solution (from Coucou):** Implement `jarvis-hook`, a lightweight IPC relay that allows terminal coding agents to send session status, file diffs, and permission approval requests directly to Jarvis.

```
┌─────────────────────────┐          Named Pipe (Windows)          ┌──────────────────────────┐
│ CLI Agent (Claude Code, │ ──────> \\.\pipe\jarvis-hook ────────> │ Jarvis Event Bus         │
│ Cursor, Codex, agy)     │ <────── (< 300ms non-blocking) <────── │ • Shows 3D Pet Approval  │
└─────────────────────────┘                                        │ • Displays File Diff     │
                                                                   │ • Syncs with Dashboard   │
                                                                   └──────────────────────────┘
```

#### Relay Mechanics:
1. **Windows Relay Executable (`bin/jarvis-hook.exe`):**
   - A tiny Rust/C binary installed to `%LOCALAPPDATA%\Jarvis\bin\jarvis-hook.exe`.
   - Communicates with Jarvis over a local Windows Named Pipe (`\\.\pipe\jarvis-hook`).
   - **Non-Blocking Safety (Coucou Pattern):** Given a strict 300ms timeout to connect to Jarvis. If Jarvis is not running or slow, the hook immediately exits with code 0. **The terminal agent is never stalled.**
2. **Hook Integrations:**
   - **Claude Code:** One-click installer in Settings that adds the hook to `%USERPROFILE%\.claude\settings.json` with a backup.
   - **Antigravity (`agy`):** Registers hooks in `%USERPROFILE%\.gemini\config\hooks.json`.
   - **Generic CLI:** Supports `coucou_agent` standard JSON payload.

### 4.2 Live File Diff Ticker & In-Context Approval
- **Live Ticker:** When Claude Code or Cursor edits files, `jarvis-hook` sends file paths and line delta metrics:
  ```json
  {"type": "agent.edit", "file": "src/auth.ts", "added": 14, "removed": 3}
  ```
  - The 3D Pet's speech bubble displays: `Editing src/auth.ts (+14 -3)`.
  - The Chat / Activity panel displays a live collapsible unified diff viewer.
- **Terminal Approval Interception:**
  - When the CLI agent requires permission (e.g., tool execution, bash command), `jarvis-hook` sends the approval payload to Jarvis.
  - Jarvis displays the unified **Approval Card** with **Allow once**, **Deny**, and **Always allow for session** directly in both the 3D Pet bubble and the Command Center.
  - Clicking a button transmits the decision back over the pipe into the terminal agent in real time.
- **Terminal Jump:** An "Open Terminal" button on the approval card brings the specific Windows Terminal / PowerShell window (matched by PID) to the foreground.

---

## 5. Module 3: Ergonomic Presence, Tactile Physics & Sound Design

### 5.1 Retractable Top-Edge Dock ("Dynamic Island" Mode)
**Problem in Jarvis:** While the 300x240 floating transparent pet is visually engaging, on single-monitor laptops it can occasionally obscure underlying windows or clickable UI buttons.  
**Solution (from Coucou):** Add a second companion presentation mode: a retractable **Top-Edge Dock** that hugs the top border of the monitor.

#### Dual-Mode Companion Selection:
Users can toggle their preferred companion presentation in Settings:
1. **Floating 3D Pet Window:** The current 300x240 always-on-top transparent character that can be placed anywhere.
2. **Top-Edge Dock ("Island"):**
   - Rests flush at the top center of the screen (height: 38px, width: 220px).
   - Shows a compact 2D or mini-3D Jarvis core, connection status dot, and active agent status pill.
   - **Hover Behavior:** Moving the cursor to the top edge expands the dock into a sleek 120px command pill showing quick mic, chat, settings, and pending task progress.
   - **Non-Intrusive:** Automatically retracts when the cursor leaves.

### 5.2 Drag-and-Drop Ingestion on Pet
**Problem in Jarvis:** Adding files or context requires opening the full chat window and clicking an attachment button.  
**Solution (from Coucou):** Make the floating 3D pet (or the Top-Edge Dock) a live drag-and-drop target.

#### Mechanics:
- When a user drags a file (PDF, code file, text document, or image) over the 3D pet window:
  - Three.js animation triggers an **"eating/inspecting"** state (mouth opens, orbital particles swirl around the cursor, antenna glows bright violet).
  - On file release (`drop` event):
    - Jarvis consumes the file path.
    - If it's an image: automatically prepares Vision analysis.
    - If it's a code/text/PDF document: extracts text content and populates the composer or executes a quick summary.
    - The pet confirms with an acknowledgment chime and speech bubble: *"Inspecting [filename]..."*

### 5.3 Window Context Attachment (Window Snapping)
- **Feature (from Coucou):** Dragging the pet onto another active application window (or pressing a hotkey `Ctrl+Alt+W`) attaches that target window as context.
- **Execution:** Takes an instant high-resolution screenshot of the target window's client bounds using `PrintWindow` Win32 API, passes it to the Vision agent, and prompts the user: *"What would you like me to do with this window?"*

### 5.4 Tactile Audio Sound Design (Earcons)
**Problem in Jarvis:** Jarvis is completely silent except for Kokoro TTS spoken responses. There is no non-vocal audio feedback to indicate background state changes.  
**Solution (from Coucou):** Implement 12 subtle, high-end procedural audio cues (earcons) played via `sounddevice` or Web Audio API.

#### Audio Palette Specifications:
| Sound Cue | Trigger | Aesthetic / Acoustic Character |
| :--- | :--- | :--- |
| `snd_wake` | Wake-word detected | Gentle 2-note rising chime (440Hz $\rightarrow$ 880Hz, soft sine wave) |
| `snd_listen_start` | Mic opens | Subdued tactile click |
| `snd_listen_stop` | Mic closes / transcribing begins | Low soft settle tone |
| `snd_success` | Tool execution / task completes | Crisp bright 3-note major chord |
| `snd_error` | Tool failure or disconnection | Muted low double-tap alert |
| `snd_approval` | High-risk approval card arrives | High-contrast melodic warning chime |
| `snd_squish` | Clicking/poking the 3D pet | Tactile soft pop / organic squish |
| `snd_dock_peek` | Top-edge dock expands | Soft swoosh / air glide |

- Includes a master **Mute UI Sounds** switch in Settings $\rightarrow$ Voice.

### 5.5 Next-Gen Pet Revamp: Elevating from "Childish Prototype" to Product-Grade Tactile Companion

#### 5.5.1 The Problem: The "Programmer Art" Pitfall
The original prototype pet (a flat blue circle with a "J" or unrefined 3D spheres) looked like a primitive school project. By comparison, Coucou's "Mochi" achieved viral acclaim because it feels like a **high-end designer toy**—cohesive, tactile, physically responsive, and alive. 

The revamped Jarvis Pet must bridge **Coucou's delightful, squishy, high-polish aesthetics** with **Jarvis's cutting-edge AI identity**: a living, robotic squircle companion that feels warm, intelligent, and physically real on the desktop.

#### 5.5.2 Visual Identity & Geometry: Continuous Curvature Squircle
- **Geometric Foundation:** Ditch primitive spheres and flat 2D circles. The pet body is defined as an organic 3D Superellipse / Lamé Curve:
  $$\left|\frac{x}{a}\right|^n + \left|\frac{y}{b}\right|^n + \left|\frac{z}{c}\right|^n \le 1 \quad \text{where } n \approx 4.2$$
  This yields a continuous-curvature "squircle" with zero abrupt crease lines and soft organic corner transitions.
- **Dual-Pass Material & Shading:**
  - *Base Layer:* Warm matte silicone / ceramic finish with soft subsurface scattering (SSS) simulation that catches ambient desktop lighting.
  - *Accent & Core Layer:* Internal luminous core with subtle chromatic rim-lighting (default cyan-blue `#00F0FF`, shifting to violet `#A855F7` during cognitive reasoning, amber `#F59E0B` during safety alerts, and emerald `#10B981` upon completion).
  - *Micro-Reflections:* Dual soft specular highlights that respond to virtual light sources, giving depth without glossy plastic glare.

#### 5.5.3 Projected Spherical Eye Kinematics & Biological Gaze
- **Spherical Surface Projection (The Coucou Technique):**
  - Rather than drawing flat 2D sticker eyes, the facial elements are calculated via spherical coordinate projection $(\theta, \phi)$ mapped onto an imaginary 3D ellipsoid surface.
  - As the pet tilts or turns to track the cursor, the eyes foreshorten naturally around the curved contour of the body, giving genuine 3D perspective and depth.
- **Expressive Eye Shapes:**
  - High-res SVG / Canvas 2D squircle capsules with dynamic corner radii.
  - *Micro-Blinking System:* Natural blink generator with randomized intervals (every 2.5–6.0 seconds), complete with occasional double-blinks and half-lids when relaxed.
  - *Saccadic Cursor Tracking:* Instead of a robotic, linear lerp, eyes move toward the mouse cursor using spring-damped saccadic micro-steps (flicking rapidly between focal points like real biological eyes, with gentle damping).

#### 5.5.4 Mass-Spring Tactile Physics (Squash, Stretch & Inertia)
- **RK4 / Verlet Spring Damper Physics:**
  - The pet body is governed by dual coupled 2nd-order spring-damper equations:
    $$\ddot{x} + 2\zeta\omega_n\dot{x} + \omega_n^2(x - x_{\text{target}}) = 0$$
  - Parameters: Natural frequency $\omega_n = 18.5$, damping ratio $\zeta = 0.65$ for bouncy, organic jiggle.
- **Volume Conservation Law (Squash & Stretch):**
  - When compressed along the vertical axis ($\Delta y < 0$), the horizontal dimensions automatically expand ($\Delta x = \Delta z = -\frac{1}{2}\Delta y$) to preserve visual volume, creating an authentic soft-body rubber/gelatin feel.
- **Interactive Poking & Rebound Wobble:**
  - Clicking on the pet calculates the hit point vector relative to center and applies an instantaneous impulse along that vector.
  - The pet indents at the contact point and wobbles back to rest over 350ms, accompanied by the tactile squish earcon (`snd_squish`).
- **Drag Velocity Trailing & Elastic Snap-Back:**
  - Dragging the pet stretches its body along the movement vector proportional to drag velocity (taffy stretch).
  - Releasing snaps the pet back to its equilibrium shape with a satisfying damped oscillation.

#### 5.5.5 Expressive State Machine & Micro-Reactions
The pet is never a static sprite. It transitions between dynamic behavioral states driven by the agent event bus:

| State | Eye Expression | Body Motion / Shader Glow | Audio Earcon | Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **Idle (Awake)** | Relaxed soft capsules, saccadic tracking | 0.12Hz rhythmic sinusoidal breathing, subtle float | Silent | Normal desktop presence |
| **Idle (Sleep/Eco)** | Gentle curved crescents (eyes closed) | Deep slow breathing, rim light dims to 15% warm ember | Soft purr settle | > 5 minutes of desktop inactivity |
| **Curious (Hover)** | Eyes enlarge 25%, slight head tilt | Body levitates +6px, particles orbit faster | Soft curious chirp | Mouse cursor hovers over pet |
| **Poked / Squished** | Squinted joy or surprise | Instant volume-conserving compression & rebound | `snd_squish` | Direct click / poke |
| **Dizzy / Annoyed** | Spiral/spinning eyes, blushing cheeks | Fast body vibration, annoyed sweat-drop micro-emote | Disgruntled trill | Rapid clicking (> 5 clicks in 1.5s) |
| **Listening** | Bright, widened eyes locked forward | Antenna pulses in real-time with microphone amplitude | `snd_listen_start` | Wake-word or hotkey activated |
| **Thinking / Planning** | Eyes glance upward-right in thought | Rotating orbital holographic ring, violet core pulse | Subtle low ambient hum | Planner / LLM inference active |
| **Executing / Tool** | Determined focused eyelids | Confident slight lean, tool glyph glowing inside core | Subtle tactile tick | Tool execution underway |
| **Inspecting / Ingesting**| Wide excited eyes, mouth open | Gravitational pull of particles toward dragged file | Intake chime + gulp | File dragged over pet window |
| **Approval Alert** | Attentive alert posture | Safety-amber rim glow, body stands tall | `snd_approval` | Risk $\ge 6$ action requires HITL |

#### 5.5.6 Ingestion Physics: The File "Eating" Interaction
- When the user drags a file (PDF, image, code) over the pet's transparent window:
  1. The pet's body leans toward the cursor coordinates with mouth opened in anticipation.
  2. Floating magnetic particle streams are sucked from the cursor tip into the pet's core.
  3. Dropping the file triggers a delightful "gulp/crunch" bounce animation with a bright flash in the core, playing `snd_success`.
  4. The pet displays an animated chewing/digest state while the file is hashed and ingested into the LLM context, outputting: *"Inspecting [filename]..."*

#### 5.5.7 Modular Wardrobe & Theme Engine
Coucou's seasonal hats and outfits gave it massive personality. Jarvis introduces an optional **Accessory & Colorway System**:
- **Colorways (Shader Themes):**
  - `Jarvis Obsidian`: Matte stealth black body with electric cyan internal illumination and neon highlights.
  - `Porcelain Mochi`: Creamy matte white ceramic body with pastel lavender accents and soft pink cheek glows.
  - `Cyberpunk 2077`: Deep dark violet body with vibrant solar-amber and hot-magenta neon trims.
  - `Titanium Frosted Glass`: Semi-translucent frosted glass body with optical refractive caustics.
- **Accessories (Toggable in Settings):**
  - Sleek magnetic designer headphones (pulses when Kokoro TTS speaks).
  - Cyberpunk mono-visor (displays tiny scrolling telemetry / terminal diff metrics).
  - Steaming mini espresso cup docked beside the pet during coding sessions.
  - Seasonal items (winter beanie, party hat).

#### 5.5.8 High-Performance / Low-Power Smart Render Loop
To ensure this visual beauty never impacts gaming or battery life:
- **Adaptive Frame Rate:**
  - Active interaction / animations: Buttery 60 FPS with hardware WebGL acceleration.
  - Static idle state: Drops automatically to 10 FPS with procedural interpolation.
  - Window occluded / backgrounded / sleep mode: Suspends rendering to 0–1 FPS.
- **Resource Budget:** CPU usage stays under **0.5%** and GPU memory under **35MB** VRAM.

---

## 6. Module 4: Preserving & Enhancing Core Jarvis Moats

While integrating the best aspects of Coucou and Hey Jev, Jarvis must **strictly preserve and enhance** its core strengths:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   JARVIS CORE PILLARS (DO NOT COMPROMISE)               │
├────────────────────────────────────────────────────────────────────────┤
│ 1. 100% LOCAL-FIRST SOVEREIGNTY                                        │
│    • Never require cloud API keys for core operation                   │
│    • LM Studio, Kokoro, Whisper, openWakeWord run entirely on-prem     │
│                                                                        │
│ 2. AUTONOMOUS MULTI-AGENT PC CONTROL                                   │
│    • Real planning, tool orchestration, vision, and file execution     │
│    • Do not regress into a passive hook watcher like Coucou            │
│                                                                        │
│ 3. HARDENED HUMAN-IN-THE-LOOP SAFETY                                   │
│    • 1-10 Risk Assessment on all tool actions                          │
│    • Armed correlation IDs and automatic timeout expirations           │
│    • Do not execute unverified commands blindly like Hey Jev           │
│                                                                        │
│ 4. DYNAMIC VRAM RESOURCE MANAGEMENT                                    │
│    • Automatic idle-unloading of models after 60s                      │
│    • Cooldown safeguards to prevent GPU memory thrashing               │
│                                                                        │
│ 5. FIRST-CLASS WINDOWS ARCHITECTURE                                    │
│    • Full Win32 integration, DPAPI credential storage, autostart       │
│    • Never become a Mac-only tool like Hey Jev                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. IPC Message Bus Schema Extensions

To support the hybrid capabilities, the local Python/WebSocket event bus is extended with the following event definitions:

### 7.1 Fast-Path & Dictation Events
```json
// Event: dictation.start
{
  "topic": "dictation.start",
  "type": "dictation",
  "payload": { "target": "cursor", "mode": "system_wide" }
}

// Event: dictation.result
{
  "topic": "dictation.result",
  "type": "dictation",
  "payload": { "text": "transcribed text here", "injected": true, "app": "devenv.exe" }
}

// Event: intent.fast_path
{
  "topic": "intent.fast_path",
  "type": "fast_path",
  "payload": {
    "action": "media_volume",
    "params": { "level": 0.5 },
    "bypassed_llm": true,
    "latency_ms": 8
  }
}
```

### 7.2 Agent Hook Relay Events (`jarvis-hook`)
```json
// Event: agent.hook.session
{
  "topic": "agent.hook.session",
  "type": "hook",
  "payload": {
    "agent": "claude-code",
    "pid": 14280,
    "project": "Personal_AI",
    "status": "running"
  }
}

// Event: agent.hook.diff
{
  "topic": "agent.hook.diff",
  "type": "hook",
  "payload": {
    "file": "src/main.rs",
    "added": 24,
    "removed": 5,
    "patch": "@@ -10,5 +10,24 @@ ..."
  }
}

// Event: agent.hook.approval_request
{
  "topic": "agent.hook.approval_request",
  "type": "hook",
  "correlation_id": "hook-uuid-7712",
  "payload": {
    "agent": "claude-code",
    "tool": "Bash",
    "command": "npm run build",
    "risk": 4,
    "timeout_s": 30
  }
}
```

---

## 8. Phased Implementation Roadmap

### Phase 1: Fast-Path Audio & TTS Pre-Caching (Immediate Impact)
- [ ] Implement `core/audio_cache.py`: Pre-render the 11 canonical Kokoro voice clips into `cache/tts/`.
- [ ] Update `agents/orchestrator.py` and `core/voice_tts.py`: Check audio cache for stock acknowledgments before dispatching to Kokoro model.
- [ ] Integrate 8 procedural UI earcons (`snd_wake`, `snd_success`, `snd_error`, `snd_approval`) into `ui_pet/src/app.css` and `chat.js`.

### Phase 2: System-Wide Dictation & Phonetic Dictionary
- [ ] Implement `tools/dictation_injector.py`: Win32 `SendInput` / clipboard paste injector.
- [ ] Add global hotkey listener (`Ctrl+Alt+D`) in `main.py` / `core/hotkey.py`.
- [ ] Create `config/vocabulary.json` and integrate dictionary replacement engine into `core/stt.py`.
- [ ] Add **Dictionary** and **Dictation History** management tabs into the Settings UI.

### Phase 3: Fast-Path Deterministic Intent Router
- [ ] Implement `core/fast_router.py`: Regex and keyword rule engine for volume (`pycaw`), media keys, application launching (`apps.json`), and system power.
- [ ] Implement compound command splitter for multi-action utterances.
- [ ] Add metric reporting in `rm-status` showing zero-latency LLM bypass counts.

### Phase 4: Developer Agent Hook Relay (`jarvis-hook`)
- [ ] Build `bin/jarvis-hook.exe` (Rust/C named pipe client with 300ms non-blocking timeout).
- [ ] Implement named pipe server in `backend/hook_bridge.py`.
- [ ] Create one-click installer in Settings $\rightarrow$ Integrations for Claude Code (`~/.claude/settings.json`) and Antigravity (`hooks.json`).
- [ ] Build Live Diff Ticker UI in `ui_pet/src/chat.js` and in the 3D pet bubble.

### Phase 5: Ergonomic Presence & File Drag-and-Drop
- [ ] Add HTML5 / Tauri file drop listener over the transparent 3D pet window.
- [ ] Wire file drop to Vision / Summary ingestion pipelines.
- [ ] Implement retractable Top-Edge Dock ("Dynamic Island") layout in `ui_pet/src/index.html` as an optional companion alternative to the floating pet.
- [ ] Build product-grade Superellipse squircle pet renderer (`ui_pet/src/pet_canvas.ts`) with dual-pass matte silicone & subsurface glow.
- [ ] Implement spherical projected eye kinematics with saccadic gaze cursor tracking.
- [ ] Implement RK4 spring-damper squash, stretch, poking wobble, and taffy-drag physics (`ui_pet/src/pet_springs.ts`).
- [ ] Integrate full 10-state emotional reactivity machine (Idle, Eco-Sleep, Poked, Dizzy, Listening, Thinking, Executing, Ingesting, Approval Alert).
- [ ] Build file "eating/crunch" particle ingestion effect and wardrobe/colorway switcher (Obsidian, Porcelain, Cyberpunk, Titanium).
- [ ] Implement adaptive 60 FPS / 10 FPS / 1 FPS low-power render throttling (<0.5% CPU).

---

## 9. Verification & Acceptance Checklist

1. **Sub-50ms Vocal Feedback:** Standard responses (*"Working on it"*, *"Done"*) begin audible playback within 50ms of command recognition.
2. **Dictation to Any App:** Pressing `Ctrl+Alt+D` transcribes speech directly into Notepad, VS Code, or browser inputs without opening Jarvis.
3. **Phonetic Replacement:** Adding `"kubectl"` $\rightarrow$ `"cube control"` in `vocabulary.json` ensures speech recognition always outputs the correct spelling.
4. **Instant Media Control:** Saying *"turn down volume"* executes in <15ms without querying LM Studio or waking the GPU.
5. **Claude Code Interception:** Running `claude` in Windows Terminal reflects active edits in the pet bubble and routes permission prompts to Jarvis's Allow/Deny card.
6. **File Ingestion:** Dragging a PDF or code file onto the 3D pet displays the inspection animation and opens the summary prompt in the composer.
7. **100% Privacy Retained:** Disconnecting the internet allows all voice commands, local inference, PC actions, and dictation to function with zero data loss or errors.
8. **Product-Grade Pet Polish:** The pet exhibits continuous squircle curvature, spherical eye projection, organic saccadic gaze tracking, tactile squash-and-stretch on click/drag, dizzy spinning on rapid pokes, and file-eating particle ingestion—fully replacing primitive circles with a high-end designer toy aesthetic.
9. **Zero Desktop Footprint When Idle:** The pet drops to <0.5% CPU and sleeps during user inactivity, waking instantly upon mouse hover or wake-word detection.
