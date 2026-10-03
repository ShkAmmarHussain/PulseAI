import asyncio
import json
import subprocess

import aiohttp

URL = "http://127.0.0.1:8765/ws"
CREATE_NO_WINDOW = 0x08000000


def proc_count(name):
    r = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {name}"],
        capture_output=True, text=True, creationflags=CREATE_NO_WINDOW,
    )
    return r.stdout.lower().count(name.lower())


async def main():
    results = {}
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(URL) as ws:

            async def pump(seconds):
                """collect messages for N seconds"""
                end = asyncio.get_event_loop().time() + seconds
                got = []
                while asyncio.get_event_loop().time() < end:
                    try:
                        r = await asyncio.wait_for(ws.receive(), end - asyncio.get_event_loop().time())
                    except asyncio.TimeoutError:
                        break
                    if r.type == aiohttp.WSMsgType.TEXT:
                        try:
                            got.append(json.loads(r.data))
                        except Exception:
                            pass
                return got

            async def send_and_wait(text, seconds, matcher=None):
                await ws.send_str(json.dumps({"type": "text_input", "payload": {"text": text}}))
                msgs = await pump(seconds)
                hits = [m for m in msgs if matcher is None or matcher(m)]
                return msgs, hits

            # 1. web search via planner -> ui.chat summary
            msgs, hits = await send_and_wait(
                "search for tauri desktop framework", 30,
                lambda m: m.get("topic") == "ui.chat" and m["payload"].get("role") == "assistant",
            )
            summ = " ".join((h["payload"].get("text") or "") for h in hits)
            results["web_search_planner"] = "http" in summ
            print("1) web_search planner:", results["web_search_planner"], "|", summ[:110].replace("\n", " "))

            # 2. open notepad (auto-allow risk 2)
            before = proc_count("notepad.exe")
            msgs, hits = await send_and_wait(
                "open notepad", 25, lambda m: m.get("topic") == "ui.chat" and m["payload"].get("role") == "assistant"
            )
            summ = " ".join((h["payload"].get("text") or "") for h in hits)
            await asyncio.sleep(1.5)
            after = proc_count("notepad.exe")
            results["open_app"] = after > before and "fail" not in summ.lower()
            print("2) open notepad:", results["open_app"], "|", summ[:120].replace("\n", " "))

            # 3. close notepad (risk 5 auto)
            if after > before or after > 0:
                msgs, hits = await send_and_wait(
                    "close notepad", 25, lambda m: m.get("topic") == "ui.chat" and m["payload"].get("role") == "assistant"
                )
                summ = " ".join((h["payload"].get("text") or "") for h in hits)
                await asyncio.sleep(1.5)
                results["close_app"] = proc_count("notepad.exe") == 0
                print("3) close notepad:", results["close_app"], "|", summ[:120].replace("\n", " "))
            else:
                results["close_app"] = "skipped"

            # 4. memory + web fallback answer
            msgs, hits = await send_and_wait(
                "Who won the 2024 Nobel Prize in Physics?", 45,
                lambda m: m.get("topic") == "ui.chat" and m["payload"].get("role") == "assistant",
            )
            ans = (hits[-1]["payload"].get("text") if hits else "") or ""
            results["memory_web"] = any(k in ans.lower() for k in ("hopfield", "hinton", "nobel", "2024"))
            print("4) memory+web:", results["memory_web"], "|", ans[:140].replace("\n", " "))

            # 5. voice listen on/off (mic presence tolerant)
            await ws.send_str(json.dumps({"type": "voice_listen", "payload": {"on": True}}))
            msgs = await pump(3)
            st = [m for m in msgs if m.get("topic") == "ui.voice_state"]
            state_on = st[-1]["payload"]["state"] if st else "none"
            await ws.send_str(json.dumps({"type": "voice_listen", "payload": {"on": False}}))
            msgs = await pump(3)
            st2 = [m for m in msgs if m.get("topic") == "ui.voice_state"]
            state_off = st2[-1]["payload"]["state"] if st2 else "none"
            results["voice_toggle"] = state_on in ("listening", "error") and state_off in ("idle", "error")
            print("5) voice states:", state_on, "->", state_off)

    print("RESULTS:", json.dumps(results))
    ok = all(v is True for v in results.values())
    print("E2E:", "PASS" if ok else "CHECK ISSUES")


asyncio.run(main())
