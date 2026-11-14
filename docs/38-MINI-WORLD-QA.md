# 38. Mini World: QA results (Sprint 8)

Release pass for the Mini World (docs 36 and 37). Everything below was run on the dev machine on 2026-11-14, against the real backend and LM Studio unless the row says otherwise.

## What changed for release

- **On by default.** `world.enabled: true` in the shipped `config.yaml`, and `world_enabled()` treats a missing key as on, so existing installs get the World tab too. An explicit `enabled: false` (or env `PULSEAI_WORLD=0`) turns it off. The World tab has the live on/off switch, and onboarding step 4 sets it.
- **World tab is home** when the world is on: the window lands there unless the URL asks for another tab.
- **Skills in the packaged app.** A frozen build has no separate `python.exe`, so skills run as `backend.exe --run-skill` in a throwaway folder (`skills_lab.skill_command`). Dev builds still use `python -I runner.py`.
- **The old pipeline stays, as the "off" path.** Doc 36 §17 planned to remove it in M6. Because the World tab has an off switch and the off path must keep working (tested below), it is kept rather than deleted. The fast-path router still runs first in both modes.

## Automated results

| Suite | Result |
|---|---|
| `world_state_test` | 11/11 |
| `world_plan_test` | 13/13 |
| `world_brain_test` | 15/15 |
| `world_runtime_test` (incl. building growth) | 24/24 |
| `world_director_test` | 25/25 |
| `world_thinker_test` (thinker, workers, reporter) | 33/33 |
| `world_team_test` | 18/18 |
| `world_service_test` (approvals, flag, commands) | 26/26 |
| `world_agents_test` (create, keep, edit, delete, restore, restart) | 26/26 |
| `world_skills_test` (AST check, sandbox, frozen entry, review flow) | 35/35 |
| `world_store_test.mjs` / `world_looks_test.mjs` | 15/15, 8/8 |
| `world_backend_e2e` (on, off, live toggle on the real backend) | 17/17 |
| `world_live_test` (LM Studio: question, multi-step plan) | 2/2 |
| Existing suites: `model_router`, `vocab`, `injector`, `smoke`, `pet_springs`, `a11y_check` | 30/30, 17/17, 17/17, OK, 9/9, 31/31 |

`injector_test` failed once (16/17) in the Sprint 5 run and passed on rerun. It drives the real clipboard and focus, and nothing in the Mini World touches it.

## Manual checks in the browser (real backend + LM Studio)

| Check | Result |
|---|---|
| World tab loads with the 8 regulars at their desks, 1440 px and 880 px wide | Pass |
| Multi-step request: Thinker plans, Rhea searches, a temp Writer is made, walks in, rides the lift and leaves | Pass |
| `run: dir` raises Otto's hand and the approval card; Deny is respected and the card clears everywhere | Pass |
| New agent form (Translator preset) creates Wren in a spare room; Reroll changes the chibi; Delete then Bring back works | Pass |
| Skills: a real model drafts `convert_temperature`, it passes check + test, is turned on, and the team answers "100 °C = 212 °F" with it | Pass |
| 29 agents: the building grows to 4 floors, floor buttons and camera follow | Pass |
| Day/night toggle | Pass |
| Default landing on the World tab with the shipped config | Pass |

## Installed-build pass (click by click), 2026-11-14

A fresh `jarvis-backend.exe`, `pulseai-skill-runner.exe` and `JarvisDesktopPet.exe` were deployed to `test_install`. All input is physical mouse and keyboard (SendInput), with `%APPDATA%\JarvisDesktopPet` backed up and restored.

| Driver | Final result |
|---|---|
| `scripts/qa35_lifecycle.py` (launch, single instance, close vs quit, reopen paths, crash handling) | 19/19, twice in a row |
| `scripts/qa35_surfaces.py` (every surface + onboarding step 4) | 85/85 (4 N/A by design: real memories, real ~/.claude, live microphone, an unbuilt menu) |
| `scripts/qa38_world.py` (World tab, new) | 44/44 |

`qa38_world` covers:
- W1: opening on the World tab with the 8 regulars and the 3D view.
- W2: roster selection and Find.
- W3: every floor button.
- W4: day and night, and Home.
- W5–W7: new agent, reroll, edit, delete with confirm, Recently deleted, Bring back.
- W8: approval card and Deny.
- W9: a rule job end to end.
- W10: Stop all on a running model job.
- W11: Bodie drafts a skill with the real model. The skill passes the check and its sandbox test inside the packaged app, is turned on, its example runs (32.0) and it is deleted.
- W12: power off and on without a restart.
- W13: the 880 px layout.
- W14: every other tab still opens.

### Bugs found and fixed in this pass

1. **Skills timed out in the installed app.** The packaged child started with no `TEMP`, so the PyInstaller bootloader could not unpack and hung. In addition, the 190 MB backend exe was slow to start as a sandbox. Fix: a separate 9 MB `pulseai-skill-runner.exe` (`skill-runner.spec`, shipped as a Tauri `externalBin`) that starts in about 0.75 s, with `TEMP`/`TMP` pointed at the throwaway folder. The backend's `--run-skill` stays as a fallback with a 90 s timeout.
2. **A late "world is on" message could pull you out of Settings.** When the backend started slowly, the World tab's one-time landing ran after the user had already moved to another tab. It now only lands while the window is still on its untouched start tab, within the first 20 s.
3. **The World tab had no way to turn the world off**, even though the README said it did. Added a power button to the toolbar.
4. Test drivers: the docs/35 driver crashed printing "→" on a cp1252 console, and L6 clicked Quit while another window was on top (Windows refused the focus change). Both are fixed in the drivers.

## Not covered here

- Animation while the window is hidden is paused on purpose, so a hidden window shows agents where they were.
