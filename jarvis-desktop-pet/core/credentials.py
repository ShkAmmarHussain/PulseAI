"""Cloud API keys in Windows Credential Manager (spec 34 section 7.6).

config.yaml keeps only a reference (llm.<provider>.api_key_ref); the key itself
lives in a generic credential named "PulseAI/llm.<provider>". Talks to
advapi32 through ctypes, so there is no extra dependency and it works in the
frozen backend. Off Windows every call is a no-op and keys stay in the config.
"""

import ctypes
import logging
import os
from ctypes import wintypes as wt

logger = logging.getLogger("credentials")

PREFIX = "PulseAI/"
REF_SCHEME = "wincred:"
PROVIDERS = ("openai", "anthropic")
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168


class _CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wt.DWORD),
        ("Type", wt.DWORD),
        ("TargetName", wt.LPWSTR),
        ("Comment", wt.LPWSTR),
        ("LastWritten", wt.FILETIME),
        ("CredentialBlobSize", wt.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wt.DWORD),
        ("AttributeCount", wt.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wt.LPWSTR),
        ("UserName", wt.LPWSTR),
    ]


_api = None


def _advapi():
    global _api
    if _api is None:
        api = ctypes.WinDLL("advapi32", use_last_error=True)
        api.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIAL), wt.DWORD]
        api.CredWriteW.restype = wt.BOOL
        api.CredReadW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.POINTER(ctypes.POINTER(_CREDENTIAL))]
        api.CredReadW.restype = wt.BOOL
        api.CredDeleteW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD]
        api.CredDeleteW.restype = wt.BOOL
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredFree.restype = None
        _api = api
    return _api


def available() -> bool:
    return os.name == "nt"


def target(name: str) -> str:
    return PREFIX + name


def write(name: str, secret: str) -> bool:
    if not available():
        return False
    blob = secret.encode("utf-16-le")
    buf = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    cred = _CREDENTIAL()
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = target(name)
    cred.Comment = "PulseAI API key"
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = "PulseAI"
    ok = bool(_advapi().CredWriteW(ctypes.byref(cred), 0))
    if not ok:
        logger.warning("CredWriteW failed for %s (error %s)", name, ctypes.get_last_error())
    return ok


def read(name: str) -> str:
    if not available():
        return ""
    p = ctypes.POINTER(_CREDENTIAL)()
    if not _advapi().CredReadW(target(name), CRED_TYPE_GENERIC, 0, ctypes.byref(p)):
        err = ctypes.get_last_error()
        if err != ERROR_NOT_FOUND:
            logger.warning("CredReadW failed for %s (error %s)", name, err)
        return ""
    try:
        c = p.contents
        raw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
        return raw.decode("utf-16-le")
    finally:
        _advapi().CredFree(p)


def delete(name: str) -> bool:
    if not available():
        return False
    return bool(_advapi().CredDeleteW(target(name), CRED_TYPE_GENERIC, 0))


# ---- config references -----------------------------------------------------
def ref_for(provider: str) -> str:
    return REF_SCHEME + target("llm." + provider)


def name_from_ref(ref: str) -> str:
    ref = str(ref or "")
    if not ref.startswith(REF_SCHEME + PREFIX):
        return ""
    return ref[len(REF_SCHEME + PREFIX):]


def resolve(section: dict) -> str:
    """The key for one llm.<provider> section: inline value first, then the ref."""
    section = section or {}
    key = str(section.get("api_key") or "").strip()
    if key:
        return key
    name = name_from_ref(section.get("api_key_ref"))
    return read(name).strip() if name else ""


def store_config_keys(cfg: dict) -> bool:
    """Move inline llm.<provider>.api_key values into Credential Manager.

    Mutates cfg: the key is blanked and api_key_ref set. api_key_clear: true
    forgets a stored key. The computed api_key_saved flag (sent to the UI) is
    never persisted. Returns True when cfg changed.
    """
    llm = (cfg or {}).get("llm")
    if not isinstance(llm, dict):
        return False
    changed = False
    for provider in PROVIDERS:
        sec = llm.get(provider)
        if not isinstance(sec, dict):
            continue
        if sec.pop("api_key_saved", None) is not None:
            changed = True
        if sec.pop("api_key_clear", False):
            delete("llm." + provider)
            sec.pop("api_key_ref", None)
            sec["api_key"] = ""
            changed = True
            continue
        key = str(sec.get("api_key") or "").strip()
        if key and available():
            if write("llm." + provider, key):
                sec["api_key"] = ""
                sec["api_key_ref"] = ref_for(provider)
                changed = True
    return changed


def annotate_saved(cfg: dict) -> dict:
    """Add api_key_saved: bool per provider so the UI can say a key is stored."""
    llm = (cfg or {}).get("llm")
    if isinstance(llm, dict):
        for provider in PROVIDERS:
            sec = llm.get(provider)
            if isinstance(sec, dict):
                sec["api_key_saved"] = bool(resolve(dict(sec, api_key="")))
    return cfg
