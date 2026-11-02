# 35. Full QA test plan (real Windows build, end to end)

Status: **executed 2026-11-03 on the installed build; results with evidence in §12.**

## 1. Why this exists

The spec 34 gates were automated suites. They ran against a scratch copy of `jarvis-pet.exe` with the backend started separately from source, plus an Edge "mirror" of the UI. They never exercised the app the way a user runs it: launch it, close it, reopen it, use the tray, quit. Three bugs reached the user:

- **B1.** Closing Jarvis leaves it running in the background.
- **B2.** The chat buttons (pet, island, dock, tray "Open Jarvis") don't open the chat window.
- **B3.** Opening Jarvis again starts a duplicate app.

This plan covers every surface and every interactive element on the **real release build**, from the user's point of view.

## 2. Test setup

| Item | Value |
|---|---|
| Build under test | `ui_pet/src-tauri/target/release/jarvis-pet.exe` built from `revamp/spec34`, deployed as **`test_install\JarvisDesktopPet.exe`**, next to a **freshly built `test_install\jarvis-backend.exe`** (PyInstaller). This is the layout the app ships with: the UI spawns the backend sidecar itself. |
| Second build | The user's existing install (whatever the Start-menu "Jarvis" shortcut points at), only to confirm B1–B3 reproduce before the fix and are gone after. |
| How it is launched | Double-click / `Start-Process` on the exe, exactly like the shortcut. **Never** with a separately started source backend. |
| Debug access | `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9335` only for DOM reads. Every *action* is a real input: Windows UI Automation `Invoke()` / physical clicks / `SendInput` keys. |
| Process checks | `Get-Process JarvisDesktopPet, jarvis-backend, msedgewebview2` plus the parent PID (orphan detection), and `Get-NetTCPConnection -LocalPort 8765`. |
| Screenshots | `scripts/inspect_ui.ps1`, saved to `jarvis-desktop-pet/artifacts/qa35/<case-id>.png`. |
| Window sizes | Default **1100×760**, and the minimum **760×560** (`minWidth`/`minHeight` in `tauri.conf.json`). |
| Clean state | Before each run: no `JarvisDesktopPet` or `jarvis-backend` processes, port 8765 free, and `config.yaml` / `vocabulary.json` restored from git afterwards. |

Verification codes used below: **P** = process / port check, **U** = real UI Automation or physical input, **D** = DOM read over CDP 9335, **S** = screenshot reviewed by eye, **L** = backend log line.

## 3. Lifecycle (launch, close, reopen, quit)

| ID | Steps | Expected | Verify |
|---|---|---|---|
| L1 | Cold launch the exe (first run, `data/onboarded.json` absent) | 1 `JarvisDesktopPet`, 1 `jarvis-backend` (child of it), :8765 listening within 15 s. Main window shows the onboarding sheet. The pet shows. | P, S |
| L2 | Cold launch (repeat run, already onboarded) | Same processes. Main window opens on Chat with the Pip hero. No onboarding. | P, S |
| L3 | **B3:** with Jarvis running, launch the exe again (shortcut / double-click) | **No second UI and no second backend.** The existing main window is restored and focused. Process counts stay 1 + 1. | P, U, S |
| L4 | B3 variant: main window hidden (closed to tray), launch again | The hidden main window reappears focused. Still 1 + 1. | P, U |
| L5 | **B1:** click the titlebar ✕ | Defined behaviour: **close hides to the tray**. The main window disappears, the tray icon stays, and the backend keeps running so the pet and island still work. A one-time hint says "Jarvis is still running in the tray" (or Settings has an option to quit on close). | P, U, S |
| L6 | **B1:** tray → **Quit** | **Everything ends:** no `JarvisDesktopPet`, no `jarvis-backend`, no orphaned `msedgewebview2` of ours, :8765 free within 5 s. | P |
| L7 | Alt+F4 on the main window | Same as L5 (hide). | U, P |
| L8 | End `JarvisDesktopPet` in Task Manager (crash simulation) | The backend notices its parent is gone and exits within 10 s. No orphan. | P |
| L9 | Backend crashes (kill `jarvis-backend` only) | UI shows the offline banner with a countdown. Behaviour is defined: the sidecar is restarted, or Retry reconnects once it is back. | P, S, D |
| L10 | Minimize / maximize / restore buttons and titlebar double-click | Each does what it says. Maximize fills the work area and restores to the previous size. Drag on the empty header moves the window. | U, S |
| L11 | Launch with `--hidden` (autostart path) | Main hidden, pet/island visible, 1 + 1 processes. | P |
| L12 | Autostart toggle (Settings → Voice → Launch at login) on, then off | The Run key is written and then removed, and it points at the installed exe path. | P (registry), D |

## 4. Opening the chat window from everywhere (B2)

Run each case with the main window in each of three states: (i) open behind other windows, (ii) minimized, (iii) closed to the tray.

| ID | Trigger | Expected | Verify |
|---|---|---|---|
| C1 | Tray icon left-click | Main window shown, restored, focused, on the **Chat** tab | U, S |
| C2 | Tray → Open Jarvis | Same as C1 | U, S |
| C3 | Tray → Settings | Main window shown on **Settings** | U, S |
| C4 | Tray → Show / Hide Pet | The pet toggles. Its state stays in sync with Settings and the `+` menu switch. | U, D |
| C5 | Pet: single click on Pip | Opens the chat (C1 result) plus the squish | U, S |
| C6 | Pet hover dock: Chat button | Same as C1 | U, S |
| C7 | Pet hover dock: Settings button | Main on Settings | U |
| C8 | Island overview: Workspace button | Same as C1 | U |
| C9 | Island result card: **Open** | Same as C1 | U |
| C10 | Island error card: **Details** | Main on **Activity** | U |
| C11 | Island chat card: "Continue in window" | Same as C1 | U |
| C12 | Dropping a file on the pet or island | Main shows chat with the composer prefilled "Summarize this file…" | U, D |

## 5. Main window: header and `+` menu

| ID | Element | Expected | Verify |
|---|---|---|---|
| H1 | Pip mark and connection dot | Green while connected. Red, with a "Reconnecting…" label, while down. | S, D |
| H2–H5 | Tabs Chat / Activity / Memory / Settings | Switch panes. `aria-current` moves. The active pill is on `--tab-on`. Keyboard: Tab focuses each tab, Enter activates it. | U, D, S |
| H6 | Provider pill | Shows the current provider and auto-routing ("Local Model · Auto"), and updates after a Settings save | D |
| H7 | Search / Command palette | Opens the palette with focus in the input. Esc closes it. Commands run. | U |
| H8 | Dictate (mic) | Starts and stops dictation, and the mic state is shown (mic-dependent: verify the UI state only) | U, D |
| H9 | `+` menu | Opens. Esc or an outside click closes it. Every item works: pet switch, Quick actions, Command palette, Dictate, Settings. | U |
| H10 | Min / Max / Close | See L5, L10 | U |

## 6. Chat

| ID | Element | Expected | Verify |
|---|---|---|---|
| CH1 | Empty state | Pip hero, greeting with `personality.yaml` `user.name`, 4 chips, hotkey hint | S |
| CH2 | Each chip (4) | Prefills the composer with its text and focuses it. Nothing is sent until Enter. | U, D |
| CH3 | Composer | Enter sends. Shift+Enter makes a new line. Empty input does not send. The send button works. Long text grows to a max height, then scrolls. | U |
| CH4 | Assistant reply | Pip avatar, name, time, plain text. A long reply wraps with no horizontal overflow. | S |
| CH5 | Approval card in chat | Friendly title, risk shown once, mono target chip. Allow, Deny and (hook) Always work. The card disappears when answered from the pet or island. | U, D |
| CH6 | Jump-to-latest button | Appears when scrolled up and scrolls to the bottom | U |
| CH7 | Offline | Banner with countdown. **Retry now** reconnects. Sending while offline queues the message and delivers it on reconnect. | P, U, S |

## 7. Activity, Memory, Settings, About, Onboarding

| ID | Element | Expected | Verify |
|---|---|---|---|
| A1 | Activity task cards | One card per request, status dot, step rows in plain words, no raw tool names | S, D |
| A2 | Timer pills | Live countdown. Cancel removes the timer and stops the backend task. | U, D |
| A3 | Clear | Clears the list and shows the empty state | U |
| M1 | Search and the 6 category chips | Filter live. "No matching memories" when nothing matches. | U, D |
| M2 | Add Fact | Opens the form. Save adds the fact. Cancel closes the form. An empty fact is rejected. | U, D |
| M3 | Edit | Pencil (hover or keyboard focus) gives inline edit. Enter saves, Esc cancels. "· edited" appears. | U, D |
| M4 | Forget + Undo | Forget removes the fact. The toast's Undo restores it. | U, D |
| M5 | Export / Clear all | Export downloads a JSON file. Clear all asks for confirmation, then empties the list. | U |
| M6 | Loading / offline | "Loading memories…" / "Memory is offline" until the store answers | D, S |
| S1 | Settings index (9 entries) | Each shows only its own section | U, S |
| S2 | Model card | Provider seg (LM Studio/OpenAI/Claude), auto-routing switch, URL, key reveal (keyboard reachable), Test connection result card. Cloud key → "Saved in Windows Credential Manager". Forget key works. | U, D, P (cmdkey /list) |
| S3 | Voice cards | Wake switch + threshold + Test, mic device select + AGC/gate, hotkeys fields, TTS engine/voice/speed + Test, UI sounds, Launch at login | U, D |
| S4 | Character & Desktop | Pet enabled, companion seg Pet/Dock (applies live), render seg 2D/3D (applies live), colorway select, Identity fields | U, S |
| S5 | Privacy & Safety | Approval mode select, approval timeout | U, D |
| S6 | Performance | Live model memory status, Advanced fields | D |
| S7 | Dictionary | Add row, edit, Save; does not dirty the main Save | U, D |
| S8 | Dictation History | Refresh lists the latest entries | U |
| S9 | Integrations | Install/Remove hook for Claude Code and Antigravity (backup made), relay status | U, P (file diff) |
| S10 | Save changes | Disabled until dirty. Saves and shows "Saved". Persists across restart (L2). | U, P |
| AB1 | About | Version = `tauri.conf.json` version, backend status | D, S |
| AB2 | Export diagnostics / Show in folder | Zip created in `%APPDATA%\JarvisDesktopPet\diagnostics` with no keys inside. Explorer opens on it. | P, U |
| O1–O3 | Onboarding: Meet Pip → Microphone → Model | Each step is one card with one white-pill action. Back/Next work. Finish persists and the sheet never returns on relaunch. Test buttons work. | U, S, P |

## 8. Pet, island, dock

| ID | Element | Expected | Verify |
|---|---|---|---|
| P1 | Pip idle / hover / speech / sleep / approval | Correct mood and art in 2D and 3D | S |
| P2 | Drag | Moves the window. A click after a drag does not open chat. | U |
| P3 | Hover dock (5 buttons) | Mic, Chat (C6), Dock mode (switches to island and persists), 2D/3D toggle (persists), Settings (C7) | U, D |
| P4 | Right-click | Compact menu (if present), or nothing; never a browser context menu | U, S |
| P5 | Approval card fallback (pet mode) | Allow/Deny work. Hidden while the island is the companion. | U, D |
| P6 | File drop | Gulp, then chat prefill (C12) | U |
| I1 | Island: hidden strip / compact / hover expand | 240×6 → 240×36 → 460×auto; hover peeks it open | U, S |
| I2 | Tabs Home/Chat/+ | Switch views. + starts a fresh inline chat. | U |
| I3 | Overview buttons | Talk, Workspace (C8), Switch to pet | U, P |
| I4 | Approval card | Allow/Deny/Always and Y/N keys | U, D |
| I5 | Result / Error / Question / Chat cards | Every button behaves as in spec 34 §3 | U, D |
| I6 | Drop | Swell, then catch, then ingest | U, S |

## 9. Keyboard and global hotkeys

| ID | Keys | Expected | Verify |
|---|---|---|---|
| K1 | Ctrl+Alt+J (anywhere) | Push-to-talk toggles; the voice state is shown on all surfaces | U (SendInput), D |
| K2 | Ctrl+Alt+D | Dictation starts and stops | U, D |
| K3 | Tab order in each pane | Every action is reachable, with a visible focus ring, in a logical order | U, S |
| K4 | Esc | Closes the palette, `+` menu, inline edit, island card | U |

## 10. Offline / reconnect

| ID | Steps | Expected | Verify |
|---|---|---|---|
| R1 | Kill the backend while the UI is up | The main banner counts down, the island headline counts down, the pet bubble shows it, Memory shows offline | S, D |
| R2 | Retry now | Reconnects immediately once the backend is back | U, D |
| R3 | Backend back on its own | Everything goes green again. No duplicate messages. The earcon plays once. | D |

## 11. Visual checklist (per pane, at 1100×760 and 760×560)

For Chat (empty and with messages), Activity, Memory, every Settings section, About, Onboarding steps 1–3, the `+` menu, the command palette, the offline banner, pet 2D/3D, and every island card:

- **Spacing:** 720px content column centred, consistent card padding (18–20px), no element touching the edge.
- **Borders:** only the hairline; no stray white or bright borders, no doubled borders.
- **Alignment:** titles, cards and action rows aligned to the same column; buttons vertically centred.
- **Overflow:** no horizontal scrollbar at 760×560; long text truncates with an ellipsis or wraps; nothing is clipped (the earlier approval-chip bug).
- **Focus:** a visible ring on every focused control.
- **Contrast:** dim text readable (AA).
- **Background:** black chrome, `--card` surfaces; no white flash on open.

Each pane gets a screenshot at both sizes: `artifacts/qa35/visual/<pane>-<w>x<h>.png`.

## 12. Results (executed 2026-11-03, installed build in `test_install`)

Build: `revamp/spec34` + the fixes below, deployed as `test_install\JarvisDesktopPet.exe` with a fresh PyInstaller `jarvis-backend.exe` sidecar. Before the fix, the user's previous build (backed up as `*.bak-20261101`) reproduced the bugs: **B3** a second launch gave 2 UIs and 4 backend processes; **B1** ending the UI left all backend processes and :8765 alive; **B2** the titlebar ✕ called `appWindow.close()`, which destroyed the main window (its CDP target vanished), so every "open chat" path had no window left to show.

Fixes: `e767cd7` (single instance on 127.0.0.1:47823; ✕ hides via Rust instead of destroying; Quit/Exit end the whole backend tree with `taskkill /T`; the backend exits when `JARVIS_PARENT_PID` dies; the reopen brings the window to the front), `8dba260` (Settings "Keep running in the tray when closed", About → Quit Jarvis, the close hint goes in the pet bubble or island instead of a toast over the pet), and the visual-pass commit (a scroll fade plus wheel on the narrow Settings strip, and a sticky section list when wide).

Drivers: `scripts/qa35_lifecycle.py` (processes, ports, Win32 window state, physical clicks) and `scripts/qa35_surfaces.py` (physical mouse and `SendInput` keys; CDP :9335 only to read state and rects; `%APPDATA%\JarvisDesktopPet` backed up and restored). Screenshots and the raw `*_results.json` are under `jarvis-desktop-pet/artifacts/qa35/` **on the test PC only**. They are not committed, because they show local chat text, paths and devices.

### 12.1 Lifecycle and the reported bugs (19/19 PASS)

| Case | Result | Evidence | Screenshot |
|---|---|---|---|
| L2 launch: one UI, backend sidecar up, :8765 listening | PASS | (['JarvisDesktopPet:16592'], ['jarvis-backend:5028', 'jarvis-backend:21760']) | qa35/L2_launch.png |
| L3 (B3) second launch: no duplicate UI or backend | PASS | (['JarvisDesktopPet:16592'], ['jarvis-backend:5028', 'jarvis-backend:21760'], ['JarvisDesktopPet:16592'], ['ja |  |
| L3 second launch: existing main window shown | PASS | {'exists': True, 'visible': True, 'minimized': False, 'foreground': True, 'zoomed': False} |  |
| L5 close button hides the main window (not destroyed) | PASS | {'exists': True, 'visible': False, 'minimized': False, 'foreground': False, 'zoomed': False} |  |
| L5 after close: UI + backend keep running (tray mode) | PASS | (['JarvisDesktopPet:16592'], ['jarvis-backend:5028', 'jarvis-backend:21760']) |  |
| B2 root cause: main webview still alive after close | PASS |  |  |
| C5 (B2) pet click reopens the chat window on Chat | PASS | ({'exists': True, 'visible': True, 'minimized': False, 'foreground': True, 'zoomed': False}, 'chat') | qa35/C5_pet_click_reopens.png |
| C6 (B2) pet dock Chat button reopens chat | PASS | {'exists': True, 'visible': True, 'minimized': False, 'foreground': True, 'zoomed': False} |  |
| C7 pet dock Settings opens Settings | PASS | ({'exists': True, 'visible': True, 'minimized': False, 'foreground': True, 'zoomed': False}, 'settings') |  |
| L4 (B3) launch while closed to tray: shows existing window, no duplicate | PASS | ({'exists': True, 'visible': True, 'minimized': False, 'foreground': True, 'zoomed': False}, ['JarvisDesktopPe |  |
| L10 minimize button minimizes | PASS | {'exists': True, 'visible': True, 'minimized': True, 'foreground': False, 'zoomed': False} |  |
| C5 (B2) pet click restores a minimized window | PASS | {'exists': True, 'visible': True, 'minimized': False, 'foreground': True, 'zoomed': False} | qa35/C5_pet_click_reopens.png |
| L10 maximize then restore | PASS | (True, False) |  |
| C8 (B2) island Workspace button reopens chat | PASS | {'exists': True, 'visible': True, 'minimized': False, 'foreground': True, 'zoomed': False} |  |
| L5b close with 'keep running in tray' off quits UI + backend | PASS | ([], []) |  |
| L6 (B1) Quit ends the UI and every backend process, :8765 freed | PASS | ([], []) |  |
| L8 UI killed -> backend exits on its own (no orphan) | PASS | ([], []) |  |
| L11 --hidden launch: main hidden, pet shown, one UI | PASS | ({'exists': True, 'visible': False, 'minimized': False, 'foreground': False, 'zoomed': False}, ['JarvisDesktop |  |
| L9 backend crash -> offline banner with countdown | PASS | {"b":true,"t":"Reconnecting in 2s…"} | qa35/L9_backend_down.png |

### 12.2 Surfaces, keyboard and visual pass (84 PASS, 0 FAIL, 4 N/A)

| Case | Result | Evidence | Screenshot |
|---|---|---|---|
| O1 onboarding step 1 is 'Meet Pip' | PASS | Meet Pip | qa35/O1_meet_pip.png |
| O2 Next goes to Microphone | PASS | 2 | qa35/O2_microphone.png |
| O3 Next goes to Model | PASS | 3 | qa35/O3_model.png |
| O3 Back returns to step 2 | PASS | 2 | qa35/O3_model.png |
| H tab activity switches pane + aria-current | PASS | ('activity', True) |  |
| H tab memory switches pane + aria-current | PASS | ('memory', True) |  |
| H tab settings switches pane + aria-current | PASS | ('settings', True) |  |
| H tab chat switches pane + aria-current | PASS | ('chat', True) |  |
| H9 + menu opens, Esc closes | PASS | (True, True) |  |
| H9 + menu Settings item opens Settings | PASS |  |  |
| H9 + menu pet switch hides then shows the pet | PASS | (True, True) |  |
| H7 command palette opens focused, Esc closes | PASS | ('cmd-palette-input', True) |  |
| H6 provider pill shows provider | PASS |  Local Model · Auto |  |
| CH1 empty state with Pip hero on a fresh start | PASS | True | qa35/CH1_empty_state.png |
| CH2 chip 1 prefills composer (not sent) | PASS | Help me open an app  |  |
| CH2 chip 2 prefills composer (not sent) | PASS | Help me find a file on this PC  |  |
| CH2 chip 3 prefills composer (not sent) | PASS | Summarize what is on my screen  |  |
| CH2 chip 4 prefills composer (not sent) | PASS | Run this routine for me:  |  |
| CH3 Shift+Enter makes a new line | PASS | 'hello pip\nsecond line' |  |
| CH3 Enter on empty composer sends nothing | PASS | 0 |  |
| CH3 Enter sends the message | PASS | 1 |  |
| CH4 assistant reply rendered | PASS | 2 | qa35/CH4_reply.png |
| CH5 approval card appears in chat | PASS | Delete qa35_probe.txt Jarvis wants to do this · High risk qa35_probe.txt Nothing happens on your computer unti | qa35/CH5_approval_card.png |
| CH5 approval card has no raw tool names | PASS | Delete qa35_probe.txt Jarvis wants to do this · High risk qa35_probe.txt Nothing happens on your computer unti | qa35/CH5_approval_card.png |
| CH5 Deny keeps the file | PASS | True | qa35/CH5_approval_card.png |
| A1 activity has task cards | PASS | TODAY Jarvis replied Done 03:53 03:53 Jarvis replied Action denied. No changes made. delete the file qa35_prob | qa35/A1_activity.png |
| A1 no raw tool names in Activity | PASS | [] | qa35/A1_activity.png |
| A2 timer pill with countdown appears | PASS | 1 | qa35/A2_timer.png |
| A2 Cancel removes the timer | PASS | (1, 0) | qa35/A2_timer.png |
| A3 Clear empties Activity | PASS | No activity yet  Actions Jarvis takes — requests, approvals, completed work — wi |  |
| M2 Add Fact saves a fact | PASS | True |  |
| M1 search filters live | PASS | 1 |  |
| M3 inline edit saves with Enter and marks edited | PASS | qa35 favourite colour is amber / 03:54 AM · edited | qa35/M3_memory_edit.png |
| M4 Forget removes, Undo restores | PASS | (0, 1) |  |
| M1 category chips switch | PASS | all |  |
| M5 Clear all | N/A | not clicked: would wipe the user's real memories |  |
| S1 sec-models shows only its section | PASS | ['sec-models'] |  |
| S1 sec-voice shows only its section | PASS | ['sec-voice'] |  |
| S1 sec-assistant shows only its section | PASS | ['sec-assistant'] |  |
| S1 sec-safety shows only its section | PASS | ['sec-safety'] |  |
| S1 sec-performance shows only its section | PASS | ['sec-performance'] |  |
| S1 sec-dictionary shows only its section | PASS | ['sec-dictionary'] |  |
| S1 sec-history shows only its section | PASS | ['sec-history'] |  |
| S1 sec-integrations shows only its section | PASS | ['sec-integrations'] |  |
| S1 sec-about shows only its section | PASS | ['sec-about'] |  |
| S2 provider seg openai | PASS | openai | qa35/S2_model.png |
| S2 provider seg anthropic | PASS | anthropic | qa35/S2_model.png |
| S2 provider seg lm_studio | PASS | lm_studio | qa35/S2_model.png |
| S2 key reveal toggles visibility | PASS | ('password', 'text') | qa35/S2_model.png |
| S2 Test connection shows a result card | PASS | LM Studio connection failed Connection error. | qa35/S2_model.png |
| S4 companion seg switches pet <-> island live | PASS | (True, True) |  |
| S4 render seg 3D then 2D applies to the pet | PASS | (True, True) |  |
| S10 Save enables when dirty and saves | PASS | (True, False, 'Saved.') |  |
| S7 dictionary Add row | PASS | (4, 5) |  |
| S8 history refresh clickable | PASS |  |  |
| S9 Integrations install/remove | N/A | not clicked: edits the user's real ~/.claude + agy configs; hook_e2e covers it with backups |  |
| S3 wake test / mic test | N/A | needs a live microphone |  |
| AB1 About shows the version | PASS | v0.1.0 | qa35/AB_about.png |
| AB2 Export diagnostics writes a zip | PASS | Saved to %APPDATA%\JarvisDesktopPet\diagnostics\pulseai-diagnostics-20261103-035541.zip | qa35/AB_about.png |
| K3 Tab moves focus with a visible ring | PASS | ('mic', 'solid 2px') |  |
| P4 right-click menu | N/A | not implemented in this build (spec 34 section 5 lists it as Phase 4+ pet simplification) |  |
| I1 hover expands the island | PASS | True |  |
| I2 island Chat tab shows the chat card | PASS | chat |  |
| I5 island inline chat sends | PASS | set a timer for 9 minutes Timer set for 9 minutes timer. hi from the island | qa35/I5_island_chat.png |
| V overflow-free chat-1100x760 | PASS | False | qa35/visual/chat-1100x760.png |
| V overflow-free activity-1100x760 | PASS | False | qa35/visual/activity-1100x760.png |
| V overflow-free memory-1100x760 | PASS | False | qa35/visual/memory-1100x760.png |
| V overflow-free settings-sec-models-1100x760 | PASS | False | qa35/visual/settings-sec-models-1100x760.png |
| V overflow-free settings-sec-voice-1100x760 | PASS | False | qa35/visual/settings-sec-voice-1100x760.png |
| V overflow-free settings-sec-assistant-1100x760 | PASS | False | qa35/visual/settings-sec-assistant-1100x760.png |
| V overflow-free settings-sec-safety-1100x760 | PASS | False | qa35/visual/settings-sec-safety-1100x760.png |
| V overflow-free settings-sec-performance-1100x760 | PASS | False | qa35/visual/settings-sec-performance-1100x760.png |
| V overflow-free settings-sec-dictionary-1100x760 | PASS | False | qa35/visual/settings-sec-dictionary-1100x760.png |
| V overflow-free settings-sec-history-1100x760 | PASS | False | qa35/visual/settings-sec-history-1100x760.png |
| V overflow-free settings-sec-integrations-1100x760 | PASS | False | qa35/visual/settings-sec-integrations-1100x760.png |
| V overflow-free settings-sec-about-1100x760 | PASS | False | qa35/visual/settings-sec-about-1100x760.png |
| V overflow-free chat-760x560 | PASS | False | qa35/visual/chat-760x560.png |
| V overflow-free activity-760x560 | PASS | False | qa35/visual/activity-760x560.png |
| V overflow-free memory-760x560 | PASS | False | qa35/visual/memory-760x560.png |
| V overflow-free settings-sec-models-760x560 | PASS | False | qa35/visual/settings-sec-models-760x560.png |
| V overflow-free settings-sec-voice-760x560 | PASS | False | qa35/visual/settings-sec-voice-760x560.png |
| V overflow-free settings-sec-assistant-760x560 | PASS | False | qa35/visual/settings-sec-assistant-760x560.png |
| V overflow-free settings-sec-safety-760x560 | PASS | False | qa35/visual/settings-sec-safety-760x560.png |
| V overflow-free settings-sec-performance-760x560 | PASS | False | qa35/visual/settings-sec-performance-760x560.png |
| V overflow-free settings-sec-dictionary-760x560 | PASS | False | qa35/visual/settings-sec-dictionary-760x560.png |
| V overflow-free settings-sec-history-760x560 | PASS | False | qa35/visual/settings-sec-history-760x560.png |
| V overflow-free settings-sec-integrations-760x560 | PASS | False | qa35/visual/settings-sec-integrations-760x560.png |
| V overflow-free settings-sec-about-760x560 | PASS | False | qa35/visual/settings-sec-about-760x560.png |

### 12.3 Failures found during the run and what happened
- **First-close Windows toast covered the pet** (C5 failed on the first lifecycle run: the click landed on the toast). Fixed in `8dba260`; the hint now goes in Pip's bubble or the island headline.
- **Narrow Settings (760×560): the section strip ran off the right edge with no sign it scrolls** (9 visual FAILs). Fixed: an edge fade on whichever side has hidden tabs, wheel-to-scroll, and the active tab kept in view. The overflow check now ignores content inside a horizontal scroller.
- **Wide Settings: the section list scrolled away under the header on long sections.** Fixed with a sticky list.
- Test-side issues, not app bugs: the `+` menu pet switch is a styled label (the hidden checkbox has no box to click), so the driver now clicks the slider; the 2D render button sat under the sticky Save bar at the bottom edge, so the driver now scrolls controls into view first, like a user; and S10 started dirty from the earlier live controls, so the driver now saves first.

### 12.4 Not covered by automation (honest gaps)
- **Tray menu clicks (C1–C4, L6 via tray).** The tray uses the same Rust functions as the tested paths (`open_main_tab`, `quit_app`); Quit was verified through About → Quit Jarvis and through close with "keep running" off. A manual tray click is still worth one try.
- **Mic-dependent:** global hotkeys K1/K2 with real audio, wake test and mic test (S3), `hotkey_e2e`, `dictation_flow_test`.
- **Not clicked to protect real data:** Memory → Clear all (M5) and Integrations hook install/remove (S9; covered by `hook_e2e` with backups).
- **P4 pet right-click menu:** not implemented in this build.

Non-mic gates after the fixes: smoke, ws_ping, a11y 31/31, credentials 19/19, perf 5/5, memory_update 14/14, model_router 30/30, fast_router 71/71, vocab 17/17, audio_cache, tts_wake, injector 17/17, hook_e2e 37/37, dictation_ui 27/27, phase5_e2e 14/14, phase5_dock 27/27, phase5_visual 28/28, chat_e2e, agent_e2e, voice_e2e ALL OK, pet_springs 9/9, inspect_states 46/46; wake_e2e PASS, then the known teardown crash.
