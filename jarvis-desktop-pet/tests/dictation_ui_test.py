"""Dictation + dictionary UI test over CDP (Edge :9334, spec 29 sections 3.2/3.3).

Checks: settings nav sections, dictation bubble structure, vocabulary table
interactions (add/save/ack re-render/restore), history refresh, dirty-guard
isolation, and the bubble show/flash/hide lifecycle driven by the backend.

Run (Edge headless on 9334 + backend on 8765):
    .venv/Scripts/python tests/dictation_ui_test.py
exit 0 = pass
"""

import asyncio
import json
import sys
import time

import aiohttp

CDP = "http://127.0.0.1:9334/json"
BACKEND_WS = "ws://127.0.0.1:8765/ws"

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


async def recv(ws, timeout):
    try:
        m = await asyncio.wait_for(ws.receive(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    if m.type == aiohttp.WSMsgType.TEXT:
        try:
            return json.loads(m.data)
        except Exception:
            return None
    return None


async def rpc(ws, method, params=None, rid=[0], timeout=15):
    rid[0] += 1
    i = rid[0]
    await ws.send_json({"id": i, "method": method, "params": params or {}})
    t = time.time() + timeout
    while time.time() < t:
        d = await recv(ws, t - time.time())
        if not d:
            continue
        if d.get("id") == i:
            return d
    return None


async def ev(ws, expr, timeout=20):
    r = await rpc(ws, "Runtime.evaluate",
                  {"expression": expr, "returnByValue": True, "awaitPromise": True},
                  timeout=timeout)
    if r and "result" in r and "result" in r["result"]:
        res = r["result"]["result"]
        if res.get("value") is not None:
            return res.get("value")
        if "exceptionDetails" in r["result"]:
            return {"exc": str(r["result"]["exceptionDetails"])[:300]}
    return None


async def wait_ev(ws, expr, pred, seconds=8, interval=0.35):
    end = time.time() + seconds
    last = None
    while time.time() < end:
        last = await ev(ws, expr)
        try:
            if pred(last):
                return last
        except Exception:
            pass
        await asyncio.sleep(interval)
    return last


STRUCT = """
(() => {
  const q = (s) => document.querySelector(s);
  const qa = (s) => [...document.querySelectorAll(s)];
  return {
    title: document.title,
    nav: qa('#settings-index button[data-sec]').map(b => b.dataset.sec),
    dictSec: !!document.getElementById('sec-dictionary'),
    histSec: !!document.getElementById('sec-history'),
    vocabTable: !!q('#vocab-table'),
    vocabAdd: !!q('#vocab-add'),
    vocabSave: !!q('#vocab-save'),
    vocabHint: q('#vocab-hint')?.textContent?.trim() || null,
    histList: !!q('#dict-history'),
    histRefresh: !!q('#dict-history-refresh'),
    dictHotkey: q('#v-dict-hotkey') ? {ph: q('#v-dict-hotkey').placeholder, val: q('#v-dict-hotkey').value} : null,
    bubble: (() => {
      const b = q('#dictation-bubble');
      if (!b) return null;
      return {hidden: b.hidden, bars: b.querySelectorAll('.db-bars i').length,
              label: b.querySelector('.db-label')?.textContent || '', flash: b.classList.contains('flash')};
    })(),
    icons: ['#i-plus', '#i-check', '#i-x'].every(s => !!q(s)),
    saveBtn: !!q('#save')
  };
})()
"""

DICT_STATE = """
(() => {
  const q = (s) => document.querySelector(s);
  const words = [...document.querySelectorAll('.vocab-row .vocab-word')].map(i => i.value);
  const hist = document.querySelectorAll('#dict-history .dict-row').length;
  const histHint = q('#dict-history .hint')?.textContent || null;
  return {
    words, hist, histHint,
    hint: q('#vocab-hint')?.textContent || '',
    rows: document.querySelectorAll('.vocab-row').length,
    saveDisabled: q('#save')?.disabled,
    hk: q('#v-dict-hotkey')?.value
  };
})()
"""


def focus_top(hwnd_child):
    import ctypes

    u32 = ctypes.windll.user32
    top = u32.GetAncestor(hwnd_child, 2)
    for _ in range(3):
        if u32.GetForegroundWindow() == top:
            return True
        fg = u32.GetForegroundWindow()
        fg_tid = u32.GetWindowThreadProcessId(fg, None) if fg else 0
        my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        u32.AttachThreadInput(my_tid, fg_tid, True)
        u32.SetForegroundWindow(top)
        u32.AttachThreadInput(my_tid, fg_tid, False)
        time.sleep(0.15)
    return u32.GetForegroundWindow() == top


def make_focus_target():
    import tkinter as tk

    root = tk.Tk()
    root.title("Jarvis dictation ui")
    root.geometry("420x150+200+560")
    root.attributes("-topmost", True)
    text = tk.Text(root)
    text.pack(fill="both", expand=True)
    root.update()
    root.lift()
    root.focus_force()
    text.focus_set()
    hwnd = root.winfo_id()
    focus_top(hwnd)
    time.sleep(0.2)
    root.update()
    return root, text


async def backend_dictation(action, text=None):
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(BACKEND_WS, timeout=15) as ws:
            await ws.send_str(json.dumps({"type": "dictation", "payload": {"action": action, "text": text}}))
            end = time.time() + 8
            while time.time() < end:
                d = await recv(ws, end - time.time())
                if d and d.get("type") == "dictation_ack":
                    return d.get("payload", {})
            return {}


async def main():
    root, text = make_focus_target()
    console_errs = []
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(CDP) as r:
                targets = await r.json()
            main_t = next((t for t in targets if t["type"] == "page" and "index.html" in t["url"]), None)
            if not main_t:
                main_t = next((t for t in targets if t["type"] == "page" and "pet.html" not in t["url"]), None)
            if not main_t:
                print("NO MAIN TARGET"); return 2

            async with s.ws_connect(main_t["webSocketDebuggerUrl"], timeout=30) as ws:
                await rpc(ws, "Runtime.enable")
                await rpc(ws, "Page.enable")
                # headless Edge freezes hidden tabs (timers + WS die); activate it
                await rpc(ws, "Page.bringToFront")
                await ev(ws, "location.reload()")
                await asyncio.sleep(3)
                await rpc(ws, "Page.bringToFront")

                async def drain(deadline):
                    while time.time() < deadline:
                        d = await recv(ws, max(0.05, deadline - time.time()))
                        if d and d.get("method") == "Runtime.exceptionThrown":
                            console_errs.append(d["params"]["exceptionDetails"].get("text", "err"))

                # --- structure ---
                st = await ev(ws, STRUCT)
                check("title Jarvis", st and st.get("title") == "Jarvis", st and st.get("title"))
                nav = (st or {}).get("nav") or []
                check("nav has Dictionary", "sec-dictionary" in nav, nav)
                check("nav has Dictation History", "sec-history" in nav, nav)
                s0 = st or {}
                check("dictionary section + controls",
                      s0.get("dictSec") and s0.get("vocabTable") and s0.get("vocabAdd") and s0.get("vocabSave"),
                      {k: s0.get(k) for k in ("dictSec", "vocabTable", "vocabAdd", "vocabSave")})
                check("history section + controls",
                      s0.get("histSec") and s0.get("histList") and s0.get("histRefresh"),
                      {k: s0.get(k) for k in ("histSec", "histList", "histRefresh")})
                hk = s0.get("dictHotkey")
                check("dictation hotkey field", hk is not None and hk.get("ph") == "ctrl+alt+d", hk)
                b = s0.get("bubble")
                check("bubble structure + hidden",
                      b is not None and b.get("hidden") is True and b.get("bars") == 5,
                      b)
                check("sprite icons", s0.get("icons") is True, s0.get("icons"))

                # --- open settings and load state ---
                await ev(ws, "showTab('settings'); Jarvis.getSettings();")
                await asyncio.sleep(1.5)
                d0 = await ev(ws, DICT_STATE)
                check("settings loaded: dict hotkey value",
                      d0 is not None and d0.get("hk") not in (None, ""), d0 and d0.get("hk"))
                check("vocabulary rows loaded", d0 is not None and (d0.get("rows") or 0) >= 1, d0 and d0.get("rows"))
                check("history list resolved",
                      d0 is not None and (d0.get("hist") or 0) >= 1 or (d0 and d0.get("histHint")), d0)

                orig = await ev(ws, "JSON.stringify(collectVocab())")
                orig = json.loads(orig) if isinstance(orig, str) else []

                # --- dirty guard: dictionary edits do NOT dirty settings save ---
                save0 = (d0 or {}).get("saveDisabled")
                await ev(ws, """
                  (() => {
                    const i = document.querySelector('.vocab-row .vocab-word');
                    i.value = 'guard-test';
                    i.dispatchEvent(new Event('input', {bubbles: true}));
                    return true;
                  })()
                """)
                await asyncio.sleep(0.3)
                d1 = await ev(ws, DICT_STATE)
                check("vocab edit does not dirty settings",
                      d1 is not None and d1.get("saveDisabled") == save0,
                      (save0, d1 and d1.get("saveDisabled")))

                # --- add mapping row ---
                rows_before = (d1 or {}).get("rows") or 0
                await ev(ws, "document.getElementById('vocab-add').click(); true")
                await asyncio.sleep(0.3)
                d2 = await ev(ws, DICT_STATE)
                check("add mapping row", d2 is not None and d2.get("rows") == rows_before + 1,
                      (rows_before, d2 and d2.get("rows")))

                # --- fill + save, ack re-renders table ---
                await ev(ws, """
                  (() => {
                    const rows = [...document.querySelectorAll('.vocab-row')];
                    const last = rows[rows.length - 1];
                    last.querySelector('.vocab-heard').value = 'jarvis unit test heard';
                    last.querySelector('.vocab-word').value = 'jarviston';
                    document.getElementById('vocab-save').click();
                    return true;
                  })()
                """)
                saved = await wait_ev(ws, DICT_STATE,
                                      lambda d: d and "Dictionary saved" in (d.get("hint") or ""),
                                      seconds=8)
                check("dictionary save ack hint", saved is not None and "Dictionary saved" in (saved.get("hint") or ""),
                      saved and saved.get("hint"))
                d3 = await ev(ws, DICT_STATE)
                check("saved mapping in table", d3 is not None and "jarviston" in (d3.get("words") or []),
                      d3 and d3.get("words"))

                # --- restore original vocabulary ---
                await ev(ws, "renderVocab(" + json.dumps(orig) + "); true")
                await asyncio.sleep(0.3)
                await ev(ws, "document.getElementById('vocab-save').click(); true")
                expect_words = sorted([m.get("word", "") for m in orig])
                restored = await wait_ev(
                    ws, DICT_STATE,
                    lambda d: d and sorted([w for w in (d.get("words") or []) if w]) == expect_words
                    and f"({len(orig)} mapping" in (d.get("hint") or ""),
                    seconds=8)
                check("vocabulary restored to original",
                      restored is not None
                      and sorted([w for w in (restored.get("words") or []) if w]) == expect_words
                      and f"({len(orig)} mapping" in (restored.get("hint") or ""),
                      restored and (restored.get("words"), restored.get("hint")))

                # --- bubble lifecycle: start -> visible ---
                ack = await backend_dictation("start")
                check("start ack via backend", ack.get("ok") is True and ack.get("active") is True, ack)
                await asyncio.sleep(0.8)
                st1 = await ev(ws, STRUCT)
                b1 = (st1 or {}).get("bubble") or {}
                check("bubble shown on dictation.start", b1.get("hidden") is False, b1)
                check("bubble listening label", "Listening" in (b1.get("label") or ""), b1.get("label"))

                # --- apply -> flash label -> auto-hide ---
                check("focus target in foreground for apply", focus_top(root.winfo_id()))
                time.sleep(0.25)
                ack = await backend_dictation("apply", "element studio now")
                check("apply ack (ui test)", ack.get("ok") is True and ack.get("injected") is True, ack)
                await asyncio.sleep(0.6)
                st2 = await ev(ws, STRUCT)
                b2 = (st2 or {}).get("bubble") or {}
                check("bubble flash + app label",
                      b2.get("hidden") is False and b2.get("flash") is True
                      and "Jarvis dictation ui" in (b2.get("label") or ""),
                      b2)
                text.update()
                typed = text.get("1.0", "end-1c")
                # dictionary applied before injection: "element studio" -> "LM Studio"
                check("typed into ui-test widget", typed == "LM Studio now", repr(typed))

                # --- stop -> hidden ---
                ack = await backend_dictation("stop")
                check("stop ack", ack.get("ok") is True and ack.get("active") is False, ack)
                await asyncio.sleep(0.5)
                st3 = await ev(ws, STRUCT)
                check("bubble hidden on dictation.stop", ((st3 or {}).get("bubble") or {}).get("hidden") is True,
                      (st3 or {}).get("bubble"))

                # --- history refresh shows the applied text ---
                await ev(ws, "document.getElementById('dict-history-refresh').click(); true")
                await asyncio.sleep(1.0)
                h = await ev(ws, DICT_STATE)
                check("history rows rendered after refresh", h is not None and (h.get("hist") or 0) >= 1,
                      h and h.get("hist"))

                # --- console stayed clean ---
                await drain(time.time() + 1.0)
                check("no console exceptions", not console_errs, console_errs[:5])
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    print(f"== {sum(results)}/{len(results)} PASS ==")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
