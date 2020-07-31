import asyncio
import json
import time
import websockets

with open("testdata.json") as f:
    data = json.load(f)

async def say_hello(websocket, path):
    total = len(data)
    this = 0
    while True:
        await websocket.send(json.dumps(data[this]))
        this += 1
        if this == total:
            this = 0
        
start_server = websockets.serve(say_hello,'localhost', 4042)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()


