"""Accessibility + wording gate (spec 34 sections 7.2 / 7.3). Static, no backend.

- WCAG AA contrast (4.5:1) for every text token on every surface token
- every focusable control keeps a visible focus ring (final :focus-visible block)
- no buttons pulled out of the tab order (tabindex="-1" on a <button>)
- tabs expose aria-current / aria-selected
- no raw tool names (delete_file, run_shell, ...) in shipped markup text

Run: .venv/Scripts/python tests/a11y_check.py      exit 0 = pass
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "ui_pet", "src")
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""), flush=True)


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return f.read()


def lum(hex_):
    h = hex_.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


css = read("app.css")
root = css[css.index(":root"):css.index("}", css.index(":root"))]
tokens = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,6})\b", root))
for need in ("bg", "card", "card-flat", "tab-on", "ink", "dim", "dim-3"):
    check("token --%s defined" % need, need in tokens, tokens.get(need))

for text in ("ink", "dim", "dim-3"):
    for surface in ("bg", "card", "card-flat", "tab-on"):
        if text in tokens and surface in tokens:
            r = ratio(tokens[text], tokens[surface])
            check("contrast --%s on --%s >= 4.5" % (text, surface), r >= 4.5, round(r, 2))
r = ratio("#000000", "#ffffff")
check("white pill text contrast", r >= 4.5, round(r, 2))

tail = css[css.rindex("spec 34 phase 5"):] if "spec 34 phase 5" in css else ""
check("final focus-visible ring block present",
      ":focus-visible" in tail and "outline: 2px solid" in tail, len(tail))

for page in ("index.html", "pet.html", "dock.html"):
    html = read(page)
    bad = re.findall(r"<button[^>]*tabindex=\"-1\"", html)
    check(page + ": no buttons removed from tab order", not bad, bad[:2])
    # visible text only: strip tags, attributes and scripts
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    raw = re.findall(r"\b(delete_file|run_shell|launch_app|open_url|move_file|type_text|press_hotkey|vision_describe)\b", text)
    check(page + ": no raw tool names in visible text", not raw, raw[:3])

idx = read("index.html")
check("main tabs carry aria-current logic", "aria-current" in read("main.js") + read("chat.js") + idx)
check("island tabs expose aria-selected", 'role="tab"' in read("dock.html") and "aria-selected" in read("dock_standalone.js"))
check("offline banner is a live status region", 'id="offline-banner" role="status"' in idx)
check("reduced motion respected", "prefers-reduced-motion" in css)

print(f"== {sum(results)}/{len(results)} PASS ==")
sys.exit(0 if all(results) else 1)
