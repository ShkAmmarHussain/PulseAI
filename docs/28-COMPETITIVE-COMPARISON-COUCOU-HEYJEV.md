# Comprehensive Competitive Analysis: PulseAI (Jarvis) vs. Coucou vs. Hey Jev

**Document Version:** 1.0  
**Date:** October 2026  
**Scope:** Architecture, Capabilities, UX/UI, Voice & Audio, Autonomy, Safety, Performance, and Strategic Recommendations.

---

## 1. Executive Summary

This document provides a deep, technical, and feature-by-feature comparative analysis among three distinct desktop AI assistant paradigms:

1. **PulseAI (Jarvis Desktop Pet)** (`ours`): An **autonomous, 100% local-first desktop companion & agent system**. It pairs a full-featured command center and an expressive, floating 3D WebGL pet with autonomous multi-agent planning, OS control (mouse/keyboard/window/file), local neural voice (openWakeWord + faster-whisper + Kokoro TTS), LM Studio local inference with dynamic VRAM management, and a hardened human-in-the-loop safety gating system.
2. **Coucou (Mochi)** (`Louis-CFM/coucou`): A **developer-focused "dynamic island" and desktop notch companion** designed specifically to observe and supervise external AI coding agents (Claude Code, Cursor, Codex, Gemini CLI, Antigravity). Written natively in Swift 6/SwiftUI for macOS (with a Tauri 2 port for Windows/Linux), it excels at non-intrusive notification, live file diff tickers, one-click terminal permission approvals, file dropping, and SaaS status pills (GitHub, Stripe, Vercel).
3. **Hey Jev** (`henryklunaris/hey-jev`): A **voice-first, sub-second Mac automation assistant & dictation utility** modeled after a modern, private Siri. Written in Python and native macOS AppKit (`pyobjc`), it specializes in low-latency voice command execution (controlling Spotify, opening apps, setting timers via AppleScript) powered by TypeSafe speculative intent classification ($0.00004/call), pre-cached emotional Fish Audio TTS replies, and cursor-injected dictation.

### Core Archetype Summary

| Dimension | PulseAI (Jarvis) | Coucou (Mochi) | Hey Jev |
| :--- | :--- | :--- | :--- |
| **Core Archetype** | Autonomous Multi-Agent Desktop Companion | Coding Agent Supervisor & Dynamic Island | Voice Automation & Fast Dictation Assistant |
| **Primary User** | Power users & general desktop companion users seeking autonomous task execution | Software developers running CLI coding agents (Claude Code, Cursor, etc.) | Mac users wanting quick voice controls, Spotify navigation, and speech-to-text dictation |
| **Autonomy Level** | **High** (Autonomous multi-step planner, tool executor, vision, PC control) | **External** (Does not plan itself; observes and approves external agent actions) | **Low / Deterministic** (Pre-mapped 1-turn or 2-turn command execution via AppleScript) |
| **Cloud Dependency** | **Zero** (100% Local-First: LM Studio, openWakeWord, Kokoro TTS, SQLite/ChromaDB) | **Hybrid** (Local agent hooks, but uses cloud API keys for chat & SaaS integrations) | **High** (Requires TypeSafe API, Fish Audio API, OpenRouter/OpenAI API) |
| **Visual Avatar** | Real-time interactive 3D WebGL chibi robot with procedural moods & physics | Procedural 2D squircle ("Mochi") in the Mac notch/top-bar with sound FX & outfits | Floating AppKit dictation waveform bubble + native macOS settings/stats window |

---

## 2. High-Level Comparison Matrix

| Feature / Dimension | PulseAI (Jarvis) | Coucou (Mochi) | Hey Jev |
| :--- | :--- | :--- | :--- |
| **Primary Platform** | **Windows 10/11** (cross-platform Tauri core) | **macOS 15+** (SwiftUI native), Windows/Linux (Tauri 2) | **macOS only** (Tahoe, Sequoia; relies on AppleScript & PyObjC) |
| **Frontend Stack** | Tauri (Rust) + HTML5 + Vanilla JS + Three.js WebGL | **Mac:** Swift 6 + SwiftUI + AppKit<br>**Win/Linux:** Tauri 2 + TS + Canvas 2D | Python + `pyobjc-framework-Cocoa` (AppKit native UI) |
| **Backend Stack** | Python (asyncio Event Bus, PyInstaller bundle, WebSocket bridge) | **Mac:** Pure Swift daemon + Unix Domain Socket<br>**Win:** Rust named pipes (`coucou-hook.exe`) | Python 3 + `py2app` bundle + AppleScript (`osascript`) |
| **Visual Presentation** | **Dual Surface:**<br>1. Always-on-top transparent 3D living pet (300×240)<br>2. Full 1100×760 command center | **Notch / Island:**<br>1. Retractable top-edge notch island<br>2. Detachable 120pt desktop squircle | **AppKit Window + Bubble:**<br>1. 900×600 Translucent native window<br>2. Floating audio waveform bubble |
| **Avatar Expressiveness** | 3D procedural animations (breathing, eye tracking, orbital particles, antenna pulse, bounce, speech sync) | 2D Canvas squircle with eye projection on sphere, squish physics, dizzy emotes, 28 audio sound FX | No avatar; animated audio waveform bubble during active speech/dictation |
| **LLM Inference** | **Local LM Studio** (OpenAI-compatible HTTP/SSE API with role-based models) | **Cloud APIs** (Anthropic Claude, OpenAI, Google Gemini) + optional local Ollama/LM Studio | **Cloud APIs** (Claude Haiku via OpenRouter for Q&A, TypeSafe for intent classification) |
| **Inference Cost** | **$0.00 / Free** (Runs on local hardware) | User's own API keys (Anthropic / OpenAI / Google) | Pay-per-call (~$0.00004 for TypeSafe, ~$0.0002 for Claude Haiku) |
| **Wake-Word Engine** | **Local openWakeWord** (ONNX model, live threshold tuning, score meter) | **None** (Not a voice assistant) | **Continuous Whisper** listening or Push-to-Talk (Right Option key) |
| **Speech-to-Text (STT)** | Local Whisper with Silero VAD, auto-gain control (AGC), and noise gate | None | Local `faster-whisper` (`small.en`) + Cloud `gpt-4o-mini-transcribe` for dictation |
| **Text-to-Speech (TTS)** | Local neural **Kokoro-82M** (multiple voices, speed slider) + Windows SAPI | None (uses 28 short pre-recorded UI sound effects / audio chimes) | Cloud **Fish Audio S2.1 Pro** with emotion tags (`[chuckling]`, `[sighing]`) + pre-cached audio |
| **Dictation to Cursor** | In chat composer only | None | **System-wide dictation:** talks into any active window/input, auto-pastes at cursor |
| **PC Automation** | Arbitrary GUI automation, PyAutoGUI, mouse/keyboard, window focus, file discovery | None (delegates all work to Claude Code or external coding agents) | Hardcoded AppleScript triggers for apps (Spotify, Slack, Brave, volume, dark mode, sleep) |
| **Safety & Human-in-the-Loop** | **Comprehensive:** Risk rating (1–10), Allow once / Deny cards, correlation IDs, auto-timeout, Conservative vs. Smart modes | **Agent-Relayed:** Intercepts Claude Code hook permission prompts (Allow / Deny / Always allow tool) | **System-level only:** Standard macOS privacy prompts (Accessibility, Automation, Mic) |
| **Multi-Agent Orchestration** | **Yes:** Orchestrator, Planner, Tool Control, Vision, Memory Agents on event bus | **No:** Pure hook receiver and UI event forwarder | **No:** Speculative classification fan-out with single LLM fallback |
| **Memory & Context** | Persistent SQLite / ChromaDB vector recall for conversation & tool history | None (stateless observer; relies on Claude Code session context) | JSON logs (`~/Library/Logs/Hey Jev dictation.jsonl`) + local dictionary replacement map |
| **Hardware Management** | **Active VRAM Manager:** loads models on demand, unloads after idle timeout (60s), cooldown control | **Passive:** Minimal footprint (~a few MBs RAM, idle state machine) | **Passive:** Keeps Whisper in memory (~250MB), delegates inference to cloud APIs |
| **SaaS / Dev Integrations** | Local filesystem, apps, browser routines | GitHub PRs/CI, Stripe, Vercel, Resend, Notion, Cal.com, Apple Music | Spotify (desktop API via AppleScript) |

---

## 3. Deep Dive: PulseAI (Jarvis Desktop Pet)

### Overview
PulseAI is built as a self-contained, sovereign AI companion. It blends the emotional presence of an expressive desktop pet with an industrial-grade multi-agent autonomous execution pipeline.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PulseAI Architecture                          │
├──────────────────────────────────┬─────────────────────────────────────┤
│  Tauri UI (Dual Surface)         │  Local Python Event Bus Core        │
│  • 3D WebGL Pet (Three.js)       │  • OpenWakeWord ONNX Engine         │
│  • 1100x760 Command Dashboard    │  • faster-whisper + Silero VAD      │
│  • Approval Cards & Settings     │  • Kokoro-82M Neural TTS Engine     │
│  • WebSocket Client Bridge       │  • LM Studio Model Lifecycle Mgr    │
│                                  │  • Orchestrator / Planner / Tool    │
│                                  │  • Safety Guardrails & Risk Rater   │
│                                  │  • SQLite / ChromaDB Memory Store   │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### Key Strengths & Differentiators

1. **Complete Privacy & Local Sovereignty (Zero Cloud Reliance):**
   - All components—wake-word detection (`openWakeWord`), speech recognition (`faster-whisper`), LLM reasoning (`LM Studio`), speech synthesis (`Kokoro-82M`), and memory storage (`SQLite`/`ChromaDB`)—run locally on the user's workstation.
   - No sensitive desktop activity, voice recordings, or file contents are ever transmitted to third-party cloud APIs.
   - Zero recurring subscription costs or API usage fees.

2. **Autonomous Multi-Agent PC Control:**
   - Possesses a full agentic loop: query understanding $\rightarrow$ plan decomposition $\rightarrow$ tool execution $\rightarrow$ visual verification $\rightarrow$ synthesis.
   - Can interact with native desktop windows, launch apps, search files, capture screenshots, and perform compound operations across the OS.

3. **Hardened Human-in-the-Loop (HITL) Safety:**
   - Pre-execution risk assessment (risk score 1–10).
   - High-contrast approval cards with plain-language action descriptions and explicit "Allow once" / "Deny" choices.
   - Correlation-ID binding ensures that answering in either the 3D pet bubble or the main chat window synchronizes state and prevents double execution.
   - Server-side timeouts automatically cancel expired prompts, treating inaction as a denial.

4. **Dynamic VRAM Lifecycle Management:**
   - Automatically loads large language models into LM Studio only when a task demands them and idle-unloads them after a configured period (e.g., 60 seconds).
   - Prevents GPU memory exhaustion, enabling high-quality LLMs to coexist smoothly with gaming, video editing, or other heavy desktop workflows.

5. **Rich 3D Companion Avatar:**
   - Procedural 3D WebGL robot character (Three.js) capable of real-time emotional state reflection (idle, listening, thinking, speaking, happy, concerned).
   - Features procedural eye tracking, blinking, antenna pulsing, floating light rings, and orbital energy particles.

---

## 4. Deep Dive: Coucou (Mochi)

### Overview
Coucou is a lightweight, developer-focused desktop utility. Rather than building its own autonomous agent, it acts as a companion and supervisor for *existing* CLI coding tools such as Claude Code, Cursor, Codex, Gemini CLI, and Antigravity.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Coucou Architecture                           │
├──────────────────────────────────┬─────────────────────────────────────┤
│  Notch / Dynamic Island UI       │  Relay & Hook Infrastructure        │
│  • Swift 6 / SwiftUI (macOS)     │  • Unix Domain Socket / Named Pipes │
│  • Tauri 2 / Canvas 2D (Win/Lin) │  • `coucou-hook.exe` CLI Bridge     │
│  • Mochi 2D Avatar + 28 Audio FX │  • Intercepts Claude Code events    │
│  • SaaS Integration Pills        │  • Live Diff Parser (+N, -M)        │
│  • File Drop Target              │  • OS Keychain / Credential Manager │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### Key Strengths & Differentiators

1. **Non-Intrusive "Dynamic Island" Form Factor:**
   - Capitalizes on the MacBook display notch (or the top screen edge on Windows/Linux).
   - Remains completely invisible or compact until needed, expanding seamlessly when an agent requires approval or when the user hovers.

2. **Native Developer Workflow Integration:**
   - Specifically built for Claude Code and coding CLI sessions.
   - Shows live file edits with diff counts (`+12, -4`), lets developers inspect unified diffs directly inside the island, and offers a single click to jump straight to the relevant terminal window.
   - Non-blocking design: if Coucou is closed or delayed, the hook relay exits in 300ms, seamlessly falling back to the terminal.

3. **Charming Micro-Interactions & Audio Design:**
   - 28 handcrafted sound effects (squishes, chirps, greetings, notifications).
   - Interactive physics: poking Mochi causes squishing and annoyed expressions; rapid clicking induces dizziness; hovering displays hearts.
   - Wardrobe system with seasonal outfits and right-click customizations.

4. **Unified SaaS Notification Hub:**
   - Integration pills for developer infrastructure: Stripe payment alerts, GitHub PRs/reviews/CI statuses, Vercel deployments, Resend emails, Notion, and Cal.com.

5. **Native Apple Silicon Engineering:**
   - macOS version is written in pure Swift 6 and SwiftUI with **zero third-party dependencies**, utilizing minimal CPU/RAM and delivering fluid 60 FPS Canvas animations.

---

## 5. Deep Dive: Hey Jev

### Overview
Hey Jev is an opinionated voice-first Mac automation assistant designed to replace Siri for desktop productivity. It bridges local speech recognition with high-speed cloud classification to achieve sub-second execution times for everyday commands.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Hey Jev Architecture                          │
├──────────────────────────────────┬─────────────────────────────────────┤
│  Native macOS AppKit UI          │  Hybrid Voice & Intent Pipeline     │
│  • PyObjC Translucent Window     │  • Local `faster-whisper` (small.en)│
│  • Floating Waveform Bubble      │  • Push-to-Talk (Right Option Key)  │
│  • Apps & Vocabulary Config      │  • TypeSafe Speculative Intent API  │
│  • Dictation History Log         │  • Pre-rendered Fish Audio TTS Cache│
│                                  │  • Cloud `gpt-4o-mini-transcribe`   │
│                                  │  • AppleScript OS Automation        │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### Key Strengths & Differentiators

1. **Sub-Second Voice Command Latency:**
   - Achieves near-instant vocal responses through an ingenious **pre-rendered TTS audio cache**: common scripted responses are pre-synthesized into `cache/tts/` on first run, eliminating synthesis latency during daily interactions.
   - Only dynamic LLM answers require live network synthesis.

2. **Speculative Intent Classification (TypeSafe):**
   - Avoids spinning up a heavy LLM prompt for every simple voice command.
   - Uses TypeSafe's fan-out classification pattern to evaluate intent category, compound actions, target apps, and parameters in a single micro-call costing just ~$0.00004.
   - Can parse compound commands in a single phrase (e.g., *"Pause Spotify and open Slack"*).

3. **System-Wide Dictation with Custom Phonetic Dictionary:**
   - Say *"Hey Jev, transcribe"*, talk naturally, say *"stop transcribing"*, and the transcribed text is typed directly into whatever input field or window currently has cursor focus.
   - Includes a **Custom Dictionary** (`vocabulary.json`) allowing users to map misheard words (e.g., technical jargon, unusual names) directly to their intended spellings.

4. **Expressive Emotional TTS:**
   - Uses Fish Audio S2.1 Pro with contextual emotion markup tags (e.g., `[chuckling]`, `[sighing]`, `[curious]`), making spoken responses sound dynamic and lifelike.

5. **Native macOS Desktop Control via AppleScript:**
   - Direct automation for system volume, display dark mode, computer sleep/lock, timers, reminders, and third-party media players (Spotify desktop play/pause/track/volume).

---

## 6. Detailed Pros & Cons Matrix

### PulseAI (Jarvis Desktop Pet)

#### Pros
- **100% Local & Sovereign:** Complete data privacy, zero API bills, immune to cloud outages.
- **Deep Agentic Autonomy:** Genuine multi-step planner, visual feedback, tool use, and PC control.
- **Superior HITL Safety Architecture:** Full risk scoring, dual-surface synchronized approval cards, correlation ID safety, and automatic denial on timeouts.
- **True 3D Interactive Character:** Immersive WebGL pet with real-time procedural mood transitions, antenna light blooms, and physics-based eye tracking.
- **Hardware-Conscious:** Active LM Studio lifecycle manager dynamically offloads models to keep consumer VRAM free.
- **Unified Dual-Surface Interface:** Seamlessly toggles between an unobtrusive desktop companion and a full command center.

#### Cons
- **Heavy Local Hardware Requirements:** Requires a modern GPU (RTX 3060/4060+ recommended) to run local Whisper, Kokoro, and 7B–14B LLMs concurrently.
- **No System-Wide Dictation Injection:** Voice input is currently tied to the Jarvis composer rather than typing into arbitrary active windows.
- **No External Coding Agent Hooks:** Does not yet intercept or visualize Claude Code or Cursor sessions.
- **Setup & Cold-Start Complexity:** Initial setup requires downloading multi-gigabyte models and running LM Studio in the background.

---

### Coucou (Mochi)

#### Pros
- **Exceptional Developer Ergonomics:** Seamlessly fits into terminal workflows with Claude Code, Cursor, and Codex.
- **Zero-Footprint Notch Design:** Takes advantage of screen bezels; unobtrusive until attention is required.
- **Live File Diff Visualization:** Shows file modifications and `+N, -M` counts in the status ticker with full diff previews.
- **Delightful Audio & Physics Polish:** 28 expressive sound effects, squish interactions, and seasonal outfits give Mochi personality.
- **Extremely Lightweight:** Native Swift codebase uses negligible CPU/RAM and requires no local AI models.

#### Cons
- **Not an Autonomous Assistant:** Cannot perform PC actions, plan tasks, or execute shell commands on its own; it is strictly an event listener and relay.
- **No Voice Pipeline:** Completely lacks voice recognition, wake words, and speech synthesis.
- **Cloud API Cost Accumulation:** Relies on external API keys (Anthropic, OpenAI, Google) for general chat queries.
- **macOS-First Bias:** Windows and Linux ports rely on Tauri 2 and lack some Mac-native features (e.g., Apple Music pill, window drag-to-context, seamless notch integration).

---

### Hey Jev

#### Pros
- **Blazing Fast Voice Responses:** Pre-rendered TTS audio cache provides sub-100ms spoken feedback for frequent commands.
- **Hands-Free Desktop Automation:** Voice-controls Spotify, apps, timers, volume, and dark mode without touching the mouse.
- **Cursor-Injected Dictation Mode:** Transcribes speech and injects it straight into active text fields across macOS.
- **Phonetic Replacement Dictionary:** User-editable vocabulary fixes persistent speech-to-text recognition errors.
- **Emotional Spoken Inflections:** Fish Audio emotion markup (`[chuckling]`, `[sighing]`) creates expressive spoken audio.

#### Cons
- **Strictly Mac-Only:** Completely dependent on AppleScript (`osascript`) and AppKit; cannot run on Windows or Linux.
- **Multi-Cloud API Dependency:** Relies on three separate commercial API services (TypeSafe, Fish Audio, OpenRouter/OpenAI); ceases to function offline.
- **Limited Automation Scope:** Hardcoded command grammar; cannot execute multi-step arbitrary plans, inspect the screen, or browse the web.
- **No Visual Pet/Avatar:** Lacks visual character or embodied presence; only provides an audio waveform bubble.
- **No Safety Gating:** Executes system commands immediately upon voice transcription without an approval card step.

---

## 7. Actionable Inspiration & Opportunities for PulseAI (Jarvis)

By analyzing Coucou and Hey Jev, several high-value features emerge that could elevate PulseAI into the undisputed leader in desktop AI companions:

### 1. Adopt Coucou's Coding Agent Hook Relay (`jarvis-hook`)
- **Opportunity:** Add a local hook listener (similar to `coucou-hook.exe`) to PulseAI's WebSocket bridge.
- **Value:** When users run Claude Code, Cursor, or Antigravity in the terminal, Jarvis's floating 3D pet can automatically react, show live file diff counts, and present the approval prompt directly in the pet's speech bubble.

### 2. Implement Hey Jev's Pre-Rendered TTS Audio Cache
- **Opportunity:** Pre-generate Kokoro audio clips for standard assistant acknowledgments (*"Working on it"*, *"Done"*, *"Action denied"*, *"Listening"*, *"I'm thinking"*) and store them in a local `.cache/tts/` folder.
- **Value:** Drops conversational acknowledgment latency to **under 50ms**, eliminating neural synthesis delay for repetitive system confirmations.

### 3. Add Global "Dictate to Cursor" Capability (from Hey Jev)
- **Opportunity:** Expand the existing push-to-talk hotkey (`Ctrl+Alt+J`) with a secondary shortcut (e.g., `Ctrl+Alt+D`) that transcribes continuous speech via local Whisper and automatically pastes or types the text at the active OS cursor position.
- **Value:** Transforms Jarvis from an isolated chat companion into an indispensable daily productivity tool for writing emails, code comments, and documents.

### 4. Implement a Phonetic Vocabulary Replacement Dictionary (from Hey Jev)
- **Opportunity:** Add a `vocabulary.json` configuration tab in Jarvis Settings allowing users to map misrecognized words (e.g., project names, developer handles) to their correct spellings.
- **Value:** Greatly improves local Whisper accuracy for technical and domain-specific terminology without fine-tuning models.

### 5. Drag-and-Drop File Ingestion onto the 3D Pet (from Coucou)
- **Opportunity:** Enable drag-and-drop file detection over the transparent 3D pet window. When a user drags a file (PDF, code, image) onto the pet, the pet enters an "eating/inspecting" animation and populates the chat composer with the file context.
- **Value:** Creates an intuitive, physical interaction model for desktop file summarization and vision tasks.

### 6. Introduce Handcrafted Audio Sound Effects (from Coucou)
- **Opportunity:** Pair the 3D pet's visual state transitions with subtle, high-quality audio cues (soft chimes on wake, subtle hum on listening, gentle pop on completion, warning chime on high-risk approval).
- **Value:** Enhances multimodal awareness even when the user is looking at another monitor.

---

## 8. Conclusion

- **PulseAI (Jarvis)** holds the decisive advantage in **autonomy, privacy, and full-stack local execution**. It is the only platform among the three capable of autonomous PC control, visual screenshot inspection, dynamic VRAM resource management, and multi-agent problem solving while keeping 100% of data on-premise.
- **Coucou** demonstrates how a companion can achieve viral developer adoption through **laser focus on workflow ergonomics**: non-intrusive notch anchoring, instant Claude Code permission interception, and delightful micro-interactions.
- **Hey Jev** proves the power of **frictionless voice UX**: by pre-rendering common TTS replies and offering cursor-level dictation with phonetic error correction, it achieves a snappy, human-like voice interaction cadence that traditional agent architectures often overlook.

By synthesizing Coucou's developer workflow hooks and Hey Jev's ultra-low-latency voice caching and dictation injection into PulseAI's local autonomous foundation, Jarvis can offer an unmatched desktop assistant experience across both Windows and cross-platform environments.
