"""Phonetic vocabulary replacement dictionary (spec 29, section 3.3).

Local Whisper models mishear technical terms ("cube control" for "kubectl").
Mappings from config/vocabulary.json are applied to raw transcription output,
whole-word and case-insensitively, before the text reaches the Orchestrator or
the dictation injector.
"""

import json
import logging
import re
import threading
from pathlib import Path

from core.config import BUNDLED_CONFIG_DIR, CONFIG_DIR

logger = logging.getLogger("stt")

VOCAB_NAME = "vocabulary.json"
DEFAULT_MAPPINGS = [
    {"word": "kubectl", "heard_as": ["cube control", "cube ctl", "koob ctl", "cube cuddle"]},
    {"word": "Claude Code", "heard_as": ["cloud code", "clawed code", "claud code"]},
    {"word": "LM Studio", "heard_as": ["element studio", "lm studio", "ellen studio"]},
    {"word": "Antigravity", "heard_as": ["anti gravity", "anti-gravity", "agy"]},
]

_lock = threading.Lock()
_cache = {"key": None, "patterns": None}


def vocabulary_path() -> Path:
    """User config copy if present, else the bundled file, else the user path
    (which is where saves go)."""
    user = CONFIG_DIR / VOCAB_NAME
    if user.exists():
        return user
    bundled = BUNDLED_CONFIG_DIR / VOCAB_NAME
    if bundled.exists():
        return bundled
    return user


def load_vocabulary(path: Path = None) -> list:
    p = Path(path) if path is not None else vocabulary_path()
    try:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            mappings = data.get("mappings")
            if isinstance(mappings, list):
                return mappings
    except Exception:
        logger.exception("vocabulary load failed (%s)", p)
    return [dict(m) for m in DEFAULT_MAPPINGS]


def save_vocabulary(mappings: list, path: Path = None) -> Path:
    p = Path(path) if path is not None else (CONFIG_DIR / VOCAB_NAME)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"mappings": mappings if isinstance(mappings, list) else []}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with _lock:
        _cache["key"] = None
    logger.info("vocabulary saved: %d mapping(s) -> %s", len(mappings or []), p)
    return p


def _compile(mappings: list) -> list:
    pats = []
    for m in mappings if isinstance(mappings, list) else []:
        if not isinstance(m, dict):
            continue
        word = str(m.get("word") or "").strip()
        heard = m.get("heard_as")
        if not word or not isinstance(heard, list):
            continue
        for h in heard:
            h = str(h or "").strip()
            if not h:
                continue
            parts = [p for p in re.split(r"[\s\-]+", h) if p]
            if not parts:
                continue
            body = r"[\s\-]+".join(re.escape(p) for p in parts)
            try:
                pats.append((re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE), word))
            except re.error:
                logger.warning("vocabulary: bad pattern %r skipped", h)
    # longest phrase first so multi-word forms win over shorter prefixes
    pats.sort(key=lambda pr: len(pr[0].pattern), reverse=True)
    return pats


def apply_vocabulary(text: str, mappings: list = None) -> str:
    """Replace phonetic misrecognitions with their canonical words."""
    if not text:
        return text
    if mappings is None:
        p = vocabulary_path()
        try:
            key = (str(p), p.stat().st_mtime if p.exists() else 0)
        except OSError:
            key = (str(p), 0)
        with _lock:
            if _cache["key"] != key:
                _cache["patterns"] = _compile(load_vocabulary(p))
                _cache["key"] = key
            pats = _cache["patterns"]
    else:
        pats = _compile(mappings)
    out = text
    for pat, word in pats:
        out = pat.sub(lambda _m, w=word: w, out)
    return out
