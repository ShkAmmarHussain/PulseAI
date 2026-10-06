"""Notifications for timers/reminders (spec 32, section 3.1).

- ``chime``  : short blocking Windows beep triplet (fallback alert).
- ``toast``  : Windows toast notification; prefers ``winotify`` when
               installed, otherwise shells out to PowerShell's runtime
               toast API, otherwise fails quietly (the chat entry and the
               spoken line already carry the message).

All functions are synchronous and thread-safe: the task manager calls them
through ``asyncio.to_thread`` so the event loop never blocks.
"""

import logging
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)


def chime() -> bool:
    """Audible 3-note chime. Returns True when it actually played."""
    if sys.platform != "win32":
        return False
    try:
        import winsound

        for freq, ms in ((880, 150), (1174, 150), (1568, 320)):
            winsound.Beep(freq, ms)
        return True
    except Exception:
        logger.exception("chime failed")
        return False


def _toast_winotify(title: str, message: str) -> bool:
    try:
        from winotify import Notification, audio
    except Exception:
        return False
    try:
        toast = Notification(
            app_id="Jarvis",
            title=title,
            msg=message,
            icon="",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return True
    except Exception:
        logger.exception("winotify toast failed")
        return False


_PS_TOAST = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$template = '<toast><visual><binding template="ToastGeneric"><text>{0}</text><text>{1}</text></binding></visual></toast>'
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(($template -f $args[0].Replace('<','(').Replace('>',')'), $args[1].Replace('<','(').Replace('>',')')))
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Jarvis').Show($toast)
"""


def _toast_powershell(title: str, message: str) -> bool:
    if shutil.which("powershell") is None:
        return False
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_TOAST, title, message],
            capture_output=True,
            timeout=12,
        )
        return True
    except Exception:
        logger.exception("powershell toast failed")
        return False


def toast(title: str, message: str) -> bool:
    """Best-effort Windows toast. Never raises."""
    if sys.platform != "win32":
        return False
    try:
        if _toast_winotify(title, message):
            return True
        return _toast_powershell(title, message)
    except Exception:
        logger.exception("toast failed")
        return False


def alert(title: str, message: str, speak=None) -> None:
    """Combined reminder alert: toast + chime (+ optional speak callback)."""
    toast(title, message)
    chime()
    if speak:
        try:
            speak(f"{title}: {message}")
        except Exception:
            logger.exception("alert speak failed")
