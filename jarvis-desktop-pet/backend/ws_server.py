from aiohttp import web

from backend.ws_bridge import WSBridge


async def start_ws_server(bus, host="127.0.0.1", port=8765):
    bridge = WSBridge(bus)
    bridge.wire_bus()
    app = web.Application()
    app.router.add_get("/ws", bridge.handle_ws)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"WS server on ws://{host}:{port}/ws")
    return runner, bridge