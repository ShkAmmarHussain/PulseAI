import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000


def launch_app(target: str) -> str:
    t = (target or "").strip().strip('"').strip(".")
    if not t:
        return "Failed: no app specified."
    if t.startswith(("http://", "https://")):
        os.startfile(t)
        return f"Opened {t} in the default browser."
    if os.path.exists(os.path.expandvars(t)):
        os.startfile(os.path.expandvars(t))
        return f"Opened {t}."
    if shutil.which(t):
        subprocess.Popen([t], creationflags=CREATE_NO_WINDOW)
        return f"Launched {t}."
    r = subprocess.run(
        ["cmd", "/c", "start", "", t],
        capture_output=True, text=True, timeout=15, creationflags=CREATE_NO_WINDOW,
    )
    if r.returncode == 0:
        return f"Launched {t}."
    err = (r.stderr or r.stdout or "").strip()
    return f"Failed to open '{t}': {err[:200] or 'app not found'}"


def _is_running(image: str) -> bool:
    r = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {image}"],
        capture_output=True, text=True, timeout=10, creationflags=CREATE_NO_WINDOW,
    )
    return image.lower() in r.stdout.lower()


def close_app(target: str) -> str:
    t = (target or "").strip().strip('"').strip(".")
    if not t:
        return "Failed: no app specified."
    if not t.lower().endswith(".exe"):
        t = t + ".exe"
    r = subprocess.run(
        ["taskkill", "/IM", t],
        capture_output=True, text=True, timeout=15, creationflags=CREATE_NO_WINDOW,
    )
    err = ((r.stderr or "") + (r.stdout or "")).strip().lower()
    if r.returncode != 0 and ("not found" in err or "no running instance" in err):
        return f"{t} is not running."
    import time

    for _ in range(15):
        time.sleep(0.2)
        if not _is_running(t):
            return f"Closed {t}."
    r2 = subprocess.run(
        ["taskkill", "/F", "/IM", t],
        capture_output=True, text=True, timeout=15, creationflags=CREATE_NO_WINDOW,
    )
    if r2.returncode == 0 and not _is_running(t):
        return f"Closed {t} (forced)."
    return f"Failed to close '{t}': {(r.stderr or '').strip()[:200] or 'still running'}"
