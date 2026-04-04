import asyncio
import base64
import json
import uuid
from BMO import BMO
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect



app = FastAPI()
bmo = BMO()


@app.websocket("/bmo/ws")
async def bmo_ws(websocket: WebSocket):
    await websocket.accept()

    pending: dict[str, asyncio.Future] = {}
    send_queue: asyncio.Queue = asyncio.Queue()

    async def sender():
        """Owns all sends so process_audio and remote_tool don't conflict."""
        while True:
            data, is_text = await send_queue.get()
            if is_text:
                await websocket.send_text(data)
            else:
                await websocket.send_bytes(data)

    async def remote_tool(name: str, inputs: dict) -> str:
        call_id = str(uuid.uuid4())[:8]
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        pending[call_id] = fut
        print(f"[RPC] Sending tool call: {name} ({call_id})")
        await send_queue.put((json.dumps({
            "type": "tool_call",
            "id": call_id,
            "name": name,
            "inputs": inputs
        }), True))
        print(f"[RPC] Waiting for result: {name} ({call_id})")
        try:
            result = await asyncio.wait_for(fut, timeout=15.0)
            print(f"[RPC] Got result for {name}: {result[:80]}")
            return result
        except asyncio.TimeoutError:
            pending.pop(call_id, None)
            return f"Tool {name} timed out"

    bmo.remote_tool = remote_tool

    audio_queue: asyncio.Queue = asyncio.Queue()

    async def audio_processor():
        while True:
            chunk = await audio_queue.get()
            resp = await bmo.process_audio(chunk)

            if isinstance(resp, bytes) and resp:
                # Wake word / farewell — already fully generated, just send it
                chunk_size = 32 * 1024
                for i in range(0, len(resp), chunk_size):
                    await send_queue.put((json.dumps({
                        "type": "tts",
                        "data": base64.b64encode(resp[i:i + chunk_size]).decode()
                    }), True))
                await send_queue.put((json.dumps({"type": "tts_end"}), True))

            elif isinstance(resp, str) and resp:
                for pcm_chunk in bmo.voice.TTS_stream(resp):
                    print(f"[server] sending TTS chunk {len(pcm_chunk)} bytes")
                    await send_queue.put((pcm_chunk, False))
                print("[server] sending sentinel")
                await send_queue.put((b"\x00", False))

    async def receiver():
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break

            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"]:
                await audio_queue.put(message["bytes"])

            elif "text" in message and message["text"]:
                msg = json.loads(message["text"])
                print(f"[WS] received text type: {msg.get('type')} id: {msg.get('id')}")
                if msg["type"] == "tool_result" and msg["id"] in pending:
                    print(f"[WS] resolving future {msg['id']}")
                    pending.pop(msg["id"]).set_result(msg["result"])
                elif msg["type"] == "setup":
                    print(f"[WS] {msg}")
                    bmo.set_client_tools(tools_schema=msg["tools_schema"], tools=msg["tools"])

    try:
        tasks = await asyncio.gather(
            sender(),
            receiver(),
            audio_processor(),
            return_exceptions=True
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        print("Client disconnected, cleaning up.")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
