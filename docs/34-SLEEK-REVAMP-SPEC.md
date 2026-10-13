# 34. SPECIFICATION: SLEEK REVAMP (coucou-inspired, production-ready)

Status: **draft, waiting on two decisions (§1)**. Inspiration: `coucou/` (MIT code, see §1.1 for the asset licence). Target: the main window, the island (dock), the pet, and onboarding, all in one visual language. Production readiness gets its own section (§7).

## 1. Decisions

### 1.1 Character and brand (required before any release)
`coucou/LICENSE-ASSETS.md` keeps the **name "Mochi"** and the **Mochi character design** (a soft squircle with big eyes, its expressions and animations) out of the MIT licence. PulseAI currently uses the name "Mochi" in code, CSS, docs and UI, and its pet is very close to that design. That's fine for personal use, but it **cannot ship publicly** without written permission.
- **Plan:** rename the character (working name **"Pip"**, easy to change) and redraw it so it is clearly its own. Keep the same rig (springs, eyes, moods) so no engine work is lost, but change the silhouette: a rounded **teardrop/egg body with a single antenna-sprout** and **no bunny ears**, set apart by one **signature colour** (warm amber core light) instead of coucou's white or blue. We can borrow coucou's *code ideas* freely, with an MIT notice, but none of its art.
- Rename `mochi` identifiers to `pip` (`#i-mochi`, `.mochi-*`, `hero-mochi`, docs).

### 1.2 Where the product lives
- **A. Hybrid (recommended):** the **island** at the top edge becomes the main surface (status, approvals, results, quick chat, as in coucou). The **main window** stays for long chats, Memory, Activity and Settings, restyled in the same language.
- **B. Window-first:** keep today's layout and restyle it only.
- **C. Island-only:** the window shrinks to Settings, and everything else happens in the island and the pet.

## 2. Design language (taken from coucou's tokens and adapted)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#000` | island, window chrome |
| `--card` | `#141518` | primary cards |
| `--card-flat` | `#0e0f11` | inset rows, inputs |
| `--tab-on` | `#1d1f23` | active tab, secondary pill |
| `--hairline` | `rgba(255,255,255,.035)` | the only border |
| `--ink` / `--dim` / `--dim-3` | `#f5f6f8` / `#9398a1` / `#6b7079` | text levels |
| `--accent` | `#f5a524` (amber, kept as PulseAI's signature) | focus, live dot, character core |
| state glows | amber (approval), green `#22c55e` (done), red `#f4505e` (error), indigo `#6366f1` (chat/listening) | a soft radial glow at the card's bottom edge |
| font | `system-ui, "Segoe UI Variable Text", "Segoe UI"`; mono `"Cascadia Mono", Consolas` | |
| radius | island 0 0 22 22; cards 22; rows 12; pills 999 | |

Rules:
- **No borders except the hairline.** Depth comes from card-on-black contrast and the state glow.
- **One primary action per surface.** It is a **white pill** (`#fff` background, `#000` text). Secondary actions are dark pills (`--tab-on`). Keyboard hints go in small outlined key caps (`Y`, `N`, `Esc`).
- **Status line pattern:** a coloured dot, then **bold title**, then a dim subtitle (for example "● Jarvis wants to run a command").
- Commands, paths and diffs sit in a mono chip on `--card-flat`.
- Motion: 180 ms ease-out for state changes, spring for the island's height and width, and `prefers-reduced-motion` respected everywhere.

## 3. Island (top-edge surface)
- **Hidden** when idle: a 240×6 wake strip that peeks open on hover.
- **Compact:** a black pill with the character's face, a status dot and a one-line headline, plus a diff badge for coding agents.
- **Expanded:** a 3-tab header (Home · Chat · +), then one card per state:
  - *Overview:* the character on the left, and on the right the live step list of the current task (an icon per step, the current one bright and past ones dim).
  - *Approval:* the command in a mono chip, then **Deny (N)**, **Always**, **Allow (Y)** with the white pill on Allow and an amber glow. This replaces the approval card on the pet.
  - *Question / Choose:* option rows plus a white-pill confirm.
  - *Result:* a title and up to 3 result rows, then **Open** (white) and **Close**, with a green glow.
  - *Error:* a red glow, one line of cause, and **Retry** / **Details**.
  - *Chat:* an inline composer with a round white send button and an indigo glow. Long chats hand off to the window.
- File drop: the island swells and the character "catches" the file.

## 4. Main window
- The frameless titlebar is merged into a **36px black header** with no separate topbar. On the left are the character mark and the tabs **Chat · Activity · Memory · Settings** as pills (the active one on `--tab-on`). On the right are the provider pill (Local · Auto) and the window controls.
- **The sidebar is removed.** The pet toggle and Quick actions move into a `+` menu.
- **Chat:** a centred 720px column. The empty state is the character, a greeting from `personality.yaml` (not a hardcoded name), and 4 suggestion pills. Assistant messages have no bubble (plain text with a small character avatar). User messages are `--tab-on` pills aligned right. Tool events and diffs collapse into single **step rows**. The composer is a floating `--card` bar with a white round send button.
- **Activity:** step rows grouped by task, with each task as a card with a status dot. Timers sit at the top as pills with a live countdown.
- **Memory:** a search field with category pills, then cards on `--card` with no borders. Forget appears on hover. Add an inline **edit**, since the empty state promises it.
- **Settings:** coucou-style stacked cards (dot, title, one-line explanation, then controls). There are sections for Model, Voice, Character, Desktop, Integrations and Privacy, and key fields have Save pills.

## 5. Pet
- The redrawn character (§1.1) in 2D SVG by default, with 3D as an option.
- It loses its approval card and toolbar: approvals go to the island, and right-click opens a compact menu.
- It keeps the springs, gaze, moods, file drop and fly-to-island on alert.

## 6. Onboarding
- One full-window black sheet, not a modal, with 3 steps: **Meet Pip**, **Microphone**, **Model**. Each step is a single card with one white-pill action, and the character reacts on each step (waves, listens, celebrates).

## 7. Production readiness (same push)
1. **Brand/IP:** finish §1.1, and add an `ATTRIBUTIONS.md` crediting coucou (MIT) for any adapted code.
2. **States:** every surface has empty, loading, offline (backend down, with a reconnect countdown) and error states. No raw tool names (`delete_file`) appear in the UI.
3. **Accessibility:** visible focus rings, `aria-current`, every action reachable by keyboard, WCAG AA contrast for `--dim` text on `--card`, and reduced motion.
4. **Performance:** the pet idles at 10 FPS and pauses when hidden, the island uses `will-change` only while animating, and no layout thrash on stream.
5. **Packaging:** a signed installer (code-signing certificate needed, which you have to provide), a versioned About pane, crash/diagnostics bundle export, and a single version source (`tauri.conf.json` → UI pill).
6. **Settings safety:** API keys move from `config.yaml` to Windows Credential Manager (as coucou does), and `config.yaml` stores only a reference.
7. **Verification:** new `inspect_states.py` captures for every island state and pane, the 19-suite gate green, and before/after screenshots in `docs/34`.

## 8. Phases
1. Tokens + main window shell (header tabs, no sidebar) + Chat.
2. Activity, Memory (with edit), Settings, Onboarding.
3. Island states (overview, approval, question, result, error, chat).
4. Character redraw + rename, then pet simplification.
5. Production items in §7 + captures + docs.

## 9. As-built: Phase 1 (tokens + shell + Chat)

Branch `revamp/spec34`. The character and its `mochi` identifiers are untouched (§1.1 is still open).

**Tokens (§2).** `:root` in `app.css` now defines `--bg`, `--card`, `--card-flat`, `--tab-on`, `--hairline`, `--ink`, `--dim`, `--dim-3`, the four state glows, `--font-ui` / `--font-mono` and the card/row radii. The older tokens (`--bg-app`, `--bg-surface`, `--text-*`, `--border-*`, `--accent*`, `--success`, `--danger`, `--info`) are remapped onto them, so Activity, Memory, Settings, the pet and the island pick up the palette before Phase 2 restyles them. Deviations:
- `--dim-3` is `#7d828b`, not `#6b7079`. The spec value is about 3.9:1 on `--card`, and §7.3 asks for WCAG AA.
- `--border-default` / `--border-strong` stay a little brighter than the hairline (0.06 / 0.1), so form controls in Settings keep an edge until their Phase 2 restyle.
- The legacy aliases `--bg`, `--card` and `--dim` were unused (only `--grad` was referenced), so they now carry the spec 34 values directly.

**Shell (§4).** `#window-titlebar` is the only bar: character mark plus a connection dot (`#conn-dot`, with `#conn` visually hidden while connected and shown in red when down), tab pills `#nav .nav-item[data-tab]` (same `showTab()`, `aria-current`), a drag region, then the provider pill `.model-badge`, `#cmd-palette-btn`, `#dictate-btn` and the `+` menu `#quick-actions-btn` → `#plus-menu` (pet switch `#pet-side-toggle[data-pet-toggle]`, Quick actions, Command palette, Dictate, Settings `#top-settings`; Esc and outside clicks close it). `#sidebar`, `#sb-toggle`, `#topbar` and the `sb-collapsed` logic are gone; every other id is kept.

**Chat (§4).** Centred 720px column. The greeting reads `personality.yaml` → `user.name` (added: `Ammar`) through `window.setGreeting()` from `onSettingsLoaded`, and is nameless when unset (`USER_NAME` removed from `chat.js`). Four suggestion pills. Assistant replies have no bubble (22px character avatar, name, time, then plain text). User messages are right-aligned `--tab-on` pills with no meta row. System lines and coding-agent diff cards render as `--card-flat` step rows. The composer is a floating `--card` bar with a white round send button and an indigo glow while listening.

**Inspection.** `scripts/inspect_states.py` probes the header (tabs left-anchored; `+` mapped by its distance from the right edge, because the mirror viewport is a different width) and captures `main_app_menu`, `main_activity`, `main_memory` and `main_settings` in place of `main_app_collapsed`: 19/19 steps. `inspect_ui.ps1` and the driver also raise the main window with a TOPMOST/NOTOPMOST round trip. Without it, the first run captured whatever window covered the app.

Before/after captures (real windows, 1100×760):
- before: `jarvis-desktop-pet/artifacts/ui_inspection/spec34/before/` (`main_app_expanded`, `main_app_collapsed`, `empty/main_app_expanded`, pet and dock states)
- after: `jarvis-desktop-pet/artifacts/ui_inspection/spec34/after/` (`main_app_expanded`, `main_app_menu`, `main_activity`, `main_memory`, `main_settings`, `empty/main_app_expanded`, pet and dock states)
Gates (non-mic, 2026-10-14): smoke OK, ws_ping, model_router 30/30, fast_router 71/71, vocab 17/17, audio_cache, tts_wake, injector 17/17, hook_e2e 37/37, dictation_ui 27/27, phase5_e2e 14/14, phase5_dock_check 27/27, phase5_visual_check 28/28, chat_e2e, agent_e2e, voice_e2e ALL OK, pet_springs 9/9, inspect_states 19/19. wake_e2e prints `WAKE E2E PASS` but the interpreter exits with 0xC0000374 during native teardown. This branch has no backend changes. Not run, because they need a live mic: hotkey_e2e, dictation_flow_test. Run notes: smoke_test needs `PYTHONPATH` set to `jarvis-desktop-pet`; wake/voice e2e boot their own backend, so stop the one on :8765 first; and the Edge mirror must be started with `--allow-file-access-from-files`, or pet3d.js (an ES module) cannot load and `Pet3D.debug` fails.