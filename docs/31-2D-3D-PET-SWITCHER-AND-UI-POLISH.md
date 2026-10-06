# 31. SPECIFICATION: 2D/3D PET SWITCHER & LUXURY PRODUCT UI POLISH

**Document:** `docs/31-2D-3D-PET-SWITCHER-AND-UI-POLISH.md`  
**Target Agent:** `opencode` / `Claude Code`  
**Purpose:** Actionable blueprint to implement a seamless **2D Vector vs. 3D WebGL Pet Switcher**, eliminate remaining 3D rendering defects (banana-slice blush, waxy lighting), and polish the Main Workspace (chat layout, interactive in-stream approval cards, and clean single-tab settings).  
**Parent Documentation:** [27-UI-REVAMP.md](file:///d:/Personal_projects/2/Personal_AI/docs/27-UI-REVAMP.md), [29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md](file:///d:/Personal_projects/2/Personal_AI/docs/29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md), [30-OPENCODE-UI-REVAMP-MASTER-PLAN.md](file:///d:/Personal_projects/2/Personal_AI/docs/30-OPENCODE-UI-REVAMP-MASTER-PLAN.md)

---

## 1. Executive Summary & User Feedback Analysis

### 1.1 The User's Direct Feedback
> *"Better, but not quite right. And also let's make the app UI better too. Add an option to switch between 3D and 2D pet too."*

### 1.2 Analysis of the 3 Provided Screenshots

```
┌───────────────────────────────────────┬───────────────────────────────────────┬───────────────────────────────────────┐
│       SCREENSHOT 1: 3D PET DEFECTS    │       SCREENSHOT 2: CHAT VOID         │       SCREENSHOT 3: SCRAMBLED SETTINGS│
├───────────────────────────────────────┼───────────────────────────────────────┼───────────────────────────────────────┤
│ 1. Cheeks look like curved banana     │ 1. Giant empty dark void in center;   │ 1. "Voice" advanced card renders on   │
│    slices / parentheses (/ \).        │    chat bubbles don't fill naturally. │    top of "Assistant & Pet" section!  │
│ 2. Waxy/grayish tint with harsh white │ 2. Jarvis avatar is a flat orange dot │ 2. Sections bleed together instead of │
│    specular glare on forehead.        │    instead of the cute mochi mascot.  │    displaying clean single active tab.│
│ 3. Inner ears look like flat stickers.│ 3. Approval is plain text ("I need    │ 3. "Save changes" button disabled and │
│ 4. User LOVES the 2D hero illustration│    approval") without action buttons! │    awkwardly stuck at bottom of card. │
│    and wants a 2D/3D switcher!        │ 4. Composer is an oversized box.      │ 4. Inconsistent card paddings/gaps.   │
└───────────────────────────────────────┴───────────────────────────────────────┴───────────────────────────────────────┘
```

---

## 2. Core Feature: 2D vs. 3D Pet Switcher

The 2D Hero Mascot in `index.html` is an immediate visual hit—charming, cozy, crisp, and expressive. Users must have the choice between the **2D Animated Vector Mochi** and the **3D Dimensional WebGL Mochi**.

### 2.1 Configuration Schema
In `jarvis-desktop-pet/config/config.yaml`:
```yaml
runtime:
  pet_render_mode: "2d" # Options: "2d" (Classic Vector Mochi) | "3d" (Dimensional Mochi)
```

### 2.2 Dual-Stage Architecture in `pet.html`
Update `ui_pet/src/pet.html` so `#pet-stage` houses both the 2D SVG canvas and the 3D WebGL container:

```html
<div id="pet-stage">
  
  <!-- 1. 2D Animated Vector Mochi (Default / Toggleable) -->
  <div id="pet-2d" class="pet-render-layer" role="img" aria-label="Jarvis 2D Pet">
    <svg class="pet-svg-character" viewBox="0 0 128 128">
      <defs>
        <linearGradient id="p2d-body" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#fffdf8"/>
          <stop offset="100%" stop-color="#f6e7d2"/>
        </linearGradient>
      </defs>
      <!-- Ears -->
      <g class="p2d-ears">
        <ellipse class="p2d-ear-l" cx="42" cy="30" rx="14" ry="17" fill="url(#p2d-body)" transform="rotate(-14 42 30)"/>
        <ellipse class="p2d-ear-r" cx="86" cy="30" rx="14" ry="17" fill="url(#p2d-body)" transform="rotate(14 86 30)"/>
        <ellipse class="p2d-inner-l" cx="43" cy="31" rx="6.5" ry="9" fill="#fb923c" opacity="0.85" transform="rotate(-14 43 31)"/>
        <ellipse class="p2d-inner-r" cx="85" cy="31" rx="6.5" ry="9" fill="#fb923c" opacity="0.85" transform="rotate(14 85 31)"/>
      </g>
      <!-- Chubby Body Squircle -->
      <rect class="p2d-body-shape" x="17" y="34" width="94" height="82" rx="36" fill="url(#p2d-body)"/>
      <!-- Rosy Blush Cheeks -->
      <g class="p2d-cheeks">
        <ellipse class="p2d-blush-l" cx="34" cy="86" rx="8.5" ry="5" fill="#ff9e9e" opacity="0.75"/>
        <ellipse class="p2d-blush-r" cx="94" cy="86" rx="8.5" ry="5" fill="#ff9e9e" opacity="0.75"/>
      </g>
      <!-- Eyes with Dual Glints -->
      <g class="p2d-eyes">
        <ellipse class="p2d-eye-l" cx="47" cy="70" rx="7" ry="9" fill="#35292a"/>
        <ellipse class="p2d-eye-r" cx="81" cy="70" rx="7" ry="9" fill="#35292a"/>
        <!-- Highlights -->
        <circle class="p2d-glint-pri-l" cx="49.5" cy="66.5" r="2.6" fill="#fff"/>
        <circle class="p2d-glint-pri-r" cx="83.5" cy="66.5" r="2.6" fill="#fff"/>
        <circle class="p2d-glint-sec-l" cx="44.5" cy="74" r="1.4" fill="#fff" opacity="0.85"/>
        <circle class="p2d-glint-sec-r" cx="78.5" cy="74" r="1.4" fill="#fff" opacity="0.85"/>
      </g>
      <!-- Cheerful Smile Arc -->
      <path class="p2d-mouth" d="M57 92 Q64 99.5 71 92" stroke="#35292a" stroke-width="3.2" stroke-linecap="round" fill="none"/>
    </svg>
  </div>

  <!-- 2. 3D WebGL Stage (Three.js) -->
  <div id="pet-3d" class="pet-render-layer" style="display: none;">
    <div id="pet" data-mood="idle"></div>
  </div>

  <!-- Warm Ambient Floor Halo -->
  <div class="pet-floor-glow" aria-hidden="true"></div>
</div>
```

### 2.3 Contextual Quick-Toggle Button
In `pet.html` inside `#pet-hover-dock`, add the mode toggle button:
```html
<button class="dock-action-btn" id="dock-btn-rendermode" title="Switch 2D / 3D Mode" aria-label="Toggle 2D or 3D pet">
  <span id="dock-render-label" style="font-size: 10px; font-weight: 800;">2D</span>
</button>
```

### 2.4 Interactive 2D Pet Animation Engine (`ui_pet/src/pet2d.js`)
Create a lightweight, organic animation controller for the 2D pet:
* **Natural Blinking:** Every 3–5 seconds, eyes scale vertically (`transform: scaleY(0.08)`) for 120ms with randomized double-blinks.
* **Saccadic Eye Tracking:** The pupils (`.p2d-eyes`) translate smoothly towards the mouse pointer (`transform: translate(${dx}px, ${dy}px)`).
* **Click Squish & Jiggle:** Clicking the 2D pet triggers a fluid squash-and-stretch CSS spring (`transform: scale(1.15, 0.85)` rebounding over 320ms to `scale(1, 1)`).
* **Mood Morphing:**
  - `idle`: Gentle 0.12Hz floating breathing cycle (`translateY(-4px)`).
  - `happy` / `poked`: Mouth widens, cheeks blush brighter (`opacity: 0.95`).
  - `thinking`: Eyes glance upward, gentle tilt (`rotate(4deg)`).
  - `sleeping`: Eyes morph into sleepy arcs (`M40 70 Q47 76 54 70`), lighting dims.

---

## 3. Component 2: Polishing the 3D Pet (`pet3d.js`)

For users who select 3D mode, eliminate the visual flaws shown in Screenshot 1:

### 3.1 Fix the "Banana-Slice" Blush Cheeks
* **Problem:** In Screenshot 1, cheeks curved upward along the side of the sphere, looking like weird pink parentheses `(  )`.
* **Fix:** Position cheeks squarely on the front face normal (`z > 0.85`) rather than out near the curved side horizon. Use soft circular disks with horizontal scale:
```javascript
// Front-facing horizontal rosy clouds
faceSurf(-0.52, -0.22, 1, _bp);
faceNormal(_bp, _bn);
blushL.position.copy(_bp).addScaledVector(_bn, 0.05);
blushL.quaternion.setFromUnitVectors(_fwd, _bn);
blushL.scale.set(1.45, 0.82, 1.0); // wide horizontal pill

faceSurf(0.52, -0.22, 1, _bp);
faceNormal(_bp, _bn);
blushR.position.copy(_bp).addScaledVector(_bn, 0.05);
blushR.quaternion.setFromUnitVectors(_fwd, _bn);
blushR.scale.set(1.45, 0.82, 1.0);
```

### 3.2 Eliminate Waxy Grayish Tint & Harsh Glare
* **Problem:** The 3D pet looks like unbaked waxy dough with a harsh white specular spot on the forehead.
* **Fix:**
  - Increase diffuse roughness to `0.52` (soft matte ceramic/velvet touch).
  - Set `clearcoat` to `0.0` (removes the shiny plastic/wax reflection).
  - Add warm ambient light (`#fff8ee`, intensity `1.4`) and tungsten key light (`#ffe8cc`) so the body reads as warm creamy porcelain.

---

## 4. Component 3: Main Workspace Refinement (Chat & Settings)

### 4.1 Chat Thread Layout & Centered Flow (Screenshot 2 Fix)
* **Problem:** Giant empty dark void on the right; chat bubbles are tiny, flat, and isolated.
* **Fix in `app.css`:**
  ```css
  #msgs {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 24px 0 100px 0;
    max-width: 820px;
    margin: 0 auto;
    width: 100%;
  }

  .msg-row {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  /* User Message: Sleek Indigo Pill */
  .msg-row.user {
    justify-content: flex-end;
  }
  .msg-row.user .bubble {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.18), rgba(139, 92, 246, 0.22));
    border: 1px solid rgba(139, 92, 246, 0.35);
    color: #f8fafc;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    max-width: 75%;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  }

  /* Jarvis Message: Soft Warm Card with Cute Mascot Avatar */
  .msg-row.assistant .bubble {
    background: rgba(26, 28, 34, 0.85);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 245, 230, 0.08);
    color: #f3f0e8;
    border-radius: 18px 18px 18px 4px;
    padding: 14px 20px;
    max-width: 80%;
    line-height: 1.55;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
  }

  /* Replace flat orange circle with cute Mochi icon */
  .msg-row.assistant .msg-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #fdfbf7;
    border: 1.5px solid rgba(251, 146, 60, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    box-shadow: 0 0 10px rgba(251, 146, 60, 0.25);
  }
  ```

### 4.2 Interactive In-Stream Approval Cards (Screenshot 2 Fix)
* **Problem:** In Screenshot 2, the approval request appeared as plain text: *"I need your approval for that action. Action denied."*
* **Fix:** When an action requires approval, render an **Interactive Approval Card** right in the chat stream:
  ```html
  <div class="chat-approval-card" data-cid="${cid}">
    <div class="cac-badge"><svg class="ic"><use href="#i-shield"/></svg> Safety Authorization Required</div>
    <div class="cac-title">Delete File Confirmation</div>
    <div class="cac-target">Target: <code>C:\Users\PCGUYS~1\AppData\Local\Temp\opencode\zz_inspect_probe.txt</code></div>
    <div class="cac-risk">Risk Score: <span class="risk-pill high">8/10 High Risk</span></div>
    <div class="cac-actions">
      <button class="cac-btn-allow">Allow once</button>
      <button class="cac-btn-deny">Deny action</button>
    </div>
  </div>
  ```

### 4.3 Settings Screen Overhaul: Clean Single-Tab Navigation (Screenshot 3 Fix)
* **Problem:** In Screenshot 3, the `Voice` section's advanced settings bleed directly into `Assistant & Pet`, and multiple sections are stacked into one confusing scrolling mess.
* **Fix:** Enforce **Strict Single-Tab Switching** in `ui_pet/src/settings.js`:
  ```javascript
  // Strict Tab Switching: Only show the currently active section!
  function showSettingsTab(tabName) {
    document.querySelectorAll(".settings-nav-btn").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.section === tabName);
    });
    document.querySelectorAll("#settings-content .section").forEach(sec => {
      const match = sec.id === `sec-${tabName}`;
      sec.style.display = match ? "block" : "none";
      if (match) sec.classList.add("fade-in");
    });
  }
  ```

#### New Setting in "Assistant & Pet" Tab:
Add the companion appearance segmented control in `index.html`:
```html
<div class="card">
  <div class="card-title">Companion Appearance</div>
  <div class="field">
    <label>Pet Render Style</label>
    <div class="segmented-control" id="pet-render-seg">
      <button type="button" data-render="2d" class="on">2D Vector (Classic Mochi)</button>
      <button type="button" data-render="3d">3D WebGL (Dimensional)</button>
    </div>
    <p class="hint">2D Vector: ultra-crisp, battery-efficient, expressive SVG companion. 3D WebGL: tactile dimensional mesh.</p>
  </div>
</div>
```

---

## 5. File-by-File Implementation Instructions for `opencode`

| Step | Target File | Exact Action Required |
| :--- | :--- | :--- |
| **1** | `ui_pet/src/pet.html` | Add dual `#pet-2d` and `#pet-3d` containers inside `#pet-stage`. Add `#dock-btn-rendermode` toggle to micro-dock. |
| **2** | `ui_pet/src/pet2d.js` | Create the 2D Mochi animation loop (blinking, pupil tracking, squish on click, reactive moods). |
| **3** | `ui_pet/src/pet.js` | Add `setRenderMode("2d" | "3d")` logic, listen for `ui.pet_render_mode` events, wire dock toggle button. |
| **4** | `ui_pet/src/pet3d.js` | Fix 3D cheeks: position at `faceSurf(±0.52, -0.22, 1)`, horizontal pill scale, remove waxy specular shine. |
| **5** | `ui_pet/src/app.css` | 1. Style `.msg-row` with centered `max-width: 820px`.<br>2. Style `.chat-approval-card` with buttons.<br>3. Fix `#settings-content` to hide non-active sections cleanly.<br>4. Style `#pet-2d` and `#pet-3d` layers. |
| **6** | `ui_pet/src/chat.js` | Render interactive `.chat-approval-card` when `ui.approval` arrives instead of plain text message. |
| **7** | `ui_pet/src/settings.js` | Implement strict single-tab rendering (`sec.style.display = match ? "block" : "none"`), bind `pet-render-seg` control. |
| **8** | `ui_pet/src/index.html` | Add "Companion Appearance" card with 2D/3D segmented control in `#sec-assistant`. |

---

## 6. Quality Gate & Acceptance Checklist

1. **2D/3D Toggle Works Instantly:** Clicking the `2D/3D` button in the pet micro-dock or changing the setting in `Assistant & Pet` immediately switches the pet render without restarting or crashing.
2. **2D Pet is Adorable & Reactive:** The 2D vector pet blinks, tracks the mouse cursor, squishes elastically on click, and displays joyful blush and smile.
3. **3D Pet Cheeks Fixed:** In 3D mode, blush cheeks are horizontal fluffy pink ovals, not vertical banana curves.
4. **Chat Stream is Centered & Polished:** Messages flow down a readable, centered 820px thread with cute mochi assistant avatars.
5. **Interactive In-Stream Approval Cards:** When a dangerous action is proposed, a formatted card with "Allow once" / "Deny" buttons appears directly in the chat view.
6. **Settings Sections Cleanly Isolated:** Clicking `Assistant & Pet`, `Voice`, or `Models` shows *only* that section with zero overlapping or bleeding headers.
