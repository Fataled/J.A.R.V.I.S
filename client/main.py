import asyncio
import base64
import json
import threading

import numpy as np
import pyaudio
import websockets

# Import your system tools
from jarvis_system import system # the JarvisSystem instance
from jarvis_web_access import search_web, aquire_links
from jarvis_vision import vision
from jarvis_git import git
import queue as stdlib_queue
from tools import tools, tools_schema

TOOL_HANDLERS = {
    "open_app":        lambda i: system.open_app(i["app"]),
    "close_app":       lambda i: system.close_app(i["app"]),
    "set_volume":      lambda i: system.set_volume_linux(i["volume"]) or f"Volume set to {i['volume']}",
    "adjust_volume":   lambda i: system.adjust_volume_linux(i["volume"]) or f"Volume adjusted by {i['volume']}",
    "mute":            lambda i: system.mute_linux() or "Toggled mute",
    "get_system_status": lambda i: system.get_system_status() if hasattr(system, 'get_system_status') else "N/A",
    "network_speed":   lambda i: system.network_speed() if hasattr(system, 'network_speed') else "N/A",
    "read_active_file": lambda i: open("/tmp/jarvis_active_file").read(),
    "jarvis_clip_that": lambda i: system.jarvis_clip_that(i["filename"]),
    "aquire_links": lambda i: aquire_links(i["query"]),
    "search_web": lambda i: search_web(i["url"]),
    "capture_and_analyze": lambda i: vision.capture_and_analyze(i["filename"], i["message"]),
    "push": lambda i: git.push(),
    "pull": lambda i: git.pull(),
    "status": lambda i: git.status(),
    "commit": lambda i: git.commit(i["message"], i.get("all", True), i.get("specific_files", None)),
    "set_repo": lambda i: git.set_repo(i["repo"])
}

data = json.dumps({"tools": list(tools), "tools_schema": tools_schema})

def execute_tool(name: str, inputs: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"Unknown tool: {name}"
    try:
        result = handler(inputs)
        return str(result) if result is not None else "Done"
    except Exception as e:
        return f"Tool {name} failed: {e}"


WS_URL = "ws://localhost:8000/jarvis/ws"
DEVICE_RATE = 48000
TARGET_RATE = 16000
CHUNK = 3840
TTS_RATE = 24000

p = pyaudio.PyAudio()
is_playing = False
audio_reassembly_buffer = bytearray()

playback_queue = stdlib_queue.Queue()

def playback_thread():
    """Runs in its own OS thread — no asyncio involvement."""
    global is_playing
    print("[Playback] thread started")
    out_stream = None
    while True:
        chunk = playback_queue.get()
        #print(f"[Playback] got chunk: {chunk if chunk is None else f'{len(chunk)} bytes'}")
        # blocks until data arrives
        if chunk is None:
            if out_stream:
                out_stream.stop_stream()
                out_stream.close()
                out_stream = None
            is_playing = False
            continue
        if out_stream is None:
            out_stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=TTS_RATE,
                output=True,
                frames_per_buffer=4800
            )
            is_playing = True
        out_stream.write(chunk)

# Start it once at module level
threading.Thread(target=playback_thread, daemon=True).start()

def get_device_index(p, name_fragment):
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        if name_fragment.lower() in d['name'].lower() and d['maxInputChannels'] > 0:
            return i
    raise RuntimeError(f"No input device matching '{name_fragment}'")

send_queue: asyncio.Queue = asyncio.Queue()

async def sender(ws):
    """Single coroutine that owns all sends."""
    while True:
        data = await send_queue.get()
        await ws.send(data)

async def send_chunks(ws, stream):
    from scipy.signal import resample
    while True:
        if is_playing:
            await asyncio.sleep(0.05)
            continue
        try:
            chunk = await asyncio.to_thread(stream.read, CHUNK, exception_on_overflow=False)
        except Exception as e:
            print(f"[Audio] Stream error: {e}, waiting...")
            await asyncio.sleep(0.1)
            continue
        audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        resampled = resample(audio, TARGET_RATE * CHUNK // DEVICE_RATE)
        data = np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
        await send_queue.put(data)
        await asyncio.sleep(0.01)


async def receive(ws):
    while True:
        message = await ws.recv()
        #print("[Client] Received message")

        if isinstance(message, bytes):
            if message == b"\x00":
                playback_queue.put(None)
            else:
                playback_queue.put(message)

        elif isinstance(message, str):
            msg = json.loads(message)

            if msg["type"] == "tts":
                # server is still sending base64 JSON — decode and play
                audio_bytes = base64.b64decode(msg["data"])
                playback_queue.put(audio_bytes)

            elif msg["type"] == "tts_end":
                playback_queue.put(None)

            elif msg["type"] == "tool_call":
                result = await asyncio.to_thread(execute_tool, msg["name"], msg["inputs"])
                print(f"[Tool] {msg['name']} → {str(result)[:80]}")
                await send_queue.put(json.dumps({
                    "type": "tool_result",
                    "id": msg["id"],
                    "result": result
                }))

async def connect_loop():
    global p
    device_index = get_device_index(p, "USB PnP")
    while True:
        stream = None
        try:
            stream = p.open(
                format=pyaudio.paInt16, channels=1, rate=DEVICE_RATE,
                input=True, input_device_index=device_index,
                frames_per_buffer=CHUNK
            )
            async with websockets.connect(
                WS_URL,
                ping_interval=20,
                ping_timeout=20,
                max_size=10 * 1024 * 1024
            ) as ws:
                print("[Client] Connected")
                await ws.send(json.dumps({"type": "setup", "tools": list(tools), "tools_schema": tools_schema}))
                await asyncio.gather(
                    sender(ws),
                    send_chunks(ws, stream),
                    receive(ws),
                )
        except Exception as e:
            print(f"[Client] Disconnected: {e}, retrying...")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            try:
                p.terminate()
            except:
                pass
            p = pyaudio.PyAudio()  # fresh instance
            device_index = get_device_index(p, "USB PnP")  # re-resolve index on new instance
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(connect_loop())