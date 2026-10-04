# JARVIS Desktop UI Revamp

## Product UI Master Specification

**Document status:** Final design and implementation specification  
**Scope:** Desktop application UI/UX, visual system, interaction model, component system, assistant presence, motion, states, accessibility, responsive behavior, and frontend implementation guidance  
**Primary goal:** Transform Jarvis from a technically capable assistant interface into a polished desktop product that feels intentional, premium, calm, fast, and trustworthy.

---

# 0. Executive Summary

Jarvis should not look like a generic AI chat client with a mascot placed on top. It should feel like a dedicated desktop command center whose core capability is understanding what the user wants, executing work across tools, remembering context, and presenting progress clearly.

The redesign therefore changes the product model from:

> **"A chat window that can do things."**

into:

> **"A personal AI workspace that happens to have conversation as its most natural control surface."**

The interface must communicate three things immediately:

1. **Jarvis is present.** The user always knows the assistant is available without being visually distracted by an oversized character.
2. **Jarvis is working.** Long-running tasks, tools, reasoning stages, automations, and external actions have understandable progress states.
3. **Jarvis is under the user's control.** Permissions, execution boundaries, memory, connected services, and automation schedules are visible and understandable.

The visual direction is intentionally product-first rather than novelty-first. The UI should feel closer to a high-end desktop productivity application than a futuristic movie prop. Futuristic details are used sparingly through subtle lighting, depth, motion, and assistant presence rather than through neon-heavy gradients, excessive glass, glowing borders, or a cartoon mascot.

The redesign uses a dark, neutral foundation with restrained cool accents, generous spacing, strong typography, low-noise surfaces, and precise motion. The assistant identity is represented primarily through an abstract, adaptive companion/orb rather than an animal avatar. The companion can express state, but it must never dominate the workspace.

The chat surface remains central, but the app is organized around a broader information architecture:

- Home / Command Center
- Conversations
- Tasks
- Automations
- Memory
- Integrations
- Settings

The same visual language should be used across all sections so the entire application feels like one coherent product rather than a set of independently designed screens.

---

# 1. Product Vision

## 1.1 Product statement

Jarvis is a desktop AI assistant designed to help a user think, search, create, automate, monitor, and execute work from one persistent environment.

It should make complex work feel approachable without hiding the important details.

The product experience is built around a simple principle:

> **The user should be able to start with an intention, while Jarvis handles the operational complexity.**

For example, the user should be able to say:

> "Find the latest invoices, summarize unpaid items, draft follow-ups, and schedule them for tomorrow at 9 AM."

The UI should then represent that request as a structured task, expose what Jarvis is doing, request approval only where necessary, and preserve the result as useful history.

The interface should not force the user to understand whether Jarvis uses a browser agent, a local script, an API, an LLM, a database query, a scheduler, or a chain of tools. Those implementation details can be surfaced progressively when useful.

## 1.2 Experience promise

Every major interaction should satisfy at least one of these promises:

- **Fast:** the user can get from intention to action with minimal friction.
- **Understandable:** the user can tell what Jarvis is doing.
- **Recoverable:** the user can understand failure and retry or change course.
- **Trustworthy:** the user can see when Jarvis needs permission or confirmation.
- **Persistent:** useful work is easy to resume later.

## 1.3 What this redesign is not

This redesign is not intended to become:

- a neon cyberpunk HUD;
- a gaming interface;
- a mascot-first chatbot;
- a pure chat clone;
- a dense enterprise dashboard;
- a collection of translucent cards floating over a gradient background.

The product should feel sophisticated because of hierarchy and polish, not because every component is visually loud.

---

# 2. Design Principles

## 2.1 Calm intelligence

Jarvis should look capable without constantly trying to prove that it is intelligent.

Avoid:

- animated text everywhere;
- persistent glowing effects;
- giant assistant illustrations;
- constantly moving decorative elements;
- excessive gradients;
- unnecessary charts.

Prefer:

- precise typography;
- meaningful status indicators;
- progressive disclosure;
- controlled motion;
- clear hierarchy;
- contextual information.

## 2.2 One surface, many capabilities

The user's primary workspace should remain continuous as they move between conversation, task execution, tool results, and follow-up actions.

Changing from a conversational state to a structured task should feel like the same object becoming more detailed, not leaving one application and opening another.

## 2.3 The UI explains state, not implementation

The user needs to know:

- waiting;
- thinking/processing;
- using a tool;
- asking permission;
- completed;
- partially completed;
- failed;
- paused.

The user generally does not need to see internal function names, model IDs, raw tool arguments, or logs unless they open an advanced view.

## 2.4 Progressive disclosure

Simple interactions stay simple.

Advanced information remains available but secondary.

For example, the default state can say:

> Searching connected files…

An expanded state can show:

> Files → Search → 38 results → 7 relevant documents

An advanced panel can expose:

> connector: files.search
> query: …
> latency: 1.4 s
> result count: 38

This layered approach preserves trust without overwhelming users.

## 2.5 User control without friction

Jarvis should ask for permission before consequential operations while avoiding constant confirmation dialogs for harmless actions.

The product should distinguish between:

- informational actions;
- reversible actions;
- low-risk external actions;
- high-impact external actions;
- recurring automation.

Permission requirements should be represented as part of the task flow rather than a generic modal whenever possible.

## 2.6 The companion is a system signal

The assistant companion is not the main character.

It exists to communicate presence and state:

- idle;
- listening;
- processing;
- successful;
- attention required;
- error;
- muted/offline.

The companion should be abstract enough that it feels like part of the product's identity rather than a separate mascot brand.

---

# 3. Visual Direction

## 3.1 Overall aesthetic

The chosen direction should feel like a premium desktop application with an understated futuristic layer.

Reference qualities:

- sophisticated;
- editorial;
- spacious;
- tactile;
- focused;
- quiet;
- technically advanced;
- highly intentional.

The UI should avoid the visual language of generic AI dashboards.

## 3.2 Color strategy

Because the earlier concepts leaned too heavily into expressive color, the production palette should be restrained.

### Base colors

Use a near-black graphite application background rather than pure black.

Suggested semantic tokens:

```css
--bg-app: #0D0F12;
--bg-sidebar: #111419;
--bg-surface: #15181D;
--bg-surface-elevated: #1A1E24;
--bg-surface-hover: #1E232A;
--bg-surface-pressed: #232831;

--border-subtle: rgba(255, 255, 255, 0.07);
--border-default: rgba(255, 255, 255, 0.10);
--border-strong: rgba(255, 255, 255, 0.16);

--text-primary: #F1F3F5;
--text-secondary: #A8AFB8;
--text-tertiary: #717984;
--text-disabled: #4C535D;
```

These are reference values, not hard requirements. The implementation should support them through design tokens rather than scattered hexadecimal values.

### Accent strategy

Use one primary cool accent rather than multiple bright brand colors everywhere.

Suggested primary accent family:

```css
--accent: #8E8CFF;
--accent-soft: rgba(142, 140, 255, 0.14);
--accent-hover: #A7A5FF;
--accent-strong: #7571F4;
```

Secondary semantic colors may be used for statuses, but they should remain muted:

```css
--success: #5FCB91;
--warning: #E9B95A;
--danger: #E57070;
--info: #71A9E8;
```

Do not build entire surfaces out of status colors.

## 3.3 Avoided visual patterns

Do not use:

- full-screen purple-blue gradients;
- large animated color blobs;
- glowing neon outlines around every card;
- rainbow AI visuals;
- bright accent backgrounds behind every primary action;
- glass blur on every element.

Depth should come mostly from contrast, spacing, borders, and subtle shadows.

## 3.4 Surface hierarchy

The product uses four practical surface levels:

1. **App background:** deepest layer.
2. **Primary surfaces:** sidebar, header, cards, composer container.
3. **Elevated surfaces:** menus, popovers, command panels.
4. **Transient surfaces:** dialogs, permission sheets, urgent notices.

Surfaces should generally differ by small changes in luminance rather than obvious color shifts.

---

# 4. Typography

## 4.1 Typography goals

Typography should make the product feel more like professional desktop software and less like a web template.

Use one primary UI typeface family with a strong hierarchy. If the codebase already has a suitable system/UI font, prefer it instead of adding unnecessary dependencies.

A sensible fallback stack is:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

## 4.2 Type scale

Suggested scale:

| Token | Size | Weight | Use |
|---|---:|---:|---|
| display | 32–36px | 600 | Rare page-level hero title |
| h1 | 24–28px | 600 | Section title |
| h2 | 18–20px | 600 | Card/area title |
| h3 | 15–16px | 600 | Subsection |
| body | 14–15px | 400 | Main text |
| body-medium | 14–15px | 500 | Emphasis |
| caption | 12–13px | 400 | Secondary metadata |
| micro | 11px | 500 | Status labels |
| mono | 12–13px | 400 | Code/logs |

Line height matters more than tiny differences in font size.

## 4.3 Message typography

Assistant messages should not appear inside giant opaque bubbles by default.

The preferred composition is:

```text
[assistant mark]  Jarvis
                 response text...
                 response text...

                 [actions] [sources] [task details]
```

User messages can have a slightly more contained treatment, especially when the conversation needs stronger separation.

Avoid the familiar "every message is a rounded rectangle" pattern throughout the product.

---

# 5. Layout System

## 5.1 Desktop frame

The main application should be designed for a desktop viewport first.

Reference layout at 1440 × 900:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Window chrome / top application region                                       │
├──────────────┬───────────────────────────────────────────────────────────────┤
│              │ Header                                                        │
│              ├───────────────────────────────────────────────────────────────┤
│   Sidebar    │                                                               │
│              │                    Main workspace                              │
│              │                                                               │
│              │                                                               │
│              │                                                               │
│              ├───────────────────────────────────────────────────────────────┤
│              │ Contextual composer / action bar                              │
└──────────────┴───────────────────────────────────────────────────────────────┘
```

Suggested widths:

- sidebar expanded: 248–272px;
- sidebar collapsed: 72–76px;
- main content max width: 1180–1320px depending on screen;
- conversation reading column: 760–900px;
- right inspector: 320–380px when open.

## 5.2 Grid

Use an 8px base spacing scale:

```text
4   micro spacing
8   base
12  compact
16  standard
20  comfortable
24  section
32  major
40  large
48  hero/major separation
64  page-level separation
```

Do not use dozens of arbitrary margins.

## 5.3 Corner radius

Use moderately rounded surfaces rather than exaggerated pill shapes.

Suggested values:

```css
--radius-xs: 6px;
--radius-sm: 8px;
--radius-md: 12px;
--radius-lg: 16px;
--radius-xl: 20px;
--radius-pill: 999px;
```

Cards should mostly use 12–16px radii.

Buttons can use 9–12px depending on hierarchy.

Reserve pill shapes for compact tags, status badges, and segmented controls.

---

# 6. Information Architecture

## 6.1 Primary navigation

The left sidebar should contain the core product areas:

```text
JARVIS

⌂  Home
✦  New conversation
◷  Tasks
↻  Automations
🧠 Memory
◈  Integrations

Recent
  conversation 1
  conversation 2
  conversation 3

────────────────
Settings
Profile / workspace
```

The exact icon set can vary, but iconography must be consistent.

## 6.2 Navigation behavior

The sidebar has two modes:

### Expanded

Shows:

- icon;
- label;
- contextual metadata where useful;
- active state;
- section grouping.

### Collapsed

Shows:

- icon only;
- tooltip on hover;
- active indicator;
- accessible label.

The sidebar should not disappear completely at normal desktop sizes. It is part of the product's persistent mental model.

## 6.3 Recent conversations

Recent conversations should not become an uncontrolled list.

Support:

- pinned items;
- recent items;
- search;
- automatic grouping by Today / Yesterday / Earlier when appropriate;
- context menu actions.

Conversation titles should be editable.

---

# 7. Home / Command Center

## 7.1 Purpose

Home is not a dashboard full of charts.

Its primary purpose is to answer:

> **What can I do right now, and what should I resume?**

## 7.2 Home composition

Recommended structure:

```text
┌────────────────────────────────────────────────────────────┐
│ Good evening, Ammar                                       │
│ What would you like to work on?                           │
│                                                            │
│ [ Ask Jarvis anything...                              ]    │
│                                                            │
│ Quick actions                                              │
│ [Research] [Draft] [Analyze] [Automate]                  │
│                                                            │
│ Active work                                                │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Reconcile invoices                    62%              │ │
│ │ 3 of 5 steps complete                  Running          │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                            │
│ Recent                                                     │
│ ...                                                        │
└────────────────────────────────────────────────────────────┘
```

## 7.3 Greeting

Greeting should be subtle.

Do not make the home screen look like a motivational wellness application.

Use:

> Good evening, Ammar.
>
> What would you like to get done?

The second line is more important than the greeting.

## 7.4 Home composer

The home composer is visually important and should feel like an invitation rather than a chatbot box.

It should include:

- text input;
- attach button;
- voice button if supported;
- optional mode selector;
- send/execute control;
- contextual shortcut row.

The composer should feel substantial but not oversized.

## 7.5 Quick actions

Quick actions should represent tasks, not abstract technology.

Good examples:

- Research a topic
- Summarize files
- Draft an email
- Analyze data
- Plan a task
- Run an automation

Avoid labels such as:

- RAG
- Agent mode
- Tool chain
- LLM pipeline

Those describe implementation, not user goals.

## 7.6 Active work cards

Active work should be presented as compact cards with:

- title;
- status;
- progress;
- current step;
- elapsed time if relevant;
- stop/open controls.

Users should never have to guess whether a task is still running.

---

# 8. Conversation Workspace

## 8.1 Core layout

The conversation screen consists of:

1. conversation header;
2. message timeline;
3. contextual task/tool region when needed;
4. composer;
5. optional right inspector.

The timeline should occupy most of the screen.

## 8.2 Conversation header

Header should contain:

- conversation title;
- lightweight state if an operation is active;
- model/mode selector only if useful;
- search conversation;
- more menu.

Avoid filling the header with technical controls.

## 8.3 User messages

User messages can use a soft surface treatment rather than a heavy bubble.

The goal is to make the user's input clearly identifiable without creating a two-column visual wall of bubbles.

## 8.4 Assistant messages

Assistant messages are editorial and content-oriented.

Support:

- markdown;
- headings;
- code;
- tables;
- citations/sources;
- expandable details;
- action buttons.

The assistant identity mark should appear at the start of substantial responses.

## 8.5 Response actions

Useful actions include:

- copy;
- retry;
- edit and resend;
- continue;
- save;
- create task;
- export/share;
- open source details.

Actions should appear on hover/focus or at the end of the response rather than permanently crowding every message.

## 8.6 Long responses

Long responses should be broken into readable sections.

Avoid maximum-width content that spans the whole application.

Default reading width should remain around 760–900px.

---

# 9. Composer Design

## 9.1 Composer anatomy

```text
┌───────────────────────────────────────────────────────────────┐
│ Ask Jarvis...                                                │
│                                                               │
│ +  Attach   /  Tools  /  Mode                         Send → │
└───────────────────────────────────────────────────────────────┘
```

The composer is one of the highest-frequency components and deserves exceptional polish.

## 9.2 Empty state

Placeholder text should communicate action:

> Ask Jarvis to research, create, analyze, or automate…

Avoid:

> Type a message…

## 9.3 Focus state

When focused:

- border contrast increases;
- the assistant accent appears subtly;
- no large glow should appear;
- controls become slightly more prominent.

## 9.4 Multi-line input

Input should grow vertically up to a defined maximum.

After reaching the maximum, content scrolls internally.

Suggested max height:

- 220–280px desktop.

## 9.5 Attachments

Attachments should appear as compact chips or previews above the composer controls.

Example:

```text
[📄 Q4-report.pdf ×] [📊 sales.csv ×]
```

Do not create giant preview cards inside the composer unless the content itself needs visual inspection.

## 9.6 Voice input

If voice input is supported, pressing the microphone should clearly change the composer state.

States:

- ready;
- listening;
- processing;
- transcription inserted;
- permission denied;
- unavailable.

Avoid an endlessly pulsing microphone animation.

---

# 10. Assistant Companion System

## 10.1 Design decision

The assistant companion should not be a literal pet or human-like character.

Use an abstract compact form—an orb, layered sphere, soft geometric core, or similarly minimal identity object.

This avoids the problems of:

- mascot-like behavior;
- cartoon visual mismatch;
- unnecessary cuteness;
- difficulty communicating technical states;
- visual aging.

## 10.2 Companion composition

The companion should have:

- a stable geometric silhouette;
- subtle depth;
- a small internal light/core;
- low-frequency state motion;
- state-dependent micro-animation.

No large eyes, face, ears, legs, or animal features should be introduced.

## 10.3 Idle state

Idle should be almost static.

Animation:

- very slow light movement;
- slight internal depth change;
- occasional low-frequency breathing.

The user should not notice the animation unless they look at it.

## 10.4 Listening state

Listening should communicate active input without becoming distracting.

Suggested behavior:

- slightly brighter core;
- subtle concentric motion;
- small response to microphone input if feasible.

## 10.5 Processing state

Processing is represented through structured movement.

Avoid infinite spinners whenever possible.

Preferred pattern:

```text
[Companion]
Processing
Understanding request → Planning → Acting
```

The animation can reflect progress but the text should carry the semantic meaning.

## 10.6 Success state

Success can use:

- brief brightness increase;
- small scale lift;
- soft settling animation.

Do not create confetti unless explicitly tied to a user achievement.

## 10.7 Attention-required state

When Jarvis needs user input:

- companion gains a small accent ring;
- state label changes to "Needs your input";
- workspace shows the relevant action.

## 10.8 Error state

Use a subdued error treatment.

Do not turn the assistant bright red.

Error should communicate:

> Something needs attention.

rather than:

> System failure.

---

# 11. Task Execution Model

## 11.1 Why task visualization matters

The application becomes more useful when Jarvis can execute multi-step work.

A simple chat transcript is insufficient for long-running operations.

The redesign therefore treats a complex assistant request as both a conversation and a task object.

## 11.2 Task card

Example:

```text
Reconcile monthly invoices
Running · 3 of 5 steps

✓ Collect invoice files
✓ Extract totals
● Compare against payment ledger
○ Prepare discrepancy report
○ Draft follow-up emails

[Open task] [Pause]
```

## 11.3 Task phases

Recommended user-facing phases:

1. Understanding
2. Planning
3. Gathering
4. Processing
5. Waiting for user
6. Executing
7. Finalizing
8. Complete
9. Partially complete
10. Failed
11. Canceled

These labels can be mapped to internal states.

## 11.4 Running task detail

When opened, the task inspector can show:

- objective;
- steps;
- current action;
- tools/services used;
- outputs;
- approvals;
- errors;
- timestamps;
- retry controls.

## 11.5 Pause and stop

For tasks that may run for a long period, provide a clear stop/pause action.

Destructive controls should be visually secondary until necessary, but still easy to find.

---

# 12. Permission and Approval UX

## 12.1 Principle

Permission prompts should appear at the moment Jarvis reaches a meaningful boundary.

For example:

> Jarvis found the messages and drafted the replies.
>
> Sending them will contact 14 recipients.
>
> **Review and send**
> **Keep as drafts**

This is better than asking upfront:

> Are you sure Jarvis can send email?

## 12.2 Approval sheet

Recommended structure:

```text
┌─────────────────────────────────────────────┐
│ Approval required                           │
│                                             │
│ Send 14 follow-up emails                   │
│                                             │
│ Jarvis will:                               │
│ • Send from work@example.com               │
│ • Contact 14 recipients                    │
│ • Use the reviewed draft                   │
│                                             │
│ [Review]                       [Approve]   │
└─────────────────────────────────────────────┘
```

## 12.3 Approval language

Avoid technical language.

Bad:

> Grant connector permission to execute outbound mutation.

Good:

> Allow Jarvis to send these emails?

## 12.4 Remember decision

For recurring actions, allow the user to choose a permission policy when appropriate:

- Always ask
- Ask for this task only
- Allow for this automation

The choice should be easy to understand and reversible from Settings.

---

# 13. Tasks Area

## 13.1 Purpose

The Tasks area is a structured view of current and historical work.

It should answer:

- What is running?
- What needs me?
- What finished?
- What failed?

## 13.2 Tabs

Suggested:

```text
Active    Needs input    Completed    Failed
```

Avoid too many filters at the top.

## 13.3 Task list item

Each item should show:

- task name;
- state;
- one-line objective;
- current step;
- updated time;
- relevant source/context;
- compact action.

## 13.4 Empty states

Empty states should be useful rather than decorative.

Example:

> Nothing is running.
> Start a task from Home or ask Jarvis to work on something that takes multiple steps.

Primary action:

> Start a task

---

# 14. Automations

## 14.1 Purpose

Automations represent recurring or trigger-based work.

Examples:

- weekday morning briefing;
- monitor a folder and summarize new files;
- check a website for changes;
- generate a recurring report;
- remind the user when a condition occurs.

## 14.2 Automation list

Each automation should show:

- name;
- trigger;
- next run;
- enabled/disabled state;
- recent execution status.

Example:

```text
Daily market briefing
Every weekday · 08:30
Next run: Tomorrow, 08:30
Last run: Completed
                                  [Enabled]
```

## 14.3 Automation builder

The builder should be conversationally assisted but visually structured.

```text
When
[ Every weekday at 08:30                    ]

Do
[ Research the latest market updates         ]
[ Summarize key changes                       ]
[ Send the briefing to me                    ]

Permissions
[ Use existing approved connections           ]

[Save automation]
```

## 14.4 Natural language creation

The user should be able to say:

> Every weekday at 8 AM, check my calendar, summarize meetings, and give me a short briefing.

Jarvis should translate this into an editable structured automation.

The UI must make the generated schedule and actions visible before saving.

---

# 15. Memory

## 15.1 Product purpose

Memory should not resemble a database admin panel.

The user needs understandable controls over what Jarvis remembers.

## 15.2 Memory categories

Suggested categories:

- Preferences
- Personal context
- Work context
- Ongoing projects
- Important instructions

## 15.3 Memory item

Example:

```text
Prefers short, natural recruiter messages
Work preference
Added Sep 12

[Edit] [Forget]
```

## 15.4 Memory explanation

Whenever appropriate, show why an item exists:

> Saved because you asked Jarvis to remember this preference.

or:

> Added from an approved conversation.

## 15.5 Forgetting

Forgetting must be easy.

A memory item should be removable directly from the list without forcing navigation into a separate settings page.

---

# 16. Integrations

## 16.1 Purpose

Integrations connect Jarvis to external services.

The UI should focus on what a connection enables rather than showing provider logos as the primary information.

## 16.2 Integration card

```text
Gmail
Connected

Read messages · Draft replies · Send email

[Manage]
```

## 16.3 Connection detail

Show:

- connected account;
- capabilities;
- permissions;
- last used;
- disconnect;
- reauthorize.

## 16.4 Connection state

Every integration needs clear states:

- not connected;
- connecting;
- connected;
- limited permissions;
- expired;
- error;
- reconnecting.

## 16.5 Security messaging

Do not use alarming or vague copy.

Prefer:

> Jarvis can access the permissions listed below.

Then enumerate them.

---

# 17. Settings

## 17.1 Settings architecture

Suggested categories:

```text
General
Appearance
Assistant
Models & behavior
Memory
Permissions
Notifications
Integrations
Shortcuts
Data & privacy
Advanced
About
```

## 17.2 Settings principles

Settings should be:

- searchable;
- grouped logically;
- descriptive;
- reversible;
- consistent with the rest of the application.

## 17.3 Appearance

Appearance settings should include:

- theme;
- density;
- sidebar mode;
- motion preferences;
- accent intensity if exposed;
- reduced transparency if available.

Do not create dozens of theme customization controls in the initial release.

## 17.4 Advanced settings

Technical controls can exist but should be isolated under Advanced.

Examples:

- logging;
- diagnostics;
- developer tools;
- experimental features;
- model debug data.

The normal application should remain clean.

---

# 18. Search

## 18.1 Global search

Keyboard shortcut:

```text
Ctrl/Cmd + K
```

should open the command/search interface.

## 18.2 Search scope

Search should eventually cover:

- conversations;
- tasks;
- automations;
- memory;
- integrations/settings.

## 18.3 Search UI

Use a centered command palette with strong typography and compact results.

Example:

```text
Search Jarvis
────────────────────────────────
⌕  invoice reconciliation

Conversations
  Invoice cleanup — Sep 29

Tasks
  Reconcile monthly invoices

Memory
  Finance workflow preference
```

## 18.4 Command mode

Search and command execution can share the same palette.

Examples:

> New conversation
> Open Settings
> Run Morning Briefing
> Pause active tasks
> Toggle compact mode

This makes the product feel like a desktop assistant instead of a website.

---

# 19. Notifications

## 19.1 Notification philosophy

Notifications should be meaningful and sparse.

Do not notify the user for every internal step.

Notify for:

- task completed;
- user input required;
- automation failed;
- important approval request;
- integration requires attention.

## 19.2 Toasts

Toasts are appropriate for immediate lightweight events.

Example:

> Report saved.
> Undo

Avoid stacked toast storms.

## 19.3 Persistent attention

Important states should also appear in the relevant task, automation, or integration view. A toast alone should never be the only record of meaningful system state.

---

# 20. Window and Desktop Behavior

## 20.1 Window chrome

If the desktop framework permits custom chrome, keep it minimal.

The top region should not waste large vertical space.

## 20.2 Minimum supported size

The interface should remain functional around:

- 1024 × 700 minimum practical workspace;
- 1280 × 800 comfortable workspace;
- 1440 × 900 preferred reference.

Below the practical minimum, secondary panels should collapse before primary interaction becomes unusable.

## 20.3 Resizing

When the window narrows:

1. right inspector collapses;
2. sidebar may collapse;
3. reading column retains usable width;
4. secondary composer actions become compact;
5. navigation becomes icon-first.

Do not allow the main content to shrink into a narrow unreadable column while large empty side panels remain visible.

---

# 21. Responsive States

Although Jarvis is desktop-first, the component system should support smaller widths.

## 21.1 Wide desktop

At 1440px and above:

- expanded sidebar;
- main workspace;
- optional inspector.

## 21.2 Standard desktop

At 1200–1439px:

- expanded sidebar;
- narrower main reading column;
- inspector opens as overlay.

## 21.3 Compact desktop

At 900–1199px:

- collapsed sidebar by default;
- inspector as overlay;
- simplified header.

## 21.4 Small window

Below 900px:

- single primary workspace;
- sidebar as drawer;
- composer controls compacted;
- tables scroll horizontally where necessary.

---

# 22. Motion Design

## 22.1 Motion principle

Animation should communicate state and hierarchy.

It should never exist merely because the interface can animate.

## 22.2 Timing

Suggested durations:

```text
micro: 100–140ms
standard: 160–220ms
emphasis: 240–320ms
panel: 280–380ms
```

Use ease-out for entering elements and ease-in-out for state changes.

## 22.3 Core motions

### Navigation

Content should transition quickly and subtly.

### Panels

Side panels slide/fade by a small distance. Avoid large travel distances.

### Modals

Use scale from ~0.98 to 1 plus fade rather than dramatic zoom.

### Task progress

Progress should animate smoothly when the percentage changes.

### Companion

Motion is continuous but low-amplitude.

## 22.4 Reduced motion

When reduced motion is enabled:

- disable decorative continuous animations;
- reduce transition duration;
- avoid parallax;
- replace animated progress with immediate state changes where appropriate.

---

# 23. Microinteractions

The product feeling comes from many small details.

Examples:

- icon changes state with a 120ms transition;
- button press slightly changes luminance and scale;
- copied content briefly shows a checkmark;
- completed task steps settle instead of disappearing;
- connection status updates without rebuilding the whole card;
- composer send action confirms visually before the message appears.

These details should be systematic, not individually improvised.

---

# 24. Iconography

## 24.1 Style

Use a single consistent icon family.

Preferred characteristics:

- simple stroke construction;
- consistent optical weight;
- 16–20px default UI size;
- clear silhouettes.

## 24.2 Icon sizing

Recommended:

```text
12px  micro/meta
16px  standard controls
18px  navigation
20px  primary action
24px  section/high emphasis
```

## 24.3 Icons should not carry text alone

Any ambiguous action should include:

- visible text;
- tooltip;
- or accessible label.

---

# 25. Component System

The UI should be built from reusable primitives.

Recommended component layers:

## 25.1 Primitives

- Button
- IconButton
- Input
- Textarea
- Select
- Checkbox
- Switch
- Badge
- Avatar/CompanionMark
- Tooltip
- Divider

## 25.2 Composite components

- SearchCommand
- ConversationListItem
- Message
- MessageActions
- Composer
- AttachmentChip
- TaskCard
- TaskStepList
- ApprovalCard
- AutomationCard
- IntegrationCard
- MemoryCard
- NotificationToast

## 25.3 Layout components

- AppShell
- Sidebar
- Header
- PageContainer
- SplitPane
- Inspector
- ModalSheet
- CommandPalette

The implementation must avoid one-off styles for each screen when a reusable component can express the same pattern.

---

# 26. Button Hierarchy

Use four levels.

## Primary

High-value current action.

Example:

> Send

## Secondary

Useful supporting action.

Example:

> Review

## Tertiary

Low-emphasis action.

Example:

> Copy

## Destructive

Actions that can cause loss or significant external effects.

Example:

> Delete automation

Destructive actions should never look like the default primary button.

---

# 27. Data Visualization

Jarvis may need to display charts, tables, and analytical results.

The visual system for generated content should remain aligned with the product shell.

## 27.1 Charts

Charts should:

- use restrained colors;
- emphasize the relevant data;
- avoid ornamental backgrounds;
- provide labels and tooltips;
- preserve accessibility.

## 27.2 Tables

Tables should support:

- sticky headers where useful;
- row hover;
- compact density;
- column alignment;
- overflow handling;
- copy/export where relevant.

## 27.3 Generated analysis

Generated data should not automatically become giant dashboard widgets.

Jarvis should select the simplest meaningful representation:

- sentence for one fact;
- list for multiple findings;
- table for structured comparisons;
- chart for relationships or trends.

---

# 28. Code and Technical Content

Because Jarvis can assist with development, technical output must be highly readable.

## 28.1 Code blocks

Use:

- distinct code surface;
- monospace font;
- syntax highlighting;
- copy action;
- optional line numbers.

## 28.2 Logs

Logs should be clearly separated from conversational content.

Example:

```text
RUNNING
08:41:02  Connected to database
08:41:03  Retrieved 1,284 rows
08:41:04  Calculating aggregate metrics
```

Advanced diagnostics can use a dedicated inspector rather than overwhelming the conversation.

---

# 29. Error UX

## 29.1 Error taxonomy

Errors should be classified into user-understandable categories:

- Needs input
- Permission denied
- Connection problem
- External service unavailable
- Task failed
- Unexpected problem

## 29.2 Error message anatomy

```text
What happened
The Google connection expired.

What you can do
Reconnect your account to continue.

[Reconnect]
```

Avoid:

> Error code 401.

unless the code is additionally useful in an advanced section.

## 29.3 Retry behavior

Where retry is safe, provide it directly.

Where retry may repeat an external action, explain what will happen before retrying.

---

# 30. Loading and Skeleton States

## 30.1 Principle

Skeletons should indicate structure, not imitate every pixel.

Use skeletons for:

- conversation loading;
- task lists;
- integration data;
- memory lists.

For active assistant work, semantic progress is generally better than a skeleton.

## 30.2 No fake progress

Never show a 70% progress bar merely because the operation is taking time.

Progress percentages should correspond to meaningful known stages.

If real progress is unavailable, use:

> Working…

or a step-based state.

---

# 31. Empty States

Empty states should explain what the area is for and how to start.

Template:

```text
[small visual cue]

No automations yet
Create a recurring workflow and let Jarvis run it for you.

[Create automation]
```

Avoid overly cute illustrations or large center-screen cartoons.

---

# 32. Onboarding

## 32.1 First-run goal

The user should understand the product within minutes.

Do not begin with a 10-screen tutorial.

## 32.2 First-run sequence

Recommended:

### Step 1 — Welcome

> Meet Jarvis.
> A desktop assistant for getting real work done.

### Step 2 — Choose capabilities

Allow the user to enable relevant features.

### Step 3 — Connect services

Offer optional integrations.

### Step 4 — Try a useful task

Give a concrete example.

> "Summarize these documents and tell me what needs attention."

### Step 5 — Arrive at Home

The user lands in the actual product.

## 32.3 Do not force everything

The user should be able to skip integration setup and continue locally.

---

# 33. First-Session Product Tour

A lightweight tour can highlight:

1. command input;
2. task progress;
3. conversation history;
4. automation area;
5. memory controls.

Use one tooltip at a time.

Never darken the entire screen for a minor feature introduction.

---

# 34. Accessibility

Accessibility is part of the product design rather than a later engineering task.

## 34.1 Keyboard support

Core flows must be fully keyboard usable.

Important shortcuts:

```text
Ctrl/Cmd + K   Search / command palette
Ctrl/Cmd + N   New conversation
Ctrl/Cmd + Enter Send in composer when applicable
Esc            Close overlays / stop editing
↑ / ↓          Navigate menus/results
Enter          Confirm
```

## 34.2 Focus visibility

Every interactive element needs a strong visible focus state.

Do not rely solely on hover states.

## 34.3 Contrast

Text and controls need sufficient contrast against their surface. Muted text should remain readable, especially in dark mode.

## 34.4 Screen readers

Icons need semantic labels.

Status changes should be announced appropriately without reading every internal step.

## 34.5 Motion preference

Respect reduced-motion preferences throughout the app.

---

# 35. Interaction States Checklist

Every interactive component should define:

```text
Default
Hover
Pressed
Focused
Disabled
Loading
Success
Error
Selected
Expanded
Collapsed
```

Not every component needs every state visually, but the implementation should deliberately decide which states exist.

A major source of unfinished product feeling is designing only the default state.

---

# 36. Visual QA Standards

The UI should be checked at multiple sizes and interaction conditions.

## 36.1 Required desktop checks

- 1440 × 900
- 1280 × 800
- 1024 × 768
- compact resized window

## 36.2 Required UI states

- empty app;
- first-run;
- active conversation;
- long conversation;
- active task;
- permission request;
- task failure;
- automation failure;
- integration disconnected;
- no search results;
- loading;
- dark mode;
- reduced motion.

## 36.3 Visual review questions

Ask:

- Does the main action immediately stand out?
- Is the page hierarchy obvious in two seconds?
- Is anything visually louder than its importance?
- Is the assistant companion supporting the UI instead of competing with it?
- Are there unnecessary borders, glows, or cards?
- Does the screen still look polished when data is empty?
- Does the screen still look polished when content is very long?

---

# 37. Product Polish Checklist

A screen should not be considered complete until it answers all of these:

### Hierarchy

- Is there one obvious primary action?
- Are secondary controls appropriately quiet?
- Is the page title useful?

### Spacing

- Is spacing based on the system?
- Are grouped elements visibly grouped?
- Are unrelated elements sufficiently separated?

### Typography

- Is text weight consistent?
- Are labels too small?
- Are headings doing useful organizational work?

### Surfaces

- Are there unnecessary cards?
- Does depth have purpose?
- Are borders too strong?

### Interaction

- Are hover/focus/pressed states defined?
- Is feedback immediate?
- Can the user recover from mistakes?

### Trust

- Does the user know when Jarvis is acting?
- Can the user see what requires approval?
- Is task status understandable?

---

# 38. Design Tokens

A token system should be the foundation of the implementation.

Example structure:

```ts
export const tokens = {
  color: {
    bg: {
      app: 'var(--bg-app)',
      sidebar: 'var(--bg-sidebar)',
      surface: 'var(--bg-surface)',
      elevated: 'var(--bg-surface-elevated)',
    },
    text: {
      primary: 'var(--text-primary)',
      secondary: 'var(--text-secondary)',
      tertiary: 'var(--text-tertiary)',
    },
    accent: {
      base: 'var(--accent)',
      soft: 'var(--accent-soft)',
    },
  },
  radius: {
    xs: 'var(--radius-xs)',
    sm: 'var(--radius-sm)',
    md: 'var(--radius-md)',
    lg: 'var(--radius-lg)',
  },
  space: {
    1: '4px',
    2: '8px',
    3: '12px',
    4: '16px',
    5: '20px',
    6: '24px',
    8: '32px',
    10: '40px',
    12: '48px',
  },
};
```

The actual frontend stack can adapt this structure.

---

# 39. Theme Architecture

Even if only one theme ships initially, implement the system so the product does not hardcode visual decisions into individual components.

Example:

```text
ThemeProvider
 ├─ color tokens
 ├─ typography tokens
 ├─ spacing tokens
 ├─ radius tokens
 └─ motion tokens
```

This enables future light mode or alternate accessibility themes without rewriting the application.

---

# 40. Frontend Architecture Guidance

The exact framework may differ, but the UI should be structured into domains rather than giant page components.

Example:

```text
src/
  app/
    shell/
    routes/
    providers/
  components/
    primitives/
    composite/
    layout/
  features/
    conversations/
    tasks/
    automations/
    memory/
    integrations/
    settings/
  design/
    tokens/
    icons/
    motion/
  lib/
    api/
    state/
    formatting/
```

Feature-level ownership makes it easier to evolve each part without creating a monolithic UI layer.

---

# 41. State Management Guidance

UI state and assistant execution state should be conceptually separated.

Examples of UI state:

- active navigation item;
- sidebar open/closed;
- current modal;
- composer draft;
- selected conversation;
- filter.

Examples of product state:

- task status;
- automation status;
- integration connection;
- conversation messages;
- memory items;
- approvals.

Do not bury persistent task state inside a local component state tree where it cannot be resumed reliably.

---

# 42. Event-Driven Interaction Model

Complex operations should be represented as stateful events rather than inferred entirely from visual rendering.

Conceptually:

```text
User request
   ↓
Task created
   ↓
Plan generated
   ↓
Step started
   ↓
Tool action
   ↓
Tool result
   ↓
Next step
   ↓
Approval needed ──→ User decision
   ↓
Completion
```

The UI should subscribe to state changes and render them consistently.

This is particularly important for:

- long-running tasks;
- background automations;
- reconnect behavior;
- app restart;
- notifications.

---

# 43. Offline and Reconnect States

A desktop assistant cannot assume perfect connectivity.

## 43.1 Connection state

Provide a subtle application status indicator when needed.

Possible states:

- Online
- Connecting
- Offline
- Degraded

Do not keep a permanent large "ONLINE" badge on the screen.

## 43.2 Offline behavior

When offline, the app should clearly distinguish:

- local actions that still work;
- queued actions;
- unavailable cloud capabilities.

Example:

> You're offline. New requests will be sent when the connection returns.

Only show this when it materially affects behavior.

---

# 44. Persistence and Recovery UX

The user should not lose meaningful work because they closed the application.

Persist where appropriate:

- conversation drafts;
- active tasks;
- task history;
- automation definitions;
- user preferences.

On reopen:

> You have 2 active tasks.
>
> [Review active work]

This is much stronger than forcing the user to reconstruct context manually.

---

# 45. Conversation Resume Experience

When reopening a conversation that has an incomplete task, show a compact state marker.

Example:

```text
Invoice cleanup
Task paused · Waiting for approval

[Resume]
```

The user should be able to resume directly from the conversation list or task list.

---

# 46. User-Controlled Assistant Modes

Where different operating modes exist, avoid presenting them as obscure technical presets.

Instead use meaningful user language.

Examples:

- Quick
- Balanced
- Deep work
- Automation

Each mode can map internally to different models or execution policies.

Provide a tooltip or secondary description:

> Deep work — more planning and tool usage for complex tasks.

---

# 47. Advanced Mode

Power users may want additional information.

Advanced mode can reveal:

- execution steps;
- tool calls;
- latency;
- model information;
- token usage where relevant;
- retry metadata;
- diagnostic details.

This should be a deliberate toggle, not the default visual language.

The design rule is:

> **Expert information should be available, not unavoidable.**

---

# 48. Companion Placement Strategy

The companion should appear in three primary locations.

## 48.1 Home

A moderate-size identity element can sit near the main composer or in the header.

## 48.2 Active processing

The companion appears in the current task/message state.

## 48.3 Global availability

A small persistent identity mark can be present in the sidebar/header.

Do not render a large floating pet over content.

Do not make the companion block content or intercept clicks.

---

# 49. Companion Expressions

Expressions should be represented through geometry/light, not face animations.

Suggested state mapping:

| State | Shape/Light | Motion |
|---|---|---|
| Idle | soft neutral core | very slow breathing |
| Listening | brighter core | subtle concentric response |
| Thinking | layered inner motion | slow rotation/flow |
| Working | directional motion | slightly more active |
| Success | brief highlight | settle animation |
| Attention | accent ring | periodic pulse |
| Error | muted warning tone | short interruption |
| Offline | dimmed core | static |

---

# 50. The Product Should Feel Alive, Not Animated

This distinction is important.

The interface should feel responsive and aware, but the user should not constantly watch animations.

A premium interface is often perceived as more advanced because it knows when **not** to move.

---

# 51. Home Screen Final Composition

The recommended production composition is:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ JARVIS                                                          ◌  •••   │
├───────────────┬──────────────────────────────────────────────────────────┤
│               │                                                          │
│  Home         │  Good evening, Ammar.                                  │
│  New chat     │  What would you like to get done?                       │
│               │                                                          │
│  Tasks        │  ┌──────────────────────────────────────────────────┐    │
│  Automations  │  │ Ask Jarvis to research, create, analyze...      │    │
│  Memory       │  │                                                  │    │
│  Integrations │  │ + Attach     Tools                         Send →│    │
│               │  └──────────────────────────────────────────────────┘    │
│               │                                                          │
│  Recent       │  Suggested                                              │
│  ...          │  [Research] [Analyze] [Draft] [Automate]               │
│               │                                                          │
│               │  Active work                                            │
│               │  ┌──────────────────────────────────────────────────┐    │
│               │  │ Reconcile invoices                Running · 62%  │    │
│               │  │ Compare against payment ledger                  │    │
│               │  └──────────────────────────────────────────────────┘    │
│               │                                                          │
│               │  Recent                                                 │
│               │  Invoice cleanup      Yesterday                        │
│               │  Market research      Sep 30                           │
└───────────────┴──────────────────────────────────────────────────────────┘
```

This layout should remain visually comfortable when the data is sparse.

---

# 52. Conversation Screen Final Composition

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Invoice cleanup                              Search    •••                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ You                                                                         │
│ Compare the latest invoices with the payment ledger and identify gaps.     │
│                                                                             │
│ ◌ Jarvis                                                                     │
│ I’ll compare the files and flag discrepancies.                              │
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ Task: Reconcile invoices                         Running · 3/5         │   │
│ │ ✓ Collect files  ✓ Extract totals  ● Compare  ○ Report  ○ Draft      │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│ Results                                                                     │
│ I found 4 discrepancies totaling $2,430.                                   │
│                                                                             │
│ [View details] [Create report]                                             │
│                                                                             │
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ Ask a follow-up…                                                    │   │
│ │                                                                       │   │
│ │ + Attach      Tools                                      Send →      │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 53. Advanced Inspector

The right-side inspector is an important mechanism for keeping the main conversation clean.

When opened, it can show:

```text
Task
────────────────────────
Reconcile invoices

Progress
3 / 5 steps

Current
Compare against ledger

Tools used
• File search
• Spreadsheet parser
• Database query

Timeline
09:14 Started
09:15 Files collected
09:16 Extraction complete
09:16 Comparison running

[Pause task]
```

This prevents detailed operational information from polluting the primary conversation flow.

---

# 54. Contextual Actions

Actions should appear where they are useful.

For example, after a generated report:

```text
[Save] [Export] [Share] [Create task]
```

After a research result:

```text
[Open sources] [Save summary] [Ask follow-up]
```

After a draft:

```text
[Edit] [Copy] [Send]
```

The UI should avoid universal action bars that show every possible command everywhere.

---

# 55. User Feedback Patterns

The product needs a consistent feedback vocabulary.

### Informational

Neutral surface + subtle icon.

### Success

Short confirmation + optional next action.

### Warning

Explain impact + action to resolve.

### Error

Explain cause + recovery.

### Attention

Make clear why Jarvis stopped and what the user needs to do.

Consistency here creates a sense of quality even when the underlying operation is complex.

---

# 56. Product Copy Style

Jarvis copy should be:

- concise;
- direct;
- human;
- calm;
- specific;
- non-technical by default.

Avoid:

> Initialization of assistant orchestration has failed.

Prefer:

> Jarvis couldn't start this task.
> Try again or view the details.

Avoid overly enthusiastic copy:

> Amazing! Jarvis is super excited to help!

Prefer:

> Ready when you are.

---

# 57. Naming Rules

Use one name consistently for each concept.

For example, choose:

- Task, not Job sometimes and Workflow elsewhere;
- Automation, not Routine in one area and Schedule in another;
- Memory, not Knowledge in another screen if both mean the same thing.

Terminology consistency is a major contributor to perceived product quality.

---

# 58. Context Menus

Context menus should be compact and task-specific.

Conversation example:

```text
Rename
Pin
Move to folder
Export
Delete
```

Task example:

```text
Open
Duplicate
Retry
Cancel
Delete history
```

Do not put unrelated global commands in every menu.

---

# 59. Confirmation Dialog Strategy

Confirmation dialogs should be reserved for genuinely consequential actions.

Good uses:

- deleting a long-running automation;
- disconnecting a critical integration;
- canceling a task with irreversible side effects.

Bad uses:

- copying text;
- starting a harmless local task;
- opening a page;
- saving normal settings.

Whenever possible, use an undo pattern for reversible local changes.

---

# 60. Drag and Drop

Where meaningful, support drag and drop for:

- files into composer;
- attachments into a task;
- potentially reordering automation steps.

During drag-over:

- make the drop target clear;
- avoid full-screen flashing;
- keep the interface stable.

---

# 61. File Handling UX

For file-based workflows, support:

- file chips;
- progress for uploads;
- parse status;
- processing state;
- unsupported file type errors;
- retry.

Example:

```text
Q4-report.pdf
Uploaded · Reading

sales.csv
Ready
```

This is more useful than a generic spinner.

---

# 62. Trust and Transparency Layer

The interface should make the assistant's actions inspectable without forcing technical complexity on every user.

A useful pattern is:

```text
Jarvis used
3 files · 1 integration · 2 actions
```

Clicking the summary reveals details.

This provides confidence without exposing implementation details by default.

---

# 63. Activity Timeline

A task timeline may use semantic timestamps.

Example:

```text
09:12  Task created
09:12  Files collected
09:13  Data extracted
09:14  Comparison started
09:15  Approval requested
```

Timeline events should be concise and grouped when possible.

Do not produce an event for every low-level internal operation.

---

# 64. Progress Representation

There are three valid progress patterns:

## Determinate progress

Use when measurable.

```text
62%
██████████████░░░░░
```

## Step progress

Use when stages are known but duration is variable.

```text
✓ Search
✓ Extract
● Compare
○ Report
```

## Indeterminate work

Use when only active state is known.

```text
Working…
```

Never mix all three unnecessarily in the same small component.

---

# 65. Assistant Response States

A response may be:

```text
Queued
Streaming
Complete
Interrupted
Failed
Regenerating
```

Streaming should not cause layout thrashing.

Text should appear naturally, but surrounding action controls should remain stable.

---

# 66. Streaming Behavior

When streaming:

- preserve message width;
- avoid jumping controls;
- keep scroll pinned only when the user is near the bottom;
- stop auto-scrolling if the user manually scrolls upward;
- show a clear stop action when supported.

This is critical for a polished AI chat experience.

---

# 67. Scroll Behavior

Conversation scroll should feel native.

Requirements:

- stable content anchoring;
- no unexpected jumps when images load;
- sticky composer where appropriate;
- jump-to-latest control when the user is away from the bottom.

Example:

```text
          ↓ New activity
```

The control should disappear once the user reaches the latest message.

---

# 68. Long-Running Work and Background Tasks

When the user navigates away from an active task, execution should continue where product architecture permits.

The sidebar can show a subtle indicator:

```text
Tasks    • 2
```

But avoid persistent animated badges.

On return, the user sees the updated task state.

---

# 69. Multi-Task Awareness

The interface should support several concurrent tasks without becoming a monitoring dashboard.

Home can show a compact active-work stack:

```text
Active work

Reconcile invoices       62%
Morning briefing         Waiting
Research competitors     Running
```

Opening Tasks gives the full operational view.

---

# 70. User Attention Model

The product should prioritize notifications by urgency.

### Level 0 — silent

Internal progress.

### Level 1 — ambient

Completed task visible in app.

### Level 2 — attention

Task needs user input.

### Level 3 — critical

Important failure or external action requiring immediate review.

This avoids training users to ignore notifications.

---

# 71. Desktop Notification Integration

Native notifications should be used selectively.

Good examples:

> Morning briefing is ready.

> Jarvis needs your approval to send 14 emails.

Bad examples:

> Step 7 complete.

Notifications should summarize the user-relevant outcome, not internal process.

---

# 72. Security-Sensitive Operations

Actions involving external systems, accounts, payments, destructive changes, or sensitive data should receive stronger visual treatment.

The UI should:

- identify the target;
- summarize impact;
- allow review;
- provide explicit approval.

Avoid vague:

> Continue?

Prefer:

> Send the final report to 8 recipients?

---

# 73. Data Privacy UX

The Data & Privacy area should clearly explain:

- what is stored;
- what is remembered;
- what is synced;
- which external services are connected;
- how the user can delete data.

Keep explanations plain-language.

---

# 74. Design for Failure

A product often feels polished because its failures are polished.

Every major feature needs:

- empty state;
- loading state;
- permission state;
- success state;
- partial success state;
- error state;
- recovery state.

For example, if a five-step task succeeds on four steps:

> Completed with 1 issue
>
> 4 of 5 steps completed. The email connection expired before the final send.
>
> [Reconnect] [Review result]

Do not simply label the task "Failed" when useful work already exists.

---

# 75. Partial Completion UX

Partial results are valuable and should be preserved.

The UI can show:

```text
Completed with issues

✓ Research completed
✓ Summary generated
✓ Report saved
× Email delivery failed

[Open report] [Reconnect email]
```

This reinforces Jarvis as a productive system rather than a binary success/failure machine.

---

# 76. Undo Patterns

Whenever an action is reversible and low risk, prefer an undo pattern.

Example:

> Conversation archived. Undo

This reduces confirmation fatigue.

---

# 77. Confirmation Fatigue Rules

Do not ask the user repeatedly for decisions that have already been established by a policy.

Instead provide policy controls and clear review paths.

For example:

> Use my approved file connection for this automation.

Then only escalate when the requested operation exceeds the policy.

---

# 78. Visual Density Modes

The app can support two density modes without redesigning the product.

## Comfortable

Default.

- larger gaps;
- easier scanning;
- generous task cards.

## Compact

For power users.

- reduced row heights;
- tighter lists;
- more visible content.

Never compress typography below comfortable readability simply to fit more rows.

---

# 79. Search and Filter Patterns

Filters should be contextual.

Tasks can support:

```text
Status   All / Running / Waiting / Complete / Failed
Date     Any / Today / Week / Month
```

Automations can support:

```text
Status   All / Enabled / Paused / Error
```

Avoid a universal filter toolbar on every page.

---

# 80. Information Hierarchy Rules

Each screen should answer three questions in order:

1. **Where am I?**
2. **What matters here?**
3. **What can I do next?**

If a screen fails these questions, redesign the hierarchy before adding visual decoration.

---

# 81. Page Header Standard

Every secondary page should follow a common header model:

```text
[Page title]
Short description

[Primary action]                 [Secondary actions]
```

Example:

> Automations
> Workflows that run for you automatically.
>
> [New automation]

This creates consistency across the application.

---

# 82. List-to-Detail Pattern

Tasks, automations, integrations, and memory should use a consistent list-to-detail interaction model.

Desktop:

```text
List                 Detail
────────────────     ─────────────────────
Item A               Item A
Item B               Description
Item C               Status
                     Actions
```

On narrower windows, detail becomes an overlay or separate route.

---

# 83. Modal and Sheet Usage

Use modals for focused decisions.

Use side sheets for contextual detail.

Use full-page navigation for complex editing.

Examples:

- approval → modal/sheet;
- task details → side sheet;
- automation editor → full page;
- settings category → full page.

This distinction keeps navigation predictable.

---

# 84. Design Language for Future Features

New features should inherit the same grammar:

- neutral surfaces;
- consistent spacing;
- restrained accent;
- progressive disclosure;
- assistant presence without mascot dominance;
- clear state communication;
- contextual actions.

If a future feature requires an entirely different visual language, that is a signal that the feature's information architecture may be wrong.

---

# 85. Implementation Priorities

The redesign should be implemented in layers rather than as a single giant visual rewrite.

## Phase 1 — Foundation

Build:

- app shell;
- design tokens;
- sidebar;
- typography;
- button/input primitives;
- surface system;
- responsive structure;
- command palette.

## Phase 2 — Core assistant experience

Build:

- home;
- conversation workspace;
- composer;
- message components;
- companion;
- streaming states.

## Phase 3 — Execution model

Build:

- task cards;
- task detail;
- approvals;
- progress states;
- recovery/error states.

## Phase 4 — Product surfaces

Build:

- automations;
- memory;
- integrations;
- settings.

## Phase 5 — Polish

Build:

- motion refinement;
- keyboard shortcuts;
- reduced-motion support;
- visual QA;
- edge states;
- performance optimization.

---

# 86. Design Implementation Order

The exact order inside each phase should be:

```text
1. Tokens
2. Layout primitives
3. Core components
4. States
5. Screen composition
6. Data wiring
7. Motion
8. Accessibility
9. Visual QA
```

Do not start with elaborate animations before the underlying states are correct.

---

# 87. Acceptance Criteria — App Shell

The app shell passes when:

- navigation remains clear at desktop sizes;
- active state is obvious;
- sidebar can collapse;
- settings/profile access is discoverable;
- spacing and typography are consistent;
- shell remains visually quiet behind content.

---

# 88. Acceptance Criteria — Home

Home passes when:

- the primary composer is immediately visible;
- quick actions are understandable;
- active tasks are visible when present;
- the screen feels useful without data;
- no oversized dashboard decoration is required.

---

# 89. Acceptance Criteria — Conversation

Conversation passes when:

- messages are readable;
- assistant identity is clear;
- user messages are distinct without excessive bubbles;
- streaming is stable;
- long responses remain readable;
- composer stays accessible;
- active tasks can be inspected.

---

# 90. Acceptance Criteria — Tasks

Tasks pass when:

- running state is unmistakable;
- current step is visible;
- paused/attention states are clear;
- failed tasks explain recovery;
- partial results are preserved;
- task history is searchable.

---

# 91. Acceptance Criteria — Automations

Automations pass when:

- trigger is understandable;
- actions are editable;
- next run is visible;
- disabled state is clear;
- execution history is inspectable;
- permissions are understandable.

---

# 92. Acceptance Criteria — Companion

The companion passes when:

- it is recognizable as Jarvis;
- it is visually distinctive without being childish;
- state changes are understandable;
- idle animation is subtle;
- it never blocks important content;
- reduced motion is respected.

---

# 93. Acceptance Criteria — Overall Product Feel

The most important qualitative acceptance test is:

> **Does this look like a real software product someone could use every day?**

A successful redesign should feel:

- composed;
- mature;
- coherent;
- fast;
- purposeful;
- technically capable;
- trustworthy.

It should not feel like a concept animation translated directly into HTML.

---

# 94. Anti-Patterns to Reject During Development

The following should trigger review:

### Giant hero mascot

Reject unless used in onboarding or marketing.

### Excessive glassmorphism

Reject if transparency reduces clarity or appears on every surface.

### Neon everywhere

Reject if accent color competes with content.

### Card overload

Reject when every paragraph is placed inside a card.

### Dashboard syndrome

Reject decorative metrics that do not help the user decide or act.

### Hidden state

Reject if a background task looks indistinguishable from an idle state.

### Confirmation spam

Reject repeated prompts for the same approved operation.

### Generic error

Reject "Something went wrong" without recovery guidance.

### Technical-first copy

Reject internal implementation language in primary user-facing surfaces.

---

# 95. Visual Regression Strategy

The design system should be supported by screenshot-based visual regression for stable components and key screens.

Prioritize:

- AppShell;
- Home;
- Conversation;
- Composer;
- TaskCard;
- ApprovalSheet;
- AutomationDetail;
- IntegrationCard;
- Settings.

Review regressions at both normal and compact desktop widths.

---

# 96. Performance Expectations

The redesign should not introduce UI lag because of decorative effects.

Avoid:

- expensive continuous blur;
- large DOM animations;
- repeated layout calculation during streaming;
- unnecessary rerendering of long conversations;
- giant always-mounted hidden panels.

For large conversations, use virtualization or incremental rendering where justified.

---

# 97. Rendering Stability

The UI must remain stable while content changes dynamically.

Examples:

- assistant streaming should not constantly resize unrelated elements;
- task progress updates should not change card height unnecessarily;
- integration reconnecting should preserve layout;
- notifications should not push primary content unexpectedly.

Predictability is part of polish.

---

# 98. Error Logging vs User Messaging

Internal logs and user-facing errors should be separate.

Internal example:

```text
connector=google_mail
status=401
refresh_token_invalid=true
retryable=false
```

User-facing:

> Your Gmail connection expired.
>
> Reconnect it to continue.

[Reconnect]

Both are necessary, but they serve different audiences.

---

# 99. Developer Handoff Requirements

For every screen/component, the implementation handoff should specify:

- purpose;
- hierarchy;
- responsive behavior;
- interactive states;
- empty state;
- loading state;
- error state;
- keyboard behavior;
- accessibility label requirements;
- animation rules.

A screenshot alone is not enough to implement this product consistently.

---

# 100. Screen Inventory

The final implementation should account for at least the following surfaces:

1. Splash/loading
2. First-run onboarding
3. Home — empty
4. Home — active work
5. New conversation
6. Conversation — normal
7. Conversation — streaming
8. Conversation — long response
9. Conversation — task active
10. Conversation — approval required
11. Conversation — task failed
12. Tasks — empty
13. Tasks — active
14. Tasks — needs input
15. Tasks — completed
16. Task detail
17. Automations — empty
18. Automations — list
19. Automation editor
20. Automation execution history
21. Memory — list
22. Memory detail/edit
23. Integrations — list
24. Integration detail
25. Integration reconnect state
26. Settings — main
27. Settings — appearance
28. Settings — assistant
29. Settings — memory
30. Settings — permissions
31. Settings — data/privacy
32. Global search
33. Command palette
34. Notification/attention states
35. Advanced diagnostics

This inventory prevents the redesign from only polishing the happy-path home screen.

---

# 101. Recommended Navigation Labels

Use a concise vocabulary.

```text
Home
New conversation
Tasks
Automations
Memory
Integrations

Recent

Settings
```

Avoid adding additional top-level categories until a feature genuinely needs independent navigation.

---

# 102. Information Architecture Test

A first-time user should be able to answer:

> Where do I chat?

Home/New conversation.

> Where do I see things Jarvis is working on?

Tasks.

> Where do I see recurring behavior?

Automations.

> Where do I manage what Jarvis remembers?

Memory.

> Where do I connect services?

Integrations.

If the user cannot answer these quickly, navigation needs refinement.

---

# 103. Product Identity

Jarvis branding should be subtle inside the application.

The identity system should be expressed through:

- companion geometry;
- typography;
- restrained accent;
- small motion signatures;
- icon treatment;
- voice of copy.

Do not rely on repeatedly writing "JARVIS" in huge type.

The application should remain visually recognizable even when the wordmark is absent.

---

# 104. Companion Brand Rules

The companion should remain consistent across:

- idle state;
- onboarding;
- task execution;
- notifications;
- loading;
- error.

It may change lighting and internal motion but should not transform into completely different creatures or illustrations per state.

---

# 105. Marketing vs Product Visuals

Marketing visuals may be more expressive than the actual product.

The production application should be more restrained.

Do not copy promotional concept art directly into the operational UI.

The product needs to survive daily use.

---

# 106. Microcopy Examples

### Ready state

> What would you like to get done?

### Processing

> Working on it…

### Permission

> Jarvis needs your approval before sending these messages.

### Completion

> Done. The report is ready.

### Partial completion

> Most of the task is complete. One connection needs attention.

### Error

> Jarvis couldn't complete the final step.

### Empty tasks

> Nothing is running right now.

### Empty automations

> Automate something you do repeatedly.

### Empty memory

> No saved memories yet.

---

# 107. Tone Guardrails

Avoid words like:

- super;
- awesome;
- magical;
- futuristic;
- mind-blowing;
- genius;
- wow.

Unless used intentionally in a marketing context.

Operational UI should remain calm and professional.

---

# 108. Future Voice Interface

If voice becomes a first-class interaction mode, the current design should accommodate it without a second product language.

The same companion states can represent voice interaction.

Voice mode could introduce:

```text
Listening
Processing
Speaking
```

The visual identity remains unchanged.

---

# 109. Future Multi-Modal Interaction

The composer should be designed to accept:

- text;
- files;
- images;
- voice;
- structured references.

The interaction model should remain unified.

A user should not feel that each modality opens a different tool.

---

# 110. Future Agent/Tool Expansion

The product should support additional tools without changing the core UI model.

A new tool should appear as:

- a capability available to Jarvis;
- an integration;
- or an execution step.

The user should not need to learn the internal architecture of every agent.

---

# 111. Future Workspace Expansion

The same shell can later support project/workspace context.

For example:

```text
Workspace
  Project A
  Project B
```

But this should only be introduced if users need persistent separation of contexts.

Do not add workspace switching merely because other productivity tools do it.

---

# 112. Design Review Checklist Before Coding

Before implementation begins, verify:

- visual direction is locked;
- companion direction is locked;
- color palette is restrained;
- token system exists;
- navigation labels are fixed;
- screen inventory exists;
- core states are defined;
- task model is understandable;
- approval model is understandable;
- error/recovery patterns are defined.

This prevents repeated redesign during implementation.

---

# 113. Design Review Checklist During Coding

During implementation, review every major screen for:

- spacing consistency;
- typography consistency;
- state completeness;
- keyboard access;
- responsive behavior;
- empty/loading/error states;
- motion consistency;
- companion behavior;
- content hierarchy.

Do not wait until the end to discover that each page implemented a different spacing or card style.

---

# 114. Design Review Checklist Before Release

Before release, perform a complete visual pass rather than checking only functional correctness.

Review:

- 100% zoom;
- larger display scaling;
- compact window;
- long conversation;
- many tasks;
- no tasks;
- no integrations;
- multiple integrations;
- network failure;
- permission denied;
- interrupted task;
- completed task;
- reduced motion.

The product should retain its identity across all of these conditions.

---

# 115. Final Design North Star

The final interface should communicate this feeling:

> **"There is a capable system here, and I can trust it to help me without getting in my way."**

That feeling comes from a combination of:

- a quiet visual foundation;
- strong hierarchy;
- restrained color;
- an abstract assistant companion;
- excellent interaction feedback;
- visible task state;
- progressive disclosure;
- thoughtful permission boundaries;
- polished failure handling;
- consistent motion;
- disciplined component architecture.

The objective is not to make Jarvis look more futuristic.

The objective is to make Jarvis look more **real**.

---

# 116. Implementation Summary

The implementation should be treated as a product redesign rather than a cosmetic restyling.

The core change is architectural at the UX level:

```text
OLD MENTAL MODEL

Chat
 ├─ message
 ├─ message
 ├─ tool output
 └─ message

NEW MENTAL MODEL

Jarvis Workspace
 ├─ Conversation
 │   ├─ Intent
 │   ├─ Response
 │   └─ Context
 │
 ├─ Task
 │   ├─ Plan
 │   ├─ Steps
 │   ├─ Permissions
 │   ├─ Progress
 │   └─ Result
 │
 ├─ Memory
 ├─ Automations
 ├─ Integrations
 └─ Settings
```

Conversation remains the easiest way to interact, while structured product surfaces provide durability and control.

---

# 117. Final Visual Rules — Non-Negotiable

These rules should remain stable during implementation unless there is a deliberate product decision to change them.

1. **No oversized cartoon pet.**
2. **No neon-heavy cyberpunk treatment.**
3. **No full-screen decorative gradients behind the main workspace.**
4. **No card around every piece of content.**
5. **No hidden long-running task state.**
6. **No generic error states without recovery.**
7. **No repeated confirmation prompts for already-approved workflows.**
8. **No technical implementation language in primary user-facing copy.**
9. **No uncontrolled continuous animation.**
10. **No page should depend on decoration to feel complete.**

---

# 118. Final Product Rules — Non-Negotiable

1. The user always knows where they are.
2. The user can always tell whether Jarvis is idle or working.
3. The user can always see when Jarvis needs input.
4. Consequential actions require an understandable approval boundary.
5. Completed work remains discoverable.
6. Failed work explains how to recover.
7. User control over memory and integrations is easy to find.
8. The primary interaction remains fast.
9. Advanced information remains available without dominating the default UI.
10. The whole application uses one consistent visual system.

---

# 119. Final Screen-Level Direction

## Home

Premium, spacious, task-oriented command center.

## Conversation

Editorial, readable, intelligent, with a strong but quiet assistant identity.

## Tasks

Operational clarity without enterprise-dashboard density.

## Automations

Structured and approachable, with natural-language entry and editable configuration.

## Memory

Human-readable control over persistent context.

## Integrations

Clear capabilities and permissions.

## Settings

Simple organization with deeper technical controls tucked away.

## Companion

Abstract, premium, restrained, state-aware.

---

# 120. Definition of Done

The Jarvis UI revamp is complete when:

### Visual

- the old UI no longer feels like the same product with new colors;
- the application has a distinctive, coherent visual identity;
- the companion feels integrated instead of pasted on;
- spacing and typography feel intentional;
- the interface looks polished at standard desktop sizes.

### UX

- chat, tasks, automations, memory, integrations, and settings form one coherent system;
- task execution is visible and understandable;
- approvals are contextual;
- errors are recoverable;
- the product is useful with no data and useful with lots of data.

### Engineering

- components use shared tokens;
- states are explicit;
- navigation is reusable;
- persistent work can be resumed;
- motion is performant;
- keyboard navigation works;
- reduced-motion behavior works;
- visual regression coverage exists for critical screens.

### Product feeling

A new user should look at the application and understand within seconds:

> This is not just another chat window.
>
> This is an AI desktop workspace built to actually get things done.

---

# Appendix A — Suggested Token Reference

```css
:root {
  --bg-app: #0D0F12;
  --bg-sidebar: #111419;
  --bg-surface: #15181D;
  --bg-surface-elevated: #1A1E24;
  --bg-hover: #1E232A;
  --bg-pressed: #232831;

  --text-primary: #F1F3F5;
  --text-secondary: #A8AFB8;
  --text-tertiary: #717984;
  --text-disabled: #4C535D;

  --border-subtle: rgba(255,255,255,.07);
  --border-default: rgba(255,255,255,.10);
  --border-strong: rgba(255,255,255,.16);

  --accent: #8E8CFF;
  --accent-hover: #A7A5FF;
  --accent-strong: #7571F4;
  --accent-soft: rgba(142,140,255,.14);

  --success: #5FCB91;
  --warning: #E9B95A;
  --danger: #E57070;
  --info: #71A9E8;

  --radius-xs: 6px;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-pill: 999px;

  --shadow-sm: 0 2px 8px rgba(0,0,0,.20);
  --shadow-md: 0 10px 30px rgba(0,0,0,.28);
  --shadow-lg: 0 20px 60px rgba(0,0,0,.36);
}
```

---

# Appendix B — Example Component State Matrix

| Component | Default | Hover | Focus | Loading | Success | Error | Disabled |
|---|---|---|---|---|---|---|---|
| Button | ✓ | ✓ | ✓ | ✓ | optional | optional | ✓ |
| Input | ✓ | ✓ | ✓ | optional | optional | ✓ | ✓ |
| Composer | ✓ | — | ✓ | ✓ | optional | ✓ | optional |
| Task card | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | optional |
| Integration card | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | optional |
| Automation row | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Memory item | ✓ | ✓ | ✓ | optional | ✓ | optional | optional |
| Companion | ✓ | — | — | ✓ | ✓ | ✓ | ✓ |

---

# Appendix C — Suggested Keyboard Map

| Shortcut | Action |
|---|---|
| Ctrl/Cmd + K | Search / command palette |
| Ctrl/Cmd + N | New conversation |
| Ctrl/Cmd + Shift + F | Search current conversation |
| Ctrl/Cmd + Enter | Send composer where applicable |
| Escape | Close modal/palette / cancel current transient action |
| Enter | Confirm selected action |
| Up/Down | Navigate suggestions |
| Ctrl/Cmd + , | Open Settings |

Shortcut availability should respect platform conventions.

---

# Appendix D — Screen Review Template

Use this for every new screen:

```markdown
## Screen name

### Purpose
What user goal does this screen support?

### Primary action
What should the user most likely do?

### Secondary actions
What supporting actions are available?

### Empty state
What does the user see with no data?

### Loading state
How is uncertainty communicated?

### Success state
What does completion look like?

### Partial state
What happens if some work succeeds?

### Error state
How is recovery presented?

### Keyboard
Which shortcuts and focus paths are supported?

### Responsive behavior
How does the screen change at narrower widths?

### Accessibility
What labels, announcements, and contrast rules apply?

### Motion
What animates, and why?
```

---

# Appendix E — Final Direction in One Paragraph

Jarvis should become a quiet, premium desktop AI workspace with a graphite foundation, restrained cool accent, strong typography, spacious composition, and subtle motion. Conversation remains the fastest entry point, but tasks, automations, memory, integrations, and approvals are treated as first-class product surfaces. The assistant identity is represented by an abstract adaptive companion rather than an animal mascot, allowing the product to feel intelligent and sophisticated without becoming playful or distracting. Every important operation communicates state, permissions are contextual, errors are recoverable, and advanced technical details are available through progressive disclosure. The result should feel less like a redesigned chatbot and more like a mature desktop product built around an AI assistant.

---

# End of Specification

**Document:** Jarvis Desktop UI Revamp — Product UI Master Specification  
**Status:** Ready for implementation planning and frontend decomposition
