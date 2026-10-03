import asyncio, json, aiohttp

async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect("http://127.0.0.1:8765/ws") as ws:
            await ws.send_str(json.dumps({"type": "text_input", "payload": {"text": "What date is it today?"}}))
            loop = asyncio.get_event_loop()
            end = loop.time() + 60
            while loop.time() < end:
                r = await asyncio.wait_for(ws.receive(), end - loop.time())
                d = json.loads(r.data)
                if d.get("topic") == "ui.chat" and d["payload"].get("role") == "assistant":
                    print("ANSWER:", d["payload"]["text"])
                    return
            print("TIMEOUT")

asyncio.run(main())