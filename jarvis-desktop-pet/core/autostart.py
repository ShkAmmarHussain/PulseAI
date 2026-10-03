import logging
import sys
from pathlib import Path

logger = logging.getLogger("backend")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "JarvisDesktopPet"


def _exe_path():
    if not getattr(sys, "frozen", False):
        return None
    p = Path(sys.executable).resolve().parent / "JarvisDesktopPet.exe"
    return p if p.exists() else None


def _command(exe):
    return f'"{exe}" --hidden'


def get_autostart() -> dict:
    exe = _exe_path()
    if exe is None:
        return {"enabled": False, "available": False}
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            try:
                stored, _ = winreg.QueryValueEx(key, VALUE_NAME)
            except FileNotFoundError:
                stored = None
        return {"enabled": bool(stored) and str(exe) in str(stored), "available": True}
    except Exception:
        logger.exception("autostart query failed")
        return {"enabled": False, "available": True}


def set_autostart(enabled: bool, exe=None) -> dict:
    if exe is None:
        exe = _exe_path()
    if exe is None:
        return {"enabled": False, "available": False}
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command(exe))
                logger.info("autostart enabled: %s", _command(exe))
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                    logger.info("autostart disabled")
                except FileNotFoundError:
                    pass
    except Exception:
        logger.exception("autostart write failed")
    if exe == _exe_path():
        return get_autostart()
    return {"enabled": bool(enabled), "available": True}
