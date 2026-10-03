# Jarvis Desktop UI Revamp

> Product and implementation brief for modernizing the existing Jarvis Desktop Pet interface. This document combines the direction from the **Modernize Assistant UI** chat with the current Tauri app, frontend, and product goals in this repository.

## 1. Product intent

Jarvis should feel like a capable, private desktop companion: calm and approachable while idle, clear and trustworthy while doing work, and always easy to reach. The redesign should make the existing app feel like one coherent product across its main window, floating pet, voice interactions, settings, and approval prompts.

The reference chat recommends a minimal glowing assistant core instead of a toy-like pet. The project’s established product direction is explicitly pet-first, with a living character that communicates mood and state. Combine these by keeping Jarvis recognizable as a companion while simplifying its presentation: make the existing 3D pet the expressive core, framed by restrained interface chrome. Do not replace it with an unrelated static orb or remove its character.

### Design principles

- **Companion first, interface second:** Jarvis remains present and expressive without dominating every screen.
- **Quiet by default, clear under activity:** use color, motion, and text to communicate listening, thinking, speaking, working, success, and errors.
- **Trust through visibility:** show what the assistant is doing and why an action needs approval; make allow and deny choices obvious.
- **Local-first confidence:** expose connection and microphone state plainly, without implying cloud processing.
- **Useful before decorative:** prioritize the composer, conversation, action feedback, and settings hierarchy over ornamental effects.
- **One visual system:** the main window, pet overlay, approval cards, and settings should share tokens and component behavior.

## 2. Current product and UI baseline

The app is a Windows desktop assistant built with Tauri, a plain HTML/CSS/JavaScript frontend, and a local Python backend connected over WebSocket. The current main window is configured at 780 × 580 px with a 560 × 420 px minimum. A separate transparent, always-on-top pet window is 300 × 240 px. A system tray can also show or hide the pet.

The main window currently has two tabs: **Chat** and **Settings**. Chat has a centered greeting, message list, text input, microphone toggle, send button, typing indicator, connection status, and approval cards with Allow/Deny. The pet window has the 3D character, a speech bubble, mic/chat/settings controls, and an approval surface. Settings currently place voice, pet/personality, LM Studio, model-role mapping, safety, and resource-manager controls into one long scrolling pane. Existing voice controls include wake-word enablement, microphone selection and input meter, auto gain, noise gate, wake-word testing and threshold, TTS engine/voice/speed, and preview playback.

The UI already uses a dark palette, violet/blue gradients, rounded controls, a draggable top bar, and WebSocket-driven voice and chat states. Treat these behaviors and the two-window/tray model as the baseline to refine. Keep backend message names, settings serialization, safety gates, Tauri window behavior, and local processing semantics intact while changing presentation.

## 3. Information architecture

### Main window

Use a persistent compact navigation rail or header with three destinations:

1. **Chat** — conversation, task progress, approvals, and input.
2. **Activity** — recent actions and their outcomes, shown only if the backend can provide reliable history. If history is not available, keep activity inline in Chat and defer this destination.
3. **Settings** — organized configuration and diagnostics.

The existing Chat and Settings routes must remain available. Avoid adding a tab that merely duplicates the floating pet’s controls.

### Floating pet

Keep the transparent, always-on-top companion window. It remains the fast path to voice, chat, settings, and in-context approvals. Its controls should be discoverable on hover/focus and visible during active states. The main-window pet visibility control and tray action must continue to reflect the same authoritative setting.

### Settings sections

Use a left-side settings index on wide layouts and a compact section selector on narrower layouts:

- Voice
- Assistant & pet
- Models & connection
- Safety & permissions
- Performance

Move existing fields into these groups; do not silently drop or rename persisted configuration keys. Place model IDs and millisecond tuning values under an **Advanced** disclosure within their relevant section. Keep connection tests and voice preview near their settings, with feedback adjacent to the action.

## 4. Main window layout

### Recommended frame

- Target initial size: **1100 × 760 px**; maintain a useful minimum around **760 × 560 px** after checking the actual layout.
- Header: **60 px** high, with **20–24 px** horizontal padding.
- Main content max width: **820 px** for the chat reading column.
- Main content inset: **24–32 px** on desktop; reduce to **16 px** on compact widths.
- Composer: anchored to the bottom of the Chat pane, within the content column.
- Scrolling belongs to the message/history region and settings content, not the entire app shell.

The current 560 × 420 minimum is too small for the proposed hierarchy. If preserving it is important for small displays, define a compact layout at that size: collapse navigation labels, hide nonessential helper copy, keep the composer and primary actions visible, and allow settings to scroll. The Tauri minimum-size change should be coordinated with the implementation rather than assumed.

### Header

- Left: Jarvis mark/name and a small, textual local-service connection state.
- Center or left-aligned after brand: Chat, Activity (if supported), Settings navigation.
- Right: pet visibility control and a restrained window utility/action area.
- Keep the existing draggable header behavior, but ensure interactive controls remain non-draggable.
- Use a status dot plus label; do not communicate connection solely through green/red color.

### Chat idle state

Use a centered, balanced welcome area that yields space when the first message arrives:

1. Medium-sized animated pet/core (approximately **120–160 px** visual footprint).
2. Headline: **“How can I help?”**
3. Short local-first hint: **“Type a request or talk to Jarvis.”**
4. Three or four contextual action chips, for example **Open an app**, **Find a file**, **Summarize my screen**, and **Run a routine**. Show only actions that are actually available; otherwise treat them as prompt suggestions and do not imply an integration is connected.
5. Composer anchored at the bottom.

The existing wake-word hint can be retained as secondary copy or a small help affordance. Avoid repeated prompts that compete with the input.

### Conversation state

- Keep messages in a centered reading column of **680–820 px**.
- Use clear speaker labels and restrained assistant identity; avoid oversized avatars on every response.
- Render assistant text with readable line length, selectable text, and appropriate paragraph spacing.
- Distinguish user and assistant messages with alignment and surface tone. Avoid using a saturated gradient for every user message; reserve gradients for emphasis and active states.
- Keep system events, progress, approvals, and errors visually distinct from conversational replies.
- Preserve scroll-to-latest for new output while allowing the user to scroll upward without the view forcibly jumping on every update.
- Support Enter to send and Shift+Enter for a newline if the composer becomes multiline.

### Composer

- Full content-column width; **60–68 px** minimum height, **18–22 px** radius.
- Multiline text area that grows to a small maximum before scrolling internally.
- Leading text field with a concise prompt such as **“Ask Jarvis to do something…”**.
- Trailing microphone button and send button with visible labels/tooltips and clear disabled/active states.
- Listening state: accent outline/glow, explicit **Listening** label nearby, and a stop/cancel affordance.
- Transcribing state: disable duplicate recording and show **Transcribing…**.
- Sending/thinking state: keep the typed request visible in the transcript and show a cancellable state only if cancellation is supported.
- Respect keyboard focus, accessible names, visible focus rings, and reduced-motion preferences.

## 5. Assistant states and feedback

Use a single UI state vocabulary shared across the main window and pet. Map it to existing backend events where available; any state that needs new backend data is a proposed enhancement, not an assumption.

| State | Visual treatment | Copy / feedback |
|---|---|---|
| Idle | Gentle breathing animation; low glow | Ready/connected status remains subtle |
| Listening | Brighter ring or waveform; mic visibly active | “Listening…” with stop control |
| Transcribing | Static, focused accent; no pulsing mic | “Transcribing…” |
| Thinking | Soft shimmer or slow orbit, not rapid spinner | “Thinking…” |
| Working | Pet remains visible but quieter; compact progress card | Describe the current action in plain language when available |
| Speaking | Subtle mouth/light response if supported | “Speaking…” only when it adds clarity |
| Approval needed | Persistent high-contrast approval card | State the exact proposed action and risk context |
| Success | Brief glow/check transition, then return to idle | Show a concise result or confirmation |
| Error / offline | Stable warning/error color and icon | State what failed and a useful next step when known |

Motion should support comprehension. Use roughly **180–260 ms** for ordinary transitions, with slow ambient motion for the pet. Respect `prefers-reduced-motion`; provide a static state with the same meaning. Never rely on animation alone to communicate a state.

## 6. Task progress and results

Represent long-running or multi-step work as compact cards in the conversation flow, close to the triggering request:

- Action title, such as **Searching files** or **Opening the browser**.
- Current progress only when the backend can report it truthfully.
- Completion result, including useful counts or destinations where available.
- Clear failure state and recovery hint when known.
- Avoid fake percentage progress, invented subtasks, or success notifications before tool completion.

For multi-step tasks, group related updates into one expandable card rather than flooding the conversation. Preserve the final assistant response as the user-facing summary. If no progress event exists today, use a truthful generic “Working…” indicator and record richer progress as a future backend/UI integration.

## 7. Approval and safety UX

Approval is a core product surface because PC control is safety-gated. Make approval cards unmistakable in both Chat and the pet bubble:

- Name the requested action in plain language and show the target (app/file/site) when known.
- Explain why confirmation is needed in one short sentence.
- Show risk level as text with a label and optional number; do not rely on a colored badge alone.
- Provide **Allow once** and **Deny** as explicit actions. Preserve existing action payloads and correlation IDs.
- Make Deny equally reachable and visually clear without styling it as the primary choice.
- Show a pending state after selection and a clear outcome when the action proceeds, is denied, or times out.
- On the pet overlay, expand the bubble/card enough to read the action and make both buttons usable; do not compress away context.
- Do not introduce “trust this action/session” controls unless the permission system supports them and clearly scopes the grant.

## 8. Floating pet and compact mode

The separate pet window is already the app’s compact always-on-top mode. Improve the current 300 × 240 presentation without changing its role:

- Keep a transparent canvas and a clear, unclipped pet silhouette.
- Use hover/focus to reveal a small, calm control dock for mic, open chat, and settings.
- Give controls a minimum **36 × 36 px** target where the window permits.
- Keep the speech bubble above or beside the pet, positioned so it does not clip at screen edges; screen-aware placement may require Tauri support.
- During listening or work, expand feedback in the bubble while keeping the character recognizable.
- During approval, prioritize action text and decision controls over decorative pet animation.
- Provide keyboard-accessible controls where the native window focus model allows it.
- Keep show/hide synchronized across the main window toggle, settings, and tray menu.

The main application window may also support a compact resized layout, but avoid adding a separate mode toggle unless it maps to real Tauri window behavior.

## 9. Settings redesign

Replace the long undifferentiated list with grouped sections and consistent rows. Each setting should include a clear label, appropriate control, and brief description only where the label is not self-explanatory.

### Voice

- Always listen for wake word, with a clear microphone-in-use explanation.
- Microphone selector and live input meter, with selected-device name and paused/error state.
- Auto gain and noise gate with concise descriptions.
- Wake-word test and threshold together; explain threshold direction in help text.
- Speech engine, voice, and speed grouped as **Spoken responses**; place Preview Voice beside them.
- Surface mic permission/device failures beside the affected control.

### Assistant & pet

- Show floating pet toggle, with the current visibility reflected from the authoritative app state.
- Assistant name, wake-word label, and voice style.
- Explain that hiding the pet leaves access through the main window and tray, if that remains true.

### Models & connection

- LM Studio endpoint, optional API key, timeout, and **Test connection** action.
- Show test result with an explicit success/failure message and loaded model list when supplied.
- Put role-to-model mapping under an **Advanced model configuration** disclosure.
- Label vision as on-demand where the backend supports that behavior.

### Safety & permissions

- Conservative/Smart policy selector with a plain-language explanation of the implications.
- Approval timeout, with units shown in seconds in the interface and correct conversion to persisted milliseconds.
- Link the setting to how pending approvals are shown and handled.
- Keep safe defaults visible; do not obscure approval behavior in advanced settings.

### Performance

- Resource-manager controls grouped under Advanced, with human-readable units and safe ranges.
- Explain the effect of vision timeout, idle unload, and cooldown in brief help text.
- Avoid presenting internal jargon such as “VRAM” without a short explanation.

### Save and status behavior

- Use a clear **Save changes** action, enabled only when values differ if practical.
- Indicate saving, saved, and failed states near the action.
- Warn before navigating away only if there are unsaved changes and the app can reliably detect them.
- Keep voice controls that intentionally apply immediately distinct from settings that require Save.
- Preserve existing settings keys and defaults unless a separate migration is planned.

## 10. Visual design system

The reference chat’s deep neutral base with violet/blue accents fits the current product and existing frontend. Refine it into a more restrained, accessible system.

### Color tokens

| Token | Value | Use |
|---|---|---|
| `--bg-canvas` | `#090910` | App background |
| `--bg-elevated` | `#10101A` | Header and major regions |
| `--surface-1` | `#151522` | Cards and composer |
| `--surface-2` | `#1C1C2B` | Hover/raised controls |
| `--border-subtle` | `rgba(255,255,255,.08)` | Quiet separators |
| `--border-strong` | `rgba(255,255,255,.14)` | Input and focus-adjacent edges |
| `--text-primary` | `#F4F3FA` | Main text |
| `--text-secondary` | `#B0AEC4` | Supporting text |
| `--text-muted` | `#85839B` | Hints and inactive labels |
| `--accent` | `#9275F5` | Primary accent |
| `--accent-blue` | `#7189F5` | Secondary gradient accent |
| `--accent-soft` | `rgba(146,117,245,.16)` | Selected/active backgrounds |
| `--success` | `#43C995` | Successful status |
| `--warning` | `#F0B94F` | Caution and pending attention |
| `--danger` | `#F07883` | Errors and destructive outcomes |

Use a violet-to-blue gradient sparingly for the primary action, selected navigation, and pet/core lighting. Do not paint large text blocks or every user message with the gradient. Ensure text and controls meet WCAG AA contrast where applicable; verify muted text against the actual dark surfaces.

### Typography

- Prefer the installed Windows UI sans stack, such as **Segoe UI Variable**, with a stable system fallback. Avoid remote font downloads in this local-first app.
- Page title: **28–32 px**, semibold.
- Section title: **18–20 px**, semibold.
- Body and message text: **14–16 px**, regular, with **1.45–1.65** line height.
- Labels: **13–14 px**, medium.
- Helper/status text: **12–13 px**; do not make essential status tiny.
- Use sentence case and reserve all caps for compact, nonessential metadata.

### Spacing, radii, and depth

Use a 4 px base / 8 px primary spacing rhythm:

| Token | Value |
|---|---:|
| `space-1` | 4 px |
| `space-2` | 8 px |
| `space-3` | 12 px |
| `space-4` | 16 px |
| `space-6` | 24 px |
| `space-8` | 32 px |
| `space-10` | 40 px |
| `space-12` | 48 px |

- Cards: **16–20 px** internal padding; section gaps **24–32 px**.
- Controls: **40–48 px** height; primary buttons at least **44 px**.
- Radii: **10 px** small controls, **14–16 px** cards, **20–24 px** hero/composer, pill only for chips and segmented navigation.
- Use soft shadows and faint borders. Use glow only to indicate active assistant states or focused/selected controls.
- Maintain a visible keyboard focus indicator at all times.

### Iconography

Continue the existing rounded line-icon style or adopt one consistent local icon set. Use **18–20 px** for navigation/action icons and **16 px** in compact controls. Pair unfamiliar icons with labels or accessible names.

## 11. Component inventory

Build or refactor the interface around reusable primitives appropriate to the current vanilla frontend:

- `AppShell` / `TopBar`
- `BrandMark` and `ConnectionStatus`
- `PrimaryNavigation` / selected navigation item
- `AssistantPresence` / `PetState`
- `WelcomePanel` and `QuickActionChip`
- `MessageList`, `MessageRow`, `SystemEvent`
- `Composer`, `VoiceButton`, `SendButton`
- `TaskProgressCard` and `ResultCard`
- `ApprovalCard` with pending, approved, denied, and expired states
- `SettingsLayout`, `SettingsSection`, `SettingRow`, `Toggle`, `Select`, `RangeInput`
- `InputLevelMeter`, `InlineFeedback`, `Toast` or inline status region
- `PetControlDock`, `PetSpeechBubble`

Define default, hover, focus, pressed, disabled, loading, active/listening, success, warning, and error states only where each component needs them. Avoid creating variants that the app never uses.

## 12. Responsive behavior

Although the target is desktop, the window is resizable and can be as small as its configured minimum. Define behavior for narrow widths:

- Below **900 px**, reduce outer padding and collapse settings sidebar to a selector or icon rail.
- Below **700 px**, keep navigation compact, stack action chips onto multiple rows, and let the composer occupy the available width.
- At the current 560 px minimum, approval text and Allow/Deny must remain legible and operable; wrap controls rather than clipping them.
- Settings rows should stack labels above controls when horizontal space is insufficient.
- Avoid horizontal scrolling in all normal layouts.
- Keep pet speech bubbles inside available viewport bounds where possible.

## 13. Accessibility and interaction requirements

- All controls must be operable by keyboard and have accessible names.
- Use semantic buttons, labels, headings, and form controls; announce asynchronous status changes in a polite live region where appropriate.
- Do not communicate meaning with color alone.
- Maintain readable contrast, predictable tab order, and clear focus styling.
- Respect reduced-motion preferences and avoid flashing/pulsing at high intensity.
- Keep messages selectable and controls large enough for reliable pointer use.
- Ensure screen-reader users can understand mic state, connection state, progress, approval requests, and save/test results.
- Prevent duplicate sends or voice starts while an operation is already in progress.

## 14. Implementation boundaries and sequencing

This is a UI redesign brief; it does not authorize changes to the agent architecture or permission policy. Preserve the current separation between frontend presentation and backend execution.

### Phase 1 — Visual foundation

- Establish CSS custom properties for color, type, spacing, radius, focus, and motion.
- Refine app shell, navigation, window sizing, background, and responsive behavior.
- Retain the HTML/CSS/JavaScript stack and Tauri packaging model.

### Phase 2 — Chat and pet experience

- Redesign welcome/empty state, transcript, composer, voice status, task feedback, and approval cards.
- Align the main-window companion visuals and floating pet states.
- Preserve WebSocket event names, correlation IDs, tray synchronization, and existing actions.

### Phase 3 — Settings

- Reorganize the existing fields into the proposed groups.
- Preserve serialization/defaults and immediate-apply behavior for wake/device settings.
- Improve validation, units, inline feedback, and advanced disclosures.

### Phase 4 — Optional backend-supported enhancements

- Add richer task progress or activity history only after confirming backend events/data are available.
- Add screen-edge-aware pet/bubble positioning only if supported cleanly by the Tauri window layer.
- Add cancellation only if execution can actually be cancelled safely.

## 15. Acceptance checklist

- [ ] Main window has a coherent Chat/Settings experience at its default size and at the supported minimum.
- [ ] Pet remains a recognizable, expressive companion and stays synchronized with the main-window toggle and tray.
- [ ] Connection, listening, transcribing, thinking, working, success, and error feedback is understandable without relying on color alone.
- [ ] Composer remains accessible and usable during idle, voice, and response states.
- [ ] Approval action, risk context, Allow, and Deny are fully readable and actionable in both the main window and pet overlay.
- [ ] Settings fields are grouped, discoverable, and preserve existing persisted values and backend behavior.
- [ ] Input meters, wake-word tests, LM Studio tests, and TTS preview present clear results and failure states.
- [ ] No UI implies unsupported integrations, fake progress, cloud processing, or unavailable cancellation.
- [ ] Keyboard focus, labels, contrast, reduced motion, and narrow-window behavior are addressed.
- [ ] The interface remains compatible with the current Tauri + vanilla frontend packaging approach.

## 16. Reference and project sources

- Chat: **Modernize Assistant UI** — recommendation for a refined dark desktop assistant, calm violet/blue accents, a clear hero, quick actions, composer, explicit activity states, and organized settings.
- `docs/01-OVERVIEW.md` — local-first, living pet, explainable and safe assistant goals; explicitly pet-first UX.
- `docs/02-ARCHITECTURE.md` — UI/overlay responsibilities, approvals, status, and separation from backend execution.
- `jarvis-desktop-pet/ui_pet/src/index.html` and `app.css` — current main-window structure and visual tokens.
- `jarvis-desktop-pet/ui_pet/src/chat.js`, `main.js`, and `settings.js` — current chat, voice, approval, pet-visibility, and settings behavior.
- `jarvis-desktop-pet/ui_pet/src/pet.html` — current pet overlay controls and approval surface.
- `jarvis-desktop-pet/ui_pet/src-tauri/tauri.conf.json` — current main/pet window configuration and tray integration.
