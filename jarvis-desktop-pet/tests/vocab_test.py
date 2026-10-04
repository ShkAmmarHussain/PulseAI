"""Phonetic vocabulary replacement engine tests (spec 29, section 3.3).

Run: .venv/Scripts/python tests/vocab_test.py   (exit 0 = pass)
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.stt import DEFAULT_MAPPINGS, apply_vocabulary, load_vocabulary, save_vocabulary

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def main():
    # bundled / default file loads and has the spec's four mappings
    mappings = load_vocabulary()
    check("vocabulary file loads", isinstance(mappings, list) and len(mappings) >= 4, len(mappings))
    words = [m.get("word") for m in mappings]
    check("spec mappings present", all(w in words for w in ("kubectl", "Claude Code", "LM Studio", "Antigravity")), words)

    # basic replacement
    out = apply_vocabulary("deploy with cube control please", mappings)
    check("basic replacement", out == "deploy with kubectl please", out)

    # case-insensitive, canonical casing wins
    out = apply_vocabulary("Cube Control get pods", mappings)
    check("case-insensitive + canonical word", out == "kubectl get pods", out)

    # whole-word only: substrings untouched
    out = apply_vocabulary("the cubed controller idea", mappings)
    check("no substring matches", out == "the cubed controller idea", out)
    out = apply_vocabulary("mycube control tower", mappings)
    check("no mid-word matches", out == "mycube control tower", out)

    # hyphen/space variants of the same phrase
    out = apply_vocabulary("anti gravity drive", mappings)
    check("space variant", out == "Antigravity drive", out)
    out = apply_vocabulary("anti-gravity drive", mappings)
    check("hyphen variant", out == "Antigravity drive", out)

    # multiple mappings in one sentence
    out = apply_vocabulary("open element studio and run clawed code", mappings)
    check("multiple replacements", out == "open LM Studio and run Claude Code", out)

    # longest phrase wins over a shorter overlapping mapping
    custom = [
        {"word": "LONG", "heard_as": ["alpha beta gamma"]},
        {"word": "SHORT", "heard_as": ["alpha beta"]},
    ]
    out = apply_vocabulary("alpha beta gamma", custom)
    check("longest mapping wins", out == "LONG", out)
    out = apply_vocabulary("alpha beta", custom)
    check("short mapping still fires", out == "SHORT", out)

    # save/load roundtrip at an explicit path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "vocabulary.json"
        save_vocabulary([{"word": "pytest", "heard_as": ["pie test", "py test"]}], path=p)
        loaded = load_vocabulary(path=p)
        check("save/load roundtrip", loaded == [{"word": "pytest", "heard_as": ["pie test", "py test"]}], loaded)
        out = apply_vocabulary("run pie test now", loaded)
        check("roundtripped mapping applies", out == "run pytest now", out)
        raw = json.loads(p.read_text(encoding="utf-8"))
        check("file schema matches spec", isinstance(raw.get("mappings"), list), list(raw.keys()))

    # defaults used when the path is missing entirely
    with tempfile.TemporaryDirectory() as td:
        loaded = load_vocabulary(path=Path(td) / "nope.json")
        check("missing file falls back to defaults", len(loaded) == len(DEFAULT_MAPPINGS), len(loaded))

    # empty / non-string input is a no-op
    check("empty text no-op", apply_vocabulary("", mappings) == "")
    check("None text no-op", apply_vocabulary(None, mappings) is None)

    print(f"== {sum(results)}/{len(results)} PASS ==")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
