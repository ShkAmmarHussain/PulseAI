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

## 10. As-built: Phase 2 (Activity, Memory, Settings, Onboarding, approvals)

Same branch. The character art and `mochi` identifiers are still untouched (§1.1 open), so onboarding step 1 reads "Meet your companion", not "Meet Pip".

**Activity (§4).** Events are grouped into task cards (status dot, title, time, `Done` tag) holding step rows, with a soft state glow at the card's bottom edge. Timers sit at the top as pills with a live countdown and a dark Cancel pill.

**Memory (§4).** Borderless `--card` cards, category pills, and Edit / Forget that appear on hover or keyboard focus. Inline edit swaps the text for a textarea (Enter saves, Esc cancels, Save is the white pill). The draft survives `memory.updated` re-renders, and an edited fact shows "· edited". Backend: new WS command `memory.update` (`{id, content?, category?}`) → `ws_bridge._memory_update` → `memory_skills.edit` → `memory_store.update_fact`, which keeps `id`/`created_at`, stamps `updated_at`, rejects empty content and publishes `memory.updated`. Covered by `tests/memory_update_test.py` (offline store checks plus a WS add → update → delete round trip, 14/14). Fix found in capture: `.memory-add-form` set `display: grid`, which beat `[hidden]`, so the add form showed on load.

**Settings (§4).** Stacked cards: amber dot + title, a one-line `.card-desc` explanation, then controls. The index now leads with Model, then Voice, Character & Desktop, Privacy & Safety, Performance, Dictionary, Dictation History, Integrations. Deviation: key fields have no per-field Save pills yet; the existing sticky Save bar stays the one save action.

**Onboarding (§6).** One full-window black sheet under the 36px header (drag and window controls keep working), a centred step bar, one `--card` per step and a white-pill Next / Finish. The character reacts per step through `data-step` (wave, listen, celebrate), with no animation under `prefers-reduced-motion`. `window.openOnboarding()` is exposed for inspection.

**Approvals (§7.2, UI review item 1).** New `approval_text.js` (loaded by `index.html` and `pet.html`) maps raw tool names to friendly titles ("Delete zz_inspect_probe.txt"), turns the 0-10 risk into one Low / Medium / High pill, and drops the backend's stock "Allow this action? (…)" prompt. The pet card and the in-chat card both use it: "Needs your OK" status line, bold title, risk once, mono target chip, white Allow pill and dark Deny pill. Fix found in capture: `.approval-body` was capped at 66px and clipped the target chip; it is now 128px.

**Inspection.** `inspect_states.py` adds `main_onboarding`, opened in the real app through its own CDP (`:9335`, app launched with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9335 --allow-file-access-from-files`). It is skipped when that port is down. 21/21 steps.

After captures (real windows, 1100×760): `jarvis-desktop-pet/artifacts/ui_inspection/spec34/after/` (`main_activity`, `main_memory`, `main_settings`, `main_onboarding`, `main_app_expanded`, `main_app_menu`, pet and dock states including `pet_approval`).

Gates (non-mic, 2026-11-01, source backend on :8765, LM Studio down): smoke OK, ws_ping, memory_update 14/14, model_router 30/30, fast_router 71/71, vocab 17/17, audio_cache, tts_wake, injector 17/17, hook_e2e 37/37, dictation_ui 27/27 (one flaky 26/27 run on "add mapping row", green on rerun), phase5_e2e 14/14, phase5_dock_check 27/27, phase5_visual_check 28/28, chat_e2e, agent_e2e, voice_e2e ALL OK, pet_springs 9/9, inspect_states 21/21. wake_e2e prints `WAKE E2E PASS`, then the interpreter crashes in native teardown (0xC0000005 this run). Not run (live mic): hotkey_e2e, dictation_flow_test. Tests rewrite `config/config.yaml` (drops comments) and `config/vocabulary.json`; restore both from git after a run.


## 11. As-built: Phase 3 (island states)

Same branch. §1.2 is still unanswered, so this phase assumes **A. Hybrid**, the recommended layout: the island owns approvals and quick results whenever it is the companion (`runtime.companion: dock`), and the main window keeps long chats, Memory, Activity and Settings. The pet and dock stay mutually exclusive companions, as before. The `mochi` identifiers and art are untouched. The island's face is still the existing two-eye pill.

**Sizes (`dock_standalone.js`).** The island has four sizes:
- Hidden wake strip, 240×6. The island tucks away after 12 s of quiet: idle state, not hovered, nothing pinned, no diff badge. Hover peeks it open, and any event wakes it.
- Compact pill, 240×36.
- Expanded, 460 wide. Its height is measured from the visible card, and re-measured on `transitionend` because the width animation rewraps text.
- Drop swell, 320×72.

`set_companion` now evals `onCompanionChanged` into the pet and dock windows too. The dock uses it to start from the compact pill, not a strip that tucked away while hidden. Width and height use a spring-like `cubic-bezier(0.34, 1.36, 0.64, 1)`, and reduced motion turns it off.

**Expanded header.** Tabs **Home · Chat · +**. `+` starts a fresh inline chat. Home shows the most urgent card: approval, then question, then a fresh result or error, then overview.

**Cards.** All cards are `--card` on black, with a radial state glow at the bottom edge, a status line (dot, bold title) and one white-pill action.
- *Overview:* the character on the left, and on the right a live step list of up to 4 steps (icon per step, current one bright with an amber icon, past ones dim). It also has the progress bar and the original three `.drawer-btn` controls (talk, workspace, switch to pet).
- *Approval:* the friendly title and risk pill from `approval_text.js`, the command in a mono chip and a countdown. **Deny `N`**, **Always** and **Allow `Y`**, with the white pill on Allow and an amber glow. Y and N work while the island has focus. **Always** appears only for coding-agent hook approvals, because that is the only path the backend grants for a session (`hook_bridge` `remember`). The card clears when the outcome `ui.chat` arrives on the same correlation id, or on `ui.approval_cancelled`. While the island is the companion, `pet.js` ignores `ui.approval`, and the pet card remains the fallback in pet mode.
- *Question / Choose:* option rows (keys 1-9, Enter confirms), Skip, and a white-pill Confirm. Backend: `ui.question` is now forwarded to the UI, and a `question_response` reply is republished on the bus as `ui.question.response` (same correlation id). No backend agent raises `ui.question` yet, so this card is wired, but nothing produces it today.
- *Result:* raised by a successful `tool.result`. The title is the summary's first line, with up to 3 rows (friendly step names, then the remaining summary lines), **Open** (white, opens the chat) and **Close**, and a green glow. It stays pinned for 6 s.
- *Error:* raised by a failed `tool.result` or a voice error. It shows one line of cause, **Details** (opens Activity through the new Tauri command `open_tab`) and **Retry** (white; it resends the last request and is hidden when there is none), with a red glow. It stays pinned for 10 s.
- *Chat:* the last 3 messages (user `--tab-on` pills, assistant plain text) and a composer with a round white send button and an indigo glow. Replies longer than 280 characters show **Continue in window**. A focused composer or an unsent draft keeps the island open. Esc collapses the island.
- *File drop:* the island swells to 320×72, and the character pill bobs over "Drop file to inspect…". It gulps on drop and adds a step; ingestion is unchanged.

All Phase 5 dock ids and markers are kept (`phase5_dock_check` 27/27).

**Inspection.** `window.islandDemo(name)` stages a card for captures. `inspect_states.py` gains `island_states()`, which drives the real dock through `:9335`. The approval is a real one (the delete probe while in dock mode). The script asserts the island shows it, that the pet card stays at `display: none`, and that the card clears once denied. The other cards are staged. 40/40 steps.

After captures: `jarvis-desktop-pet/artifacts/ui_inspection/spec34/after/`
- `island_hidden`, `island_overview`, `island_approval`, `island_question`
- `island_result`, `island_error`, `island_chat`, `island_drop`
- refreshed `dock_collapsed` (compact) and `dock_expanded`

Gates (non-mic, 2026-11-01):
- smoke OK, ws_ping, memory_update 14/14, model_router 30/30, fast_router 71/71, vocab 17/17
- audio_cache, tts_wake, injector 17/17, hook_e2e 37/37, dictation_ui 27/27
- phase5_e2e 14/14, phase5_dock_check 27/27, phase5_visual_check 28/28
- chat_e2e, voice_e2e ALL OK, pet_springs 9/9, inspect_states 40/40
- agent_e2e: the first run's web search came back empty, and it was green on rerun.
- wake_e2e: `WAKE E2E PASS`, then the known native-teardown crash (0xC0000374).
- Not run (live mic): hotkey_e2e, dictation_flow_test.


## 12. As-built: Phase 5 (production items, before Phase 4)

Same branch. Code signing (§7.5) is not done: it needs your certificate. The brand item (§7.1) is partial: `jarvis-desktop-pet/ATTRIBUTIONS.md` credits coucou (MIT, with its full notice) for the adapted design tokens, the island state model and the keys-in-the-OS-store idea, and repeats that coucou's name, character and art are outside the MIT licence.

**States (§7.2).**
- `ws.js` now emits `jarvis:reconnecting {seconds}` during each backoff and exposes `Jarvis.reconnectNow()` and `Jarvis.isConnected()`.
- Main window: an `#offline-banner` live status region floats under the header with a dot, "Jarvis isn't running. Reconnecting in Ns…" and a white **Retry now** pill. On a cold start it waits 2.5 s before appearing. The error earcon plays once per outage, not on every retry.
- Island: the headline counts down, "Offline — retrying in Ns".
- Pet: the bubble says "Lost the backend — reconnecting…", then counts down quietly during longer outages.
- Memory: shows "Loading memories…" or "Memory is offline" until the store first answers, instead of claiming nothing is remembered.
- No raw tool names: Activity step names go through `ApprovalText.friendlyAction`.

**Accessibility (§7.3).**
- A final block in `app.css` gives every button, tab, radio, summary, link and `[tabindex]` a 2px amber `:focus-visible` outline. Inputs and composers get an amber ring, because Phase 2 restyles had zeroed the old box-shadow ring.
- The API-key reveal buttons are back in the tab order (they had `tabindex="-1"`).
- `--dim-3` was lifted again to `#838891`: `#7d828b` was 4.27:1 on `--tab-on`.
- New gate `tests/a11y_check.py` (static, 31/31): AA contrast for `--ink`, `--dim` and `--dim-3` on `--bg`, `--card`, `--card-flat` and `--tab-on`; the white pill; that the focus block exists; no `<button tabindex="-1">`; no raw tool names in visible markup; `aria-current` / `aria-selected`; the offline live region; reduced motion.

**Performance (§7.4).**
- Tauri v1 hides windows without changing `document.hidden`. `main.rs` now evals `window.setPetVisible(bool)` into the pet on every show/hide (`set_pet`, `set_companion`, close-to-hide).
- `pet3d.js` renders nothing while hidden (it was 1 FPS) and restarts its clock on return.
- `pet2d.js` runs its eye loop only while the eyes are moving, and never while hidden.
- New gate `tests/perf_check.py`, against the real app on `:9335` (5/5): 3D idle at 10 FPS (fpsInterval 100, 10.0 renders/s), the 2D eye loop idle at 0 frames, and a hidden pet rendering 0 frames.
- Not done: the 3D renderer still idles at 10 FPS behind the 2D pet. `phase5_visual_check` asserts that throttle in the mirror tab, so pausing 3D in 2D mode needs that test reworked first.

**Packaging (§7.5).**
- One version source: `tauri.conf.json` `package.version`, read with `__TAURI__.app.getVersion()`. The mirror tabs say "Development build".
- New Settings section **About** (`#sec-about`): version, backend connection, **Export diagnostics** with **Show in folder**, and credits.
- WS `diagnostics.export {app_version}` calls `backend/diagnostics.py` `export_bundle`. It writes `%APPDATA%\JarvisDesktopPet\diagnostics\pulseai-diagnostics-<stamp>.zip`, containing `about.json`, `rm_state.json`, every settings YAML with secret fields replaced by `<redacted>`, and `backend.log(.1)` with key-shaped strings masked.
- `diagnostics.reveal` opens Explorer, and only on bundles inside that folder.

**Settings safety (§7.6).**
- New `core/credentials.py` talks to Windows Credential Manager through `advapi32` with ctypes, so there is no new dependency and it works in the frozen backend. `keyring` is not installed, and installing it would have meant a new download.
- `llm.<openai|anthropic>.api_key` is moved to a generic credential `PulseAI/llm.<provider>`. The config keeps `api_key: ''` and `api_key_ref: wincred:PulseAI/llm.<provider>`.
- Migration runs at backend startup (`ws_bridge.migrate_config_keys`) and on every `save_settings`.
- `get_settings` adds a computed `api_key_saved` flag that is never persisted. `llm.get_api_key` resolves the inline key first, then the ref.
- Settings shows "Saved in Windows Credential Manager", and a saved key is not echoed. An empty field keeps the stored key, and **Forget key** sends `api_key_clear`.
- The LM Studio key (`lm_studio.api_key`, a local placeholder) is unchanged.
- New gate `tests/credentials_test.py` (19/19): write/read/delete, unicode round trip, migration, resolve, empty-keeps, Forget, redaction, log scrub, and a real `diagnostics.export` zip with no key-shaped strings. Every credential it creates is deleted again.

Captures added in `spec34/after/`: `main_about` (version v0.1.0 read from tauri.conf), `main_offline` (backend stopped, banner counting down). `inspect_states` 43/43.

Gates (non-mic, 2026-11-01): smoke OK, ws_ping, a11y_check 31/31, credentials_test 19/19, perf_check 5/5, memory_update 14/14, model_router 30/30, fast_router 71/71, vocab 17/17, audio_cache, tts_wake, injector 17/17, hook_e2e 37/37, dictation_ui 27/27, phase5_e2e 14/14, phase5_dock_check 27/27, phase5_visual_check 28/28, chat_e2e, agent_e2e, voice_e2e ALL OK, pet_springs 9/9. wake_e2e: PASS, then the known teardown crash (0xC0000374). Not run (live mic): hotkey_e2e, dictation_flow_test.
