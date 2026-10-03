# 13. PC CONTROL

Safe desktop automation: apps, files, mouse/kb, shell, browser.

## 13.1 Principles
Least privilege, explicit approval (default), session grants, whitelist, read-only by default, reversible where possible.

## 13.2 Capabilities
App control, file ops (with backups/trash), input_control (L3), shell (allowlist), browser, window mgmt.

## 13.3 Safety Per Action
input_control/shell = High → require approval unless session_grant + whitelist. Destructive (delete/overwrite) → confirm.

## 13.4 Guardrails
Path allowlists, realpath, no traversal, command allowlist, timeout, cwd restricted, rate limits.

## 13.5 Approval UX
Pet bubble (Approval UI), timeout (30–60s), Allow Once/Allow Session/Deny/Always Deny.

## 13.6 Verification
Post-action verify (window exists, file changed, state matches) via Vision/Checks.
