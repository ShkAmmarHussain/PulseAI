# 14. SAFETY & GUARDRAILS

Defense-in-depth: Approval layer + Safety Agent (parallel veto) + whitelists + risk scoring.

## 14.1 Risk Scoring (0–10)
| Risk | Score | Gate |
|---|---|---|
| Read-only | 0–1 | Auto |
| Info/query | 1–2 | Auto |
| Open app | 2–3 | Auto (common) |
| File write/move | 4–5 | May ask |
| Mouse/kb | 6–7 | Require approval (default) |
| Shell/CLI | 6–8 | Approval + allowlist |
| Destructive (delete/overwrite) | 8–10 | Require explicit approval |

## 14.2 Gates
- Pre-exec validation (Tool_Control)
- Parallel veto (Safety Agent, independent)
- Human-in-loop (Approval UI)
- Whitelist/Session grants
- Kill switch, circuit breaker

## 14.3 Trust Model
Conservative default → build session trust (time/app-scoped grants). Revocable anytime.

## 14.4 Audit
All actions logged (timestamp, agent, skill, params, decision, result). Tamper-friendly append log.
