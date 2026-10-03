import asyncio, json, aiohttp

async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect("http://127.0.0.1:8765/ws") as ws:
            await ws.send_str(json.dumps({"type": "ping"}))
            r = await asyncio.wait_for(ws.receive(), 5)
            print("WS reply:", str(r.data)[:150])

asyncio.run(main())