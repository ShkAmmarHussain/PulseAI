import os
import shutil
from pathlib import Path


def _resolve(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser((p or "").strip().strip('"'))))


def delete_path(target: str) -> str:
    p = _resolve(target)
    if not str(p).strip():
        return "Failed: no path specified."
    if not p.exists():
        return f"Failed: '{p}' does not exist."
    if str(p).lower().rstrip("\\") in (str(Path(p.anchor)).lower().rstrip("\\"), "c:\\", "c:"):
        return "Failed: refusing to delete a drive root."
    if p.is_dir():
        shutil.rmtree(p)
        return f"Deleted folder {p} and its contents."
    p.unlink()
    return f"Deleted file {p}."


def list_dir(target: str = ".") -> str:
    p = _resolve(target)
    if not p.exists():
        return f"Failed: '{p}' does not exist."
    if p.is_file():
        return str(p)
    entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    lines = [f"{'[DIR] ' if e.is_dir() else ''}{e.name}" for e in entries[:40]]
    more = f"\n... and {len(entries) - 40} more" if len(entries) > 40 else ""
    return f"Contents of {p}:\n" + "\n".join(lines) + more


def move_file(src: str, dst: str) -> str:
    s, d = _resolve(src), _resolve(dst)
    if not s.exists():
        return f"Failed: '{s}' does not exist."
    if d.is_dir():
        d = d / s.name
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return f"Moved {s} -> {d}."


def create_file(path: str, content: str = "") -> str:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created {p}."


TEXT_EXTS = (
    ".txt", ".md", ".rst", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".xml", ".html", ".htm", ".css", ".js", ".ts",
    ".jsx", ".tsx", ".py", ".rs", ".go", ".java", ".kt", ".c", ".h", ".cpp",
    ".hpp", ".cs", ".rb", ".php", ".sh", ".ps1", ".bat", ".sql", ".r",
    ".swift", ".scala", ".lua", ".pl", ".dockerfile", ".gitignore", ".env",
    ".txtx", ".tex",
)
READ_MAX_BYTES = 400_000


def read_text(path: str, max_bytes: int = READ_MAX_BYTES) -> str:
    """Read a text/code file (and basic PDF extraction) for summarization."""
    p = _resolve(path)
    if not str(p).strip():
        return "Failed: no path specified."
    if not p.is_file():
        return f"File not found: {p}"
    if p.suffix.lower() == ".pdf":
        try:
            import io

            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(p.read_bytes()))
            pages = [(pg.extract_text() or "") for pg in reader.pages[:40]]
            text = "\n".join(pages).strip()
            if not text:
                return f"PDF '{p.name}' has no extractable text ({len(reader.pages)} pages)."
            return text[:max_bytes]
        except ImportError:
            return f"PDF '{p.name}': text extraction unavailable (pypdf not installed)."
        except Exception as e:
            return f"Failed to read PDF '{p.name}': {e}"
    data = p.read_bytes()[:max_bytes]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")
