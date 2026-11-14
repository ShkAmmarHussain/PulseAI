import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__" and "--run-skill" in sys.argv:
    # packaged builds run Mini World skills through the backend exe itself
    # (doc 37 sprint 8): a separate, short-lived process in a throwaway folder
    from core.world.skills_lab import run_skill_main

    sys.exit(run_skill_main())

from backend.app import App  # noqa: E402


def setup_logging() -> None:
    log_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "JarvisDesktopPet"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / "backend.log", maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def watch_parent() -> None:
    """Exit when the UI that spawned us is gone, even if it crashed (docs/35 L8).

    The Tauri shell passes its pid in JARVIS_PARENT_PID; a backend started by
    hand has no parent to watch.
    """
    pid = os.environ.get("JARVIS_PARENT_PID", "").strip()
    if not pid.isdigit() or os.name != "nt":
        return
    import ctypes
    import threading

    SYNCHRONIZE = 0x00100000
    INFINITE = 0xFFFFFFFF
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = ctypes.c_void_p
    handle = k32.OpenProcess(SYNCHRONIZE, False, int(pid))
    log = logging.getLogger("backend")
    if not handle:
        log.warning("parent pid %s not found; exiting", pid)
        os._exit(0)

    def wait():
        k32.WaitForSingleObject(ctypes.c_void_p(handle), INFINITE)
        log.info("parent %s exited; shutting down", pid)
        os._exit(0)

    threading.Thread(target=wait, name="parent-watch", daemon=True).start()


async def main():
    setup_logging()
    watch_parent()
    logging.getLogger("backend").info("starting jarvis backend")
    try:
        from backend.ws_bridge import migrate_config_keys

        migrate_config_keys()
    except Exception:  # never block startup on the key store
        logging.getLogger("backend").exception("API key migration failed")
    app = App()
    await app.start()
    logging.getLogger("backend").info("all systems running")
    try:
        await asyncio.Event().wait()
    finally:
        await app.bus.stop()
        for a in app.agents.values():
            try:
                await a.stop()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())