import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import App


def setup_logging() -> None:
    log_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "JarvisDesktopPet"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / "backend.log", maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


async def main():
    setup_logging()
    logging.getLogger("backend").info("starting jarvis backend")
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