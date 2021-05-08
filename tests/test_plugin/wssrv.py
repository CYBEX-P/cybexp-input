import asyncio
import json
import time
import websockets

with open("testdata.json") as f:
    data = json.load(f)

async def send_data(websocket, path):
    total = len(data)
    this = 0
    while True:
        await websocket.send(json.dumps(data[this]))
        this += 1
        if this == total:
            this = 0
            break
      
start_server = websockets.serve(send_data,'localhost', 4042)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()



