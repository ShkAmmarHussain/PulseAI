# Attributions

## coucou (MIT)

The spec 34 redesign of Jarvis adapts ideas and structure, but no artwork, from **coucou** (https://github.com/Louis-CFM/coucou):

- the dark design tokens (black chrome, `--card` / `--card-flat` / `--tab-on` surfaces, a single hairline border, state glows at a card's bottom edge, one white-pill primary action per surface, key caps for shortcuts);
- the top-edge island model: a hidden wake strip, a compact pill and an expanded surface with a tab header and one card per state (overview, approval, question, result, error, chat), plus the "catch the file" drop;
- keeping cloud API keys in the operating system's credential store rather than on disk.

The adapted code in this repository is written for Jarvis (HTML/CSS/JS on Tauri v1 and a Python backend). coucou's code is credited here under its licence:

```
MIT License

Copyright (c) 2026 Louis Raillé

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Not covered: name, character and artwork

coucou's `LICENSE-ASSETS.md` keeps the names "Coucou" and "Mochi", the Mochi character design, its icons, sounds and media outside the MIT licence. Jarvis uses none of coucou's assets. Its companion is **Pip** (spec 34 section 1.1): Jarvis's own name and design, a cream egg-shaped body with a single antenna-sprout and a warm amber core light, drawn for Jarvis in SVG (`pet.html`, `index.html`, `dock.html`) and Three.js (`pet3d.js`). The earlier bunny-eared "Mochi" look and name were retired in this change.
