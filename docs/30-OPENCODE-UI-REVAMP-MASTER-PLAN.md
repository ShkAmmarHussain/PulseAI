# 30. OPENCODE MASTER PLAN: COZY PRODUCT-GRADE UI & DESKTOP PET REVAMP

**Document:** `docs/30-OPENCODE-UI-REVAMP-MASTER-PLAN.md`  
**Target Agent:** `opencode` / `Claude Code`  
**Purpose:** Actionable, file-by-file master specification and implementation blueprint to completely overhaul the Jarvis Desktop Pet and Main Workspace into a warm, cozy, world-class desktop companion that matches and exceeds the design standards of **Coucou (Mochi)** and **Hey Jev**.  
**Parent Documentation:** [27-UI-REVAMP.md](file:///d:/Personal_projects/2/Personal_AI/docs/27-UI-REVAMP.md), [28-COMPETITIVE-COMPARISON-COUCOU-HEYJEV.md](file:///d:/Personal_projects/2/Personal_AI/docs/28-COMPETITIVE-COMPARISON-COUCOU-HEYJEV.md), [29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md](file:///d:/Personal_projects/2/Personal_AI/docs/29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md)

---

## 1. Executive Visual Audit & Root Cause Analysis

### 1.1 The User's Direct Feedback
> *"After implementing the 29 doc. Have a look does this look like a product ready version to you? there are so many visual things missing here. even notification when appear hides the pet, its cropped, why are there button below and a bar above they should appear when to tell something and then disapper, also I don't see the edge dock thing. Look at the app too, I wanna make it better looking too, refined version also the sidebar when clicked closes, but can't be opened again. Look at coucou and jev's UI its so much better."*
>
> *"Did you also add to review the whole UI visually too? I mean to take screenshots of things analyze them and find faults in them in the md so claude code can see what it's making too? Also did you not only mention the faults but also told it make the UI and pet better looking? It should give a cozy vibe, not a sci-fi like it's doing right now."*

### 1.2 The Two Primary Flaws Diagnosed

```
┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
│         1. AESTHETIC / VIBE MISMATCH         │  │           2. TECHNICAL / UX CRIPPLING        │
├──────────────────────────────────────────────┤  ├──────────────────────────────────────────────┤
│ Current: Cold, aggressive, dark sci-fi /     │  │ Current: Severe cropping, pet head sliced,   │
│ cybernetic robot with glowing neon and HUD   │  │ permanent 2010-era buttons stealing space,   │
│ bars that look like a gaming terminal.       │  │ speech bubbles covering the pet's face, and  │
│                                              │  │ sidebar collapse button that deletes itself! │
│ TARGET: Warm, delightful, cozy designer pet  │  │                                              │
│ (like Mochi, Animal Crossing, Ghibli tech)   │  │ TARGET: Frameless living pet, auto-hiding    │
│ with soft squishy textures, warm lighting,   │  │ micro-dock on hover, floating bubbles ABOVE  │
│ gentle peach blush, and cozy desktop warmth! │  │ head, working dynamic island, and fixed UI.  │
└──────────────────────────────────────────────┘  └──────────────────────────────────────────────┘
```

---

## 2. Aesthetic Paradigm Shift: From "Cold Sci-Fi" to "Warm, Cozy Companion"

The app currently feels like an intimidating cybernetic terminal. Coucou's Mochi succeeded because it feels like a **lovable desktop desk buddy** sitting next to your coffee mug while you work. Jarvis must embrace this **warm, cozy, peaceful aesthetic**:

```
                  ┌───────────────────────────────┬───────────────────────────────┐
                  │ OLD (COLD SCI-FI - AVOID)     │ NEW (COZY COMPANION - BUILD)  │
├─────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Pet Palette     │ Harsh electric cyan, pitch    │ Warm ivory/porcelain cream,   │
│                 │ black, cold chrome metal      │ soft peach blush, warm amber  │
├─────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Pet Material    │ Reflective hard plastic glass │ Soft matte silicone/ceramic,  │
│                 │ with sharp specular points    │ warm subsurface scattering    │
├─────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Lighting        │ Cold blue neon spotlights     │ Warm diffuse desk-lamp glow,  │
│                 │ and glowing sci-fi lasers     │ gentle warm rim-lighting      │
├─────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Face & Eyes     │ Hard cybernetic LED screen    │ Expressive rounded dark eyes, │
│                 │ with rigid neon smile         │ warm curvature, happy blinks  │
├─────────────────┼───────────────────────────────┼───────────────────────────────┤
│ App Foundation  │ Pure black stark background,  │ Warm dark charcoal (#16171B), │
│                 │ sharp borders, cold purple    │ velvety depth, linen text     │
├─────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Micro-Copy      │ "SAFETY GATE ARMED",          │ "Need a hand?", "All set!",   │
│                 │ "LOCAL SERVICE RUNNING"       │ "Standing by with you"        │
├─────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Sound Design    │ High-pitched electronic beeps │ Soft woodblock taps, bubbles, │
│                 │ and robotic hums              │ acoustic chimes, gentle purr  │
└─────────────────┴───────────────────────────────┴───────────────────────────────┘
```

---

## 3. Mandatory Visual Self-Review Protocol for `opencode` / `Claude Code`

> **CRITICAL DIRECTIVE FOR THE AGENT EXECUTING THIS SPEC:**  
> **You MUST NOT blindly write code without visually seeing the result.**  
> You must run the development environment, trigger window captures, visually inspect the screenshots with multimodal vision, critique the alignment, margins, cropping, and warmth, and iterate until the UI is flawless.

### 3.1 The Automated Screenshot Inspection Workflow
1. **Launch the Environment:**
   Run the dev server: `cd ui_pet && npm run dev` or run Tauri in dev mode.
2. **Execute Visual Inspection Script:**
   A dedicated PowerShell helper `scripts/inspect_ui.ps1` captures snapshots of all windows:
   - `pet_idle.png`: Floating pet at rest (verify zero clipping, soft warm glow, no top/bottom chrome).
   - `pet_hover.png`: Mouse hovered over pet (verify contextual micro-dock fades in smoothly).
   - `pet_speech.png`: Pet speaking (verify bubble floats strictly *above* the pet's head, face is 100% visible).
   - `pet_approval.png`: Approval request (verify warm amber card anchored above, clean buttons).
   - `dock_collapsed.png`: Dynamic island resting at top edge of screen.
   - `dock_expanded.png`: Dynamic island expanded on hover with live diffs.
   - `main_app_expanded.png`: Main workspace with full sidebar.
   - `main_app_collapsed.png`: Main workspace with collapsed icon rail (verify collapse button is visible!).
3. **Multimodal Visual Analysis:**
   The agent reads the captured images into context and runs the **Cozy Visual Checklist**:
   - [ ] Is any part of the pet's head, ears, antenna, or feet cut off? (Must have $\ge 20\%$ margin).
   - [ ] Does the pet look soft, adorable, and cozy, or does it look like a harsh sci-fi robot?
   - [ ] Are the speech bubbles floating above the head without overlapping eyes or cheeks?
   - [ ] Are the clunky permanent `#pet-head` bar and bottom buttons completely gone?
   - [ ] Is the sidebar toggle button clearly visible and functional when collapsed?
   - [ ] Do terminal coding diffs look like polished Coucou cards (`+14 -3`) rather than plain italic text?

---

## 4. Component 1: The Cozy Desktop Pet Overhaul (`pet.html`, `pet.js`, `pet3d.js`, `app.css`)

### 4.1 Window Bounds (`tauri.conf.json`)
The rigid `300x240` window was the primary cause of pet decapitation. Update `ui_pet/src-tauri/tauri.conf.json`:
```json
{
  "label": "pet",
  "title": "Jarvis Pet",
  "url": "pet.html",
  "width": 360,
  "height": 360,
  "resizable": false,
  "decorations": false,
  "transparent": true,
  "alwaysOnTop": true,
  "skipTaskbar": true,
  "visible": true
}
```

### 4.2 Frameless Template (`pet.html`)
Completely eliminate the permanent header `#pet-head` and the bottom `#mini-btns`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Jarvis Pet</title>
  <link rel="stylesheet" href="app.css" />
  <style>
    html, body {
      background: transparent !important;
      overflow: hidden !important;
      margin: 0; padding: 0;
      width: 100vw; height: 100vh;
      user-select: none;
    }
  </style>
</head>
<body class="pet-transparent-surface">
  <div id="pet-container" data-tauri-drag-region>
    
    <!-- 1. Floating Speech Bubble (Positioned strictly ABOVE pet head with clearance) -->
    <div id="pet-bubble-anchor">
      <div id="bubble" class="floating-bubble" role="status" aria-live="polite">
        <span class="bubble-tail"></span>
        <div class="bubble-content" id="bubble-text"></div>
      </div>
    </div>

    <!-- 2. Human-in-the-Loop Approval Modal (Positioned strictly ABOVE pet head) -->
    <div id="approval-anchor">
      <div id="approval" class="floating-approval-card" role="alertdialog">
        <div class="approval-header">
          <span class="approval-badge">Safety Confirmation</span>
          <span class="approval-timer" id="approval-countdown">30s</span>
        </div>
        <div class="approval-body" id="approval-msg"></div>
        <div class="approval-actions">
          <button class="btn-allow" id="pet-allow-btn">Allow once</button>
          <button class="btn-deny" id="pet-deny-btn">Deny</button>
        </div>
      </div>
    </div>

    <!-- 3. The 3D Living Character Stage -->
    <div id="pet-stage">
      <div id="pet" data-mood="idle"></div>
      <div class="pet-floor-glow" aria-hidden="true"></div>
    </div>

    <!-- 4. Contextual Floating Micro-Dock (AUTO-HIDING: Appears ONLY on hover) -->
    <div id="pet-hover-dock" class="context-dock" aria-label="Quick Actions">
      <button class="dock-action-btn" id="dock-btn-mic" title="Talk to Jarvis (Push-to-Talk)">
        <svg class="ic"><use href="#i-mic"/></svg>
      </button>
      <button class="dock-action-btn" id="dock-btn-chat" title="Open Command Center">
        <svg class="ic"><use href="#i-chat"/></svg>
      </button>
      <button class="dock-action-btn" id="dock-btn-dockmode" title="Switch to Top-Edge Dynamic Island">
        <svg class="ic"><use href="#i-dock"/></svg>
      </button>
      <button class="dock-action-btn" id="dock-btn-settings" title="Settings">
        <svg class="ic"><use href="#i-sliders"/></svg>
      </button>
    </div>

  </div>

  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <symbol id="i-chat" viewBox="0 0 24 24"><path d="M21 12c0 4-4 7-9 7-1.2 0-2.3-.2-3.3-.5L4 20l1.2-3.3C4.4 15.4 4 13.7 4 12c0-4 4-7 9-7s8 3 8 7z"/></symbol>
      <symbol id="i-sliders" viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2.2"/><circle cx="10" cy="17" r="2.2"/></symbol>
      <symbol id="i-mic" viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></symbol>
      <symbol id="i-dock" viewBox="0 0 24 24"><path d="M4 4h16M4 20h16M12 9l-4 4h8l-4-4z"/></symbol>
    </defs>
  </svg>

  <script src="ws.js"></script>
  <script src="pet.js"></script>
  <script type="module" src="pet3d.js"></script>
</body>
</html>
```

### 4.3 Cozy Pet 3D Shaders & Materials (`pet3d.js`)
Transform the 3D model from a cold metallic robot into a warm, cuddly, ceramic/mochi designer toy:

```javascript
// Warm Diffuse Desk-Lamp Lighting
scene.add(new THREE.HemisphereLight(0xfff6ea, 0x241d28, 1.2)); // Warm cream to soft violet ambient

// Warm Key Light (Soft Tungsten Glow)
const warmKey = new THREE.DirectionalLight(0xffeedd, 1.8);
warmKey.position.set(2.5, 4.0, 4.5);
scene.add(warmKey);

// Warm Amber/Peach Rim Light
const warmRim = new THREE.PointLight(0xffb07c, 18, 12);
warmRim.position.set(-3.2, -1.0, 2.5);
scene.add(warmRim);

// Cozy Soft Matte Ceramic Material with Subsurface Scattering Feel
const bodyMat = new THREE.MeshPhysicalMaterial({
  color: 0xfcf9f2,          // Warm creamy ivory/porcelain
  roughness: 0.38,          // Soft matte touch (not glossy plastic!)
  metalness: 0.04,          // Non-metallic, organic toy feel
  transmission: 0.08,       // Subtle translucency
  ior: 1.45,
  sheen: 1.0,
  sheenRoughness: 0.5,
  sheenColor: 0xffdfd0,     // Soft peach velvet sheen
  clearcoat: 0.12,
  clearcoatRoughness: 0.4
});

// Soft Rounded Peach Blush Cheeks
const blushMat = new THREE.MeshBasicMaterial({
  color: 0xfca5a5,
  transparent: true,
  opacity: 0.65
});
```

### 4.4 Camera Framing Fix in `pet3d.js`
Ensure at least 25% empty clearance around the character so the antenna and feet never collide with window edges:
```javascript
const camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 100);
camera.position.set(0, 0.08, 5.8);
camera.lookAt(0, -0.05, 0);
```

---

## 5. Component 2: Dedicated Retractable Top-Edge Dock ("Dynamic Island")

### 5.1 The Root Cause of Missing Dock
The previous implementation tried to open `index.html?mode=dock` in a `220x38` window, crashing the layout.

### 5.2 Standalone `dock.html`
Create a clean, dedicated `ui_pet/src/dock.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Jarvis Dynamic Island</title>
  <link rel="stylesheet" href="app.css" />
  <style>
    html, body {
      background: transparent !important;
      margin: 0; padding: 0;
      overflow: hidden !important;
      width: 100vw; height: 100vh;
      user-select: none;
    }
  </style>
</head>
<body class="dock-window-body">
  <div id="dynamic-island" class="island-collapsed" data-state="idle">
    
    <!-- Collapsed Rail (Always Visible Flush to Top Screen Edge) -->
    <div class="island-rail" data-tauri-drag-region>
      <div class="island-avatar-pill">
        <span class="island-eye left"></span>
        <span class="island-eye right"></span>
      </div>
      <span class="island-status-dot" id="island-dot"></span>
      <span class="island-headline" id="island-headline">Jarvis Standing By</span>
      <span class="island-diff-badge" id="island-diff" hidden>+0 -0</span>
    </div>

    <!-- Expanded Drawer (Smoothly slides down on hover) -->
    <div class="island-drawer">
      <div class="drawer-task-info">
        <span class="drawer-task-title" id="island-subtext">Ready for instructions</span>
        <div class="drawer-progress-track">
          <div class="drawer-progress-fill" id="island-progress"></div>
        </div>
      </div>
      <div class="drawer-controls">
        <button class="drawer-btn" id="island-mic-btn" title="Push-to-Talk">
          <svg class="ic"><use href="#i-mic"/></svg>
        </button>
        <button class="drawer-btn" id="island-chat-btn" title="Open Workspace">
          <svg class="ic"><use href="#i-chat"/></svg>
        </button>
        <button class="drawer-btn" id="island-pet-btn" title="Switch to Floating Pet Mode">
          <svg class="ic"><use href="#i-face"/></svg>
        </button>
      </div>
    </div>

    <!-- Drag-and-Drop Ingestion Overlay -->
    <div class="island-drop-overlay" id="island-dropzone" hidden>
      <span>Drop file to inspect...</span>
    </div>

  </div>

  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <symbol id="i-mic" viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></symbol>
      <symbol id="i-chat" viewBox="0 0 24 24"><path d="M21 12c0 4-4 7-9 7-1.2 0-2.3-.2-3.3-.5L4 20l1.2-3.3C4.4 15.4 4 13.7 4 12c0-4 4-7 9-7s8 3 8 7z"/></symbol>
      <symbol id="i-face" viewBox="0 0 24 24"><rect x="4" y="6" width="16" height="13" rx="5"/><circle cx="9.4" cy="12" r="1.5" fill="currentColor"/><circle cx="14.6" cy="12" r="1.5" fill="currentColor"/></symbol>
    </defs>
  </svg>

  <script src="ws.js"></script>
  <script src="dock_standalone.js"></script>
</body>
</html>
```

### 5.3 Rust Tauri Command (`main.rs`)
In `ui_pet/src-tauri/src/main.rs`, update `set_companion`:
```rust
#[tauri::command]
fn set_companion(app: tauri::AppHandle, mode: String) {
    if mode == "dock" {
        if let Some(pet) = app.get_window("pet") {
            let _ = pet.hide();
        }
        if let Some(dock) = app.get_window("dock") {
            let _ = dock.show();
        } else {
            let built = WindowBuilder::new(
                &app,
                "dock",
                WindowUrl::App("dock.html".into()),
            )
            .title("Jarvis Dynamic Island")
            .inner_size(240.0, 36.0)
            .resizable(false)
            .decorations(false)
            .transparent(true)
            .always_on_top(true)
            .skip_taskbar(true)
            .build();
            if let Ok(w) = built {
                position_dock(&w);
                let _ = w.show();
            }
        }
    } else {
        if let Some(dock) = app.get_window("dock") {
            let _ = dock.hide();
        }
        if let Some(pet) = app.get_window("pet") {
            let _ = pet.show();
        }
    }
}
```

---

## 6. Component 3: Main Desktop Workspace Polish & Bug Fixes

### 6.1 Fix the Sidebar Trap
In `ui_pet/src/app.css`, **delete the self-destructing rule**:
```css
/* DELETE THIS LINE: */
#app.sb-collapsed #sb-toggle { display: none; }
```
Add the proper collapsed icon-rail behavior:
```css
#app.sb-collapsed #sidebar {
  width: 68px !important;
}
#app.sb-collapsed #sb-toggle {
  display: flex !important;
  margin: 0 auto !important;
  transform: rotate(180deg);
}
#app.sb-collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
}
#app.sb-collapsed .nav-item .ic {
  width: 20px;
  height: 20px;
}
#app.sb-collapsed .brand {
  justify-content: center;
  padding: 14px 0;
}
#app.sb-collapsed .brand-text,
#app.sb-collapsed .nav-label,
#app.sb-collapsed .pet-mini-label,
#app.sb-collapsed .sidebar-foot .switch {
  display: none !important;
}
```

### 6.2 Cozy Workspace Palette & Typography
Update CSS root variables in `ui_pet/src/app.css` to introduce the warm, cozy theme:
```css
:root {
  /* Warm Dark Foundation */
  --bg-app: #15161a;
  --bg-sidebar: #1a1b20;
  --bg-card: #202228;
  --bg-elevated: #282a32;
  --bg-hover: rgba(255, 245, 235, 0.06);

  /* Cozy Warm Accents */
  --accent-warm: #f59e0b;           /* Warm honey amber */
  --accent-soft: rgba(245, 158, 11, 0.15);
  --accent-peach: #fb923c;          /* Soft terracotta */
  --accent-lavender: #a78bfa;       /* Gentle lavender */

  /* Text Hierarchy */
  --text-primary: #f7f5f0;          /* Warm linen white */
  --text-secondary: #a3a099;        /* Warm muted stone */
  --text-tertiary: #6b6861;

  /* Borders & Shadows */
  --border-subtle: rgba(255, 245, 235, 0.07);
  --border-strong: rgba(255, 245, 235, 0.14);
  --radius-lg: 16px;
  --radius-md: 12px;
  --radius-sm: 8px;
}
```

### 6.3 Coucou-Grade Terminal Coding Agent Diff Cards
In `ui_pet/src/chat.js`, replace raw italic logs with rich interactive cards:
```javascript
function renderAgentDiffCard(data) {
  const card = document.createElement("div");
  card.className = "agent-diff-card";
  card.innerHTML = `
    <div class="diff-card-head">
      <span class="diff-agent-badge">${data.agent || "Coding Agent"}</span>
      <span class="diff-file-path" title="${data.file}">${baseFilename(data.file)}</span>
      <span class="diff-counts">
        <span class="diff-add">+${data.added || 0}</span>
        <span class="diff-del">-${data.removed || 0}</span>
      </span>
      ${data.pid ? `<button class="diff-jump-btn" data-pid="${data.pid}" title="Focus Terminal Window">Jump ↵</button>` : ""}
    </div>
    ${data.patch ? `
      <details class="diff-patch-collapsible">
        <summary>View diff snippet</summary>
        <pre class="diff-patch-code"><code>${escapeHtml(data.patch)}</code></pre>
      </details>
    ` : ""}
  `;
  return card;
}
```

### 6.4 Clean Workspace Header (Eliminating Duplicate Search Input)
In `ui_pet/src/index.html`, replace the redundant `<input id="global-search">` with a clean telemetry and breadcrumb bar:
```html
<header id="topbar">
  <div class="topbar-context">
    <span class="session-pill">Active Session</span>
    <span class="model-badge"><i class="core-dot"></i> Qwen3-8B • Local</span>
  </div>
  <div class="topbar-actions">
    <button class="topbar-tool-btn" id="cmd-palette-btn" title="Command Palette (Ctrl+K)">
      <svg class="ic"><use href="#i-search"/></svg>
      <span class="kbd-hint">Ctrl K</span>
    </button>
    <button class="topbar-tool-btn" id="dictate-btn" title="Dictate to Cursor (Ctrl+Alt+D)">
      <svg class="ic"><use href="#i-mic"/></svg>
      <span class="kbd-hint">Ctrl Alt D</span>
    </button>
    <div class="topbar-divider"></div>
    <button class="icon-btn" id="top-settings" title="Settings"><svg class="ic"><use href="#i-sliders"/></svg></button>
  </div>
</header>
```

---

## 7. Automated Screenshot Testing Script (`scripts/inspect_ui.ps1`)

Create `scripts/inspect_ui.ps1` so `opencode` / `Claude Code` can capture screenshots of all windows and inspect them:

```powershell
# PowerShell UI Inspection Script
param([string]$OutputDir = "$PSScriptRoot\..\artifacts\ui_inspection")

if (!(Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null }

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Capture-WindowByName([string]$WindowName, [string]$Filename) {
    $proc = Get-Process | Where-Object { $_.MainWindowTitle -like "*$WindowName*" } | Select-Object -First 1
    if (!$proc) {
        Write-Warning "Window matching '$WindowName' not found."
        return
    }
    $h = $proc.MainWindowHandle
    [System.Windows.Forms.SendKeys]::SendWait("%{PRTSC}")
    Start-Sleep -Milliseconds 300
    $img = [System.Windows.Forms.Clipboard]::GetImage()
    if ($img) {
        $path = Join-Path $OutputDir $Filename
        $img.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
        Write-Host "Captured: $path"
    }
}

Write-Host "Capturing UI snapshots for visual review..."
Capture-WindowByName "Jarvis Pet" "pet_window.png"
Capture-WindowByName "Jarvis" "main_workspace.png"
Capture-WindowByName "Dynamic Island" "dynamic_island.png"
Write-Host "Screenshots saved to $OutputDir. Agent must now review them."
```

---

## 8. Quality Gate & Acceptance Criteria

1. **Mandatory Visual Inspection Completed:** The agent must run the visual inspection script and confirm zero clipping, zero awkward cropping, and zero overlapping elements.
2. **Warm, Cozy Vibe Validated:** The pet must feel like a soft, delightful, cuddly desktop companion (matte warm porcelain/mochi with gentle peach blush and warm lighting) rather than a harsh sci-fi terminal.
3. **Zero Pet Cropping:** Pet forehead, antenna, ears, and feet must have at least 20% clear space inside the window boundaries.
4. **Zero Persistent Chrome on Pet:** The pet window has NO permanent title bar and NO permanent button row. Control dock appears only on hover.
5. **Elevated Speech Bubbles:** All dialog bubbles and safety approval cards render strictly *above* the pet's head.
6. **Functional Sidebar Toggle:** The sidebar collapse button remains visible and clickable in both collapsed (68px) and expanded (240px) states.
7. **Working Dynamic Island:** Standalone `dock.html` sits flush to monitor top edge and expands smoothly on hover.
8. **Interactive Diff Cards:** Coding agent file edits render with colored badges and a working terminal focus jump button.
