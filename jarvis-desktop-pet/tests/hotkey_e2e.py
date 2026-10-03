import asyncio
import json
import sys
import time
from pathlib import Path

import aiohttp

WS = "ws://127.0.0.1:8765/ws"

VK_CONTROL, VK_MENU, VK_J = 0x11, 0x12, 0x4A


def press_combo():
    import ctypes

    u = ctypes.windll.user32
    for vk, down in ((VK_CONTROL, True), (VK_MENU, True), (VK_J, True), (VK_J, False), (VK_MENU, False), (VK_CONTROL, False)):
        u.keybd_event(vk, 0, 0 if down else 0x0002, 0)
        time.sleep(0.05)


class Client:
    def __init__(self, ws):
        self.ws = ws
        self.msgs = []

    async def send(self, obj):
        await self.ws.send_str(json.dumps(obj))

    async def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            try:
                m = await asyncio.wait_for(self.ws.receive(), timeout=max(0.1, end - time.time()))
            except asyncio.TimeoutError:
                break
            if m.type != aiohttp.WSMsgType.TEXT:
                break
            self.msgs.append(json.loads(m.data))
        return self.msgs

    async def wait_for(self, pred, seconds):
        end = time.time() + seconds
        while time.time() < end:
            for m in self.msgs:
                if pred(m):
                    return m
            try:
                m = await asyncio.wait_for(self.ws.receive(), timeout=max(0.1, end - time.time()))
            except asyncio.TimeoutError:
                break
            if m.type != aiohttp.WSMsgType.TEXT:
                break
            self.msgs.append(json.loads(m.data))
        for m in self.msgs:
            if pred(m):
                return m
        return None


async def main():
    ok = {"autostart": False, "hotkey_on": False, "hotkey_off": False}
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(WS, timeout=30) as ws:
            c = Client(ws)

            # 1. autostart state + set/unset roundtrip
            await c.send({"type": "autostart_state"})
            r = await c.wait_for(lambda m: m.get("type") == "autostart_state", 5)
            st = (r or {}).get("payload", {})
            print("autostart initial:", st)
            if st.get("available"):
                c.msgs.clear()
                await c.send({"type": "autostart", "payload": {"enabled": True}})
                r = await c.wait_for(lambda m: m.get("type") == "autostart_state", 5)
                on = (r or {}).get("payload", {})
                print("autostart on:", on)
                c.msgs.clear()
                await c.send({"type": "autostart", "payload": {"enabled": False}})
                r = await c.wait_for(lambda m: m.get("type") == "autostart_state", 5)
                off = (r or {}).get("payload", {})
                print("autostart off:", off)
                ok["autostart"] = bool(on.get("enabled")) and not off.get("enabled", True)
            else:
                print("autostart: not available in this mode (dev) - structure ok")
                ok["autostart"] = True

            # 2. hotkey: press combo -> listening, press again -> back
            await c.send({"type": "voice_listen", "payload": {"on": False}})
            c.msgs.clear()
            print("pressing ctrl+alt+j ...")
            press_combo()
            r = await c.wait_for(
                lambda m: m.get("topic") == "ui.voice_state" and m["payload"].get("state") == "listening", 6
            )
            ok["hotkey_on"] = r is not None
            print("state after press 1:", (r or {}).get("payload", {}).get("state"))

            c.msgs.clear()
            await asyncio.sleep(0.6)
            print("pressing ctrl+alt+j again ...")
            press_combo()
            r = await c.wait_for(
                lambda m: m.get("topic") == "ui.voice_state" and m["payload"].get("state") in ("idle", "wake", "disabled"),
                6,
            )
            ok["hotkey_off"] = r is not None
            print("state after press 2:", (r or {}).get("payload", {}).get("state"))

    print("RESULTS:", json.dumps(ok))
    print("E2E:", "PASS" if all(ok.values()) else "FAIL")
    return 0 if all(ok.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
