import asyncio
import base64
import json
import numpy as np
import pyaudio
import websockets

# Import your system tools
from jarvis_system import system # the JarvisSystem instance
from jarvis_web_access import search_web, aquire_links

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
}

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


def get_device_index(p, name_fragment):
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        if name_fragment.lower() in d['name'].lower() and d['maxInputChannels'] > 0:
            return i
    raise RuntimeError(f"No input device matching '{name_fragment}'")


async def play_audio(audio_bytes: bytes):
    global is_playing
    is_playing = True
    def _play():
        out = p.open(format=pyaudio.paInt16, channels=1, rate=TTS_RATE, output=True)
        for i in range(0, len(audio_bytes), 1024):
            out.write(audio_bytes[i:i + 1024])
        out.stop_stream()
        out.close()
    await asyncio.to_thread(_play)
    is_playing = False


send_queue: asyncio.Queue = asyncio.Queue()

async def sender(ws):
    """Single coroutine that owns all sends."""
    while True:
        data = await send_queue.get()
        await ws.send(data)

async def send_chunks(ws, stream):
    from scipy.signal import resample
    while True:
        chunk = await asyncio.to_thread(stream.read, CHUNK, exception_on_overflow=False)
        if not is_playing:
            audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
            resampled = resample(audio, TARGET_RATE * CHUNK // DEVICE_RATE)
            data = np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
            await send_queue.put(data)  # queue instead of direct send
        await asyncio.sleep(0.01)

async def receive(ws):
    global audio_reassembly_buffer
    while True:
        message = await ws.recv()

        if isinstance(message, bytes):
            await play_audio(message)

        elif isinstance(message, str):
            msg = json.loads(message)

            if msg["type"] == "tts":
                audio_reassembly_buffer.extend(base64.b64decode(msg["data"]))

            elif msg["type"] == "tts_end":
                if audio_reassembly_buffer:
                    await play_audio(bytes(audio_reassembly_buffer))
                    audio_reassembly_buffer.clear()

            elif msg["type"] == "tool_call":
                result = await asyncio.to_thread(execute_tool, msg["name"], msg["inputs"])
                print(f"[Tool] {msg['name']} → {result[:80]}...")
                await send_queue.put(json.dumps({  # queue instead of direct send
                    "type": "tool_result",
                    "id": msg["id"],
                    "result": result
                }))

async def connect_loop():
    device_index = get_device_index(p, "USB PnP")
    stream = p.open(
        format=pyaudio.paInt16, channels=1, rate=DEVICE_RATE,
        input=True, input_device_index=device_index,
        frames_per_buffer=CHUNK
    )
    while True:
        try:
            async with websockets.connect(
                WS_URL,
                ping_interval=20,
                ping_timeout=20,
                max_size=10 * 1024 * 1024
            ) as ws:
                print("[Client] Connected")
                await asyncio.gather(
                    sender(ws),       # owns all ws.send calls
                    send_chunks(ws, stream),
                    receive(ws),
                )
        except Exception as e:
            print(f"[Client] Disconnected: {e}, retrying...")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(connect_loop())