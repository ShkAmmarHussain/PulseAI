# 35. Full QA test plan (real Windows build, end to end)

Status: **plan written 2026-11-01; not yet executed.** Results are filled in, with evidence, in §12 once the run happens.

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

## 12. Results

To be filled in during execution. Columns: ID · result (PASS / FAIL → fixed in `<commit>` / N/A with reason) · evidence (screenshot path, process dump, log line).

Execution order:
1. Reproduce B1–B3 on the current build and record the evidence.
2. Root-cause and fix B1–B3.
3. Run §3–§10 on the rebuilt `test_install`.
4. Run the §11 visual pass.
5. Fix every failure.
6. Re-run the failed cases and the non-mic gates.
7. Push.
