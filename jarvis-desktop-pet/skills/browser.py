import os


def open_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return "Failed: no URL specified."
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    os.startfile(u)
    return f"Opened {u} in the default browser."
