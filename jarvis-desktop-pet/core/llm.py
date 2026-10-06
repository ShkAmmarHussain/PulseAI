import asyncio
import logging

import httpx
from openai import OpenAI

logger = logging.getLogger("llm")

DEFAULT_BASE_URL = "http://localhost:1234/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"

PROVIDERS = ("lm_studio", "openai", "anthropic")


def get_llm_cfg(cfg: dict) -> dict:
    return (((cfg or {}).get("config") or {}).get("llm") or {})


def get_provider(cfg: dict) -> str:
    """Active provider: lm_studio | openai | anthropic (spec 33, section 3)."""
    p = str(get_llm_cfg(cfg).get("provider") or "lm_studio").strip().lower()
    return p if p in PROVIDERS else "lm_studio"


def get_api_key(cfg: dict, provider: str) -> str:
    llm_cfg = get_llm_cfg(cfg)
    sec = llm_cfg.get(provider) or {}
    key = str(sec.get("api_key") or "").strip()
    if not key and provider == "lm_studio":
        lm = ((cfg or {}).get("config") or {}).get("lm_studio") or {}
        key = str(lm.get("api_key") or "").strip()
    return key


def get_base_url(cfg: dict, provider: str) -> str:
    llm_cfg = get_llm_cfg(cfg)
    sec = llm_cfg.get(provider) or {}
    url = str(sec.get("base_url") or "").strip().rstrip("/")
    if provider == "openai":
        return url or OPENAI_BASE_URL
    if provider == "anthropic":
        return url or ANTHROPIC_BASE_URL
    lm = ((cfg or {}).get("config") or {}).get("lm_studio") or {}
    return str(sec.get("base_url") or lm.get("base_url") or DEFAULT_BASE_URL)


def _base_url(url: str | None) -> str:
    base = (url or DEFAULT_BASE_URL).strip().rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    # ::1 ("localhost") can blackhole SYNs when nothing listens; IPv4 refuses fast
    if base.lower().startswith("http://localhost"):
        base = "http://127.0.0.1" + base[len("http://localhost"):]
    elif base.lower().startswith("https://localhost"):
        base = "https://127.0.0.1" + base[len("https://localhost"):]
    return base


def _client(lm_cfg: dict, base_url: str | None = None) -> OpenAI:
    return OpenAI(
        base_url=_base_url(base_url or lm_cfg.get("base_url")),
        api_key=lm_cfg.get("api_key") or "lm-studio",
        timeout=(lm_cfg.get("timeout_ms") or 30000) / 1000,
        max_retries=int(lm_cfg.get("max_retries") or 1),
    )


def _openai_client(cfg: dict) -> OpenAI:
    return OpenAI(
        api_key=get_api_key(cfg, "openai") or "missing-key",
        base_url=get_base_url(cfg, "openai"),
        timeout=45.0,
        max_retries=1,
    )


def _model_name(model_id: str) -> str:
    return (model_id or "").strip().removesuffix("-gguf")


_lifecycle = None


def set_lifecycle(lc) -> None:
    """Installed by the app so chat calls load/offload models on demand."""
    global _lifecycle
    _lifecycle = lc


# --------------------------------------------------------------------------
# Anthropic Messages API (native httpx streaming, spec 33 section 3.2)
# --------------------------------------------------------------------------

def _anthropic_request(model: str, messages: list, temperature: float, max_tokens: int) -> dict:
    system_prompt = ""
    claude_msgs = []
    for m in messages:
        if m.get("role") == "system":
            system_prompt += str(m.get("content") or "") + "\n"
        else:
            # cloud models take plain text turns; image parts only exist on vision tiers
            content = m.get("content")
            if isinstance(content, list):
                content = "\n".join(
                    str(p.get("text") or "") for p in content if isinstance(p, dict) and p.get("type") == "text"
                )
            claude_msgs.append({"role": m.get("role") or "user", "content": str(content or "")})
    if not claude_msgs:
        claude_msgs = [{"role": "user", "content": "(empty)"}]
    payload = {
        "model": model,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
        "messages": claude_msgs,
        "stream": True,
    }
    if system_prompt:
        payload["system"] = system_prompt.strip()
    return payload


def _anthropic_headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }


def _consume_anthropic_sse(lines) -> str:
    """Accumulate text deltas from an Anthropic SSE stream."""
    parts: list[str] = []
    for raw in lines:
        line = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            import json as _json

            ev = _json.loads(data)
        except Exception:
            continue
        if ev.get("type") == "content_block_delta":
            delta = ev.get("delta") or {}
            if delta.get("type") == "text_delta":
                parts.append(delta.get("text") or "")
        elif ev.get("type") == "error":
            raise RuntimeError("anthropic stream error: " + str(ev.get("error")))
    return "".join(parts).strip()


def _anthropic_chat_sync(cfg: dict, model: str, messages: list, temperature: float, max_tokens: int) -> str:
    key = get_api_key(cfg, "anthropic")
    if not key:
        raise RuntimeError("No Anthropic API key configured (Settings -> Models & Connection).")
    url = get_base_url(cfg, "anthropic").rstrip("/") + "/messages"
    payload = _anthropic_request(model, messages, temperature, max_tokens)
    with httpx.Client(timeout=45.0) as client:
        with client.stream("POST", url, json=payload, headers=_anthropic_headers(key)) as resp:
            if resp.status_code >= 400:
                body = resp.read().decode("utf-8", "replace")[:400]
                raise RuntimeError(f"anthropic HTTP {resp.status_code}: {body}")
            text = _consume_anthropic_sse(resp.iter_lines())
    if not text:
        raise RuntimeError("anthropic returned an empty response")
    return text


async def chat_anthropic(
    api_key: str,
    model: str,
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 256,
    base_url: str | None = None,
) -> str:
    """Native Anthropic Messages streaming over httpx (spec 33, section 3.2)."""
    if not api_key:
        raise RuntimeError("No Anthropic API key configured (Settings -> Models & Connection).")
    url = (base_url or ANTHROPIC_BASE_URL).rstrip("/") + "/messages"
    payload = _anthropic_request(model, messages, temperature, max_tokens)
    async with httpx.AsyncClient(timeout=45.0) as client:
        async with client.stream("POST", url, json=payload, headers=_anthropic_headers(api_key)) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "replace")[:400]
                raise RuntimeError(f"anthropic HTTP {resp.status_code}: {body}")
            parts = []
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    import json as _json

                    ev = _json.loads(data)
                except Exception:
                    continue
                if ev.get("type") == "content_block_delta":
                    delta = ev.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        parts.append(delta.get("text") or "")
                elif ev.get("type") == "error":
                    raise RuntimeError("anthropic stream error: " + str(ev.get("error")))
            text = "".join(parts).strip()
    if not text:
        raise RuntimeError("anthropic returned an empty response")
    return text


def chat_sync(cfg: dict, model_id: str, messages: list, temperature: float = 0.7, max_tokens: int = 256) -> str:
    provider = get_provider(cfg)
    if provider == "anthropic":
        return _anthropic_chat_sync(cfg, _model_name(model_id), messages, temperature, max_tokens)
    if provider == "openai":
        name = _model_name(model_id) or "gpt-4o-mini"
        client = _openai_client(cfg)
        resp = client.chat.completions.create(
            model=name, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return (resp.choices[0].message.content or "").strip()

    # ---- local LM Studio path (model lifecycle load/offload applies) ----
    lm = (cfg.get("config") or {}).get("lm_studio") or {}
    name = _model_name(model_id)
    if _lifecycle:
        _lifecycle.before_chat(name)
    client = _client(lm)
    try:
        last = None
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as e:
                last = e
                # transient "model unloaded" right after startup/eviction -
                # re-ensure the model and retry once
                if attempt == 0 and "unloaded" in str(e).lower() and _lifecycle:
                    logger.info("model %s unloaded mid-call - reloading and retrying", name)
                    _lifecycle.before_chat(name)
                    continue
                raise
        raise last  # pragma: no cover
    finally:
        if _lifecycle:
            _lifecycle.after_chat(name)


async def chat(cfg: dict, model_id: str, messages: list, temperature: float = 0.7, max_tokens: int = 256) -> str:
    if get_provider(cfg) == "anthropic":
        return await chat_anthropic(
            get_api_key(cfg, "anthropic"),
            _model_name(model_id),
            messages,
            temperature,
            max_tokens,
            base_url=get_base_url(cfg, "anthropic"),
        )
    return await asyncio.to_thread(chat_sync, cfg, model_id, messages, temperature, max_tokens)


def test_lm_sync(
    url: str | None = None,
    cfg: dict | None = None,
    provider: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Connectivity check for the selected provider (spec 33, section 5.1).

    - lm_studio: GET /models on the local endpoint
    - openai:    GET https://api.openai.com/v1/models with the key
    - anthropic: GET https://api.anthropic.com/v1/models with the key
    The caller only needs to paste a key - no endpoint configuration.
    """
    p = (provider or get_provider(cfg or {})).strip().lower()
    if p not in PROVIDERS:
        p = "lm_studio"

    if p == "openai":
        key = (api_key or "").strip() or get_api_key(cfg or {}, "openai")
        base = get_base_url(cfg or {}, "openai")
        if not key:
            return {"ok": False, "error": "Enter an OpenAI API key (sk-...) to test.", "provider": p, "base_url": base}
        try:
            client = OpenAI(api_key=key, base_url=base, timeout=20.0, max_retries=0)
            models = [m.id for m in client.models.list().data]
            return {"ok": True, "models": models, "provider": p, "base_url": base}
        except Exception as e:
            logger.warning("openai test failed: %s", e)
            return {"ok": False, "error": str(e), "provider": p, "base_url": base}

    if p == "anthropic":
        key = (api_key or "").strip() or get_api_key(cfg or {}, "anthropic")
        base = get_base_url(cfg or {}, "anthropic")
        if not key:
            return {
                "ok": False,
                "error": "Enter an Anthropic API key (sk-ant-...) to test.",
                "provider": p,
                "base_url": base,
            }
        try:
            r = httpx.get(
                base.rstrip("/") + "/models",
                headers=_anthropic_headers(key),
                timeout=20.0,
            )
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            data = r.json() or {}
            models = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
            return {"ok": True, "models": models, "provider": p, "base_url": base}
        except Exception as e:
            logger.warning("anthropic test failed: %s", e)
            return {"ok": False, "error": str(e), "provider": p, "base_url": base}

    # lm_studio (legacy default)
    lm = (((cfg or {}).get("config") or {}).get("lm_studio")) or {}
    try:
        client = _client(lm, base_url=url)
        models = [m.id for m in client.models.list().data]
        return {
            "ok": True,
            "models": models,
            "provider": "lm_studio",
            "base_url": _base_url(url or lm.get("base_url")),
        }
    except Exception as e:
        logger.warning("lm test failed: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "provider": "lm_studio",
            "base_url": _base_url(url or lm.get("base_url")),
        }


async def test_lm(
    url: str | None = None,
    cfg: dict | None = None,
    provider: str | None = None,
    api_key: str | None = None,
) -> dict:
    return await asyncio.to_thread(test_lm_sync, url, cfg, provider, api_key)
