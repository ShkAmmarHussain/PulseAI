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

## Not covered here

- A full installed-build pass (doc 35 driver) with the new tab. Run `scripts/qa35_surfaces.py` after the next `build.bat`.
- `--run-skill` was verified through `backend/main.py` in dev. The real frozen exe still needs one check after a build.
- Animation while the window is hidden is paused on purpose, so a hidden window shows agents where they were.
