import asyncio
import json
import time
from pathlib import Path
from collections import deque

from dotenv import load_dotenv
import os
from vosk import Model as VoskModel, KaldiRecognizer
from pyaudio import paInt16
import numpy as np
import whisper

from jarvis_voice import JarvisVoice
from jarvis_spotify import play, pause, resume, currently_playing, clear_and_play
from anthropic import Anthropic
from jarvis_git import commit, status, push
from jarvis_weather import weather_data


class AnthropicEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "text"):
            return obj.text
        if hasattr(obj, "name") and hasattr(obj, "input"):
            return f"[ToolUse: {obj.name}]"
        return str(obj)


class Jarvis:
    SYSTEM_PROMPT = """
    You are J.A.R.V.I.S., a voice assistant modelled after the Jeeves/Wodehouse butler character. You are speaking aloud — your responses will be converted to speech and played back to the user.

    CRITICAL RULES:
    - NEVER return raw tool output. Always interpret and summarize results in natural spoken language.
    - Keep responses concise and conversational — you are speaking, not writing a report.
    - Use the butler/Jeeves tone: calm, dry wit, slightly formal, effortlessly competent.
    - No bullet points, no markdown, no lists. Prose only.
    - No numbers like "192.168.2.192" unless specifically asked — say "your local network" instead.
    - Round numbers naturally. "83 percent memory usage" not "83.0%".
    - If a tool returns an error, acknowledge it briefly and move on.

    EXAMPLES of good responses:
    - get_system_status result → "Your machine is running well, sir. CPU is light at the moment, though you're using the majority of your RAM. The GPU is warm but well within limits."
    - network_speed result → "Network looks healthy — roughly 18 kilobytes per second in both directions."
    - open_app result → "Firefox is open, sir."
    - weather_data result → "It's currently overcast and 12 degrees. You may want a jacket."

    EXAMPLES of bad responses (never do this):
    - "CPU: 6 cores, 4821MHz, 0.0% usage Memory: 25.30GB/30.49GB (83.0%)"
    - "Upload: 2.29GB, Download: 10.34GB, Upload Speed: 18.62KB/s"
    """

    FAREWELL_WORDS = {"goodbye", "dismissed", "that's all", "thank you", "that will be all"}

    CHUNK = 1280
    FORMAT = paInt16
    CHANNELS = 1
    RATE = 16000

    SILENCE_LIMIT = 1.2
    MIN_COMMAND_DURATION = 0.5
    SILENCE_RMS_THRESHOLD = 200

    # Tools that execute on the client machine via RPC
    CLIENT_SIDE_TOOLS = {
        "open_app", "close_app", "set_volume", "adjust_volume",
        "mute", "get_system_status", "network_speed",
        "read_active_file", "jarvis_clip_that",
        "aquire_links", "search_web", "capture_and_analyze"
    }

    def __init__(self):
        load_dotenv()

        print("Loading Vosk model...")
        self.vosk_model = VoskModel("models/vosk-small/vosk-model-small-en-us-0.15")
        self.recognizer = KaldiRecognizer(self.vosk_model, self.RATE)
        print("Vosk ready.")

        print("Loading Whisper model...")
        self.whisper_model = whisper.load_model("base")
        print("Whisper ready.")

        print("Initializing voice...")
        self.voice = JarvisVoice()
        print("Voice ready.")

        print("Initializing Anthropic client...")
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        print("Anthropic ready.")

        self.MAX_HISTORY = 7
        self.CONVERSATION_MODE = False
        self.last_interaction = time.time()

        self.partial_text = ""
        self.last_speech_time = 0.0
        self.command_buffer: list[bytes] = []
        self.last_voice_chunk_time = 0.0
        self.collecting_command = False

        self.audio_buffer = deque(maxlen=50)
        self.frame_buffer = deque(maxlen=50)

        # Injected by the WebSocket server when a client connects
        self.remote_tool = None

        print("Loading memory...")
        if Path("memory.json").exists():
            self.message_history = json.load(open("memory.json"))
        else:
            self.message_history = []
            with open("memory.json", "w") as f:
                json.dump(self.message_history, f, cls=AnthropicEncoder, indent=2)
        print("Memory ready.")

        print("Loading tools...")
        # server-side tools — run locally on the server
        self.tool_map = {
            "clear_and_play": clear_and_play,
            "play": play,
            "pause": pause,
            "resume": resume,
            "currently_playing": currently_playing,
            "commit": commit,
            "status": status,
            "push": push,
            "weather_data": weather_data,
        }

        server_tools = [fn.to_dict() for fn in self.tool_map.values() if hasattr(fn, "to_dict")]

        # Client-side tools — schemas only, execution happens on client via RPC
        client_tools = [
            {
                "name": "open_app",
                "description": "Open an application on the user's machine.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "app": {"type": "string", "description": "The name or path of the application to open"}
                    },
                    "required": ["app"]
                }
            },
            {
                "name": "close_app",
                "description": "Close a running application on the user's machine.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "app": {"type": "string", "description": "The name of the application to close"}
                    },
                    "required": ["app"]
                }
            },
            {
                "name": "set_volume",
                "description": "Set the system volume to a specific level.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "volume": {"type": "number", "description": "Volume level from 0 to 100"}
                    },
                    "required": ["volume"]
                }
            },
            {
                "name": "adjust_volume",
                "description": "Adjust the system volume up or down by a relative amount.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "volume": {"type": "number",
                                   "description": "Amount to adjust by, positive to increase, negative to decrease"}
                    },
                    "required": ["volume"]
                }
            },
            {
                "name": "mute",
                "description": "Toggle mute on the system audio.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_system_status",
                "description": "Get CPU, RAM, disk, network, and GPU stats from the user's machine.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "network_speed",
                "description": "Get the current network upload and download speed.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "read_active_file",
                "description": "Read the currently active file open in the IDE.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "jarvis_clip_that",
                "description": "Clip the last 30 seconds of screen recording and save it.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name to save the clip as"}
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "aquire_links",
                "description": "Get the link to a url based of a query",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What the user wants to search for"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_web",
                "description": "Open a browser page and open the given url",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Given url to seacrh/open"}
                    },
                    "required": ["url"]
                }
            },
        {
            "name": "capture_and_analyze",
            "description": "Take a picture using the camera and then analyze what it shows",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "name for the file"},
                "message": {"type": "string", "description": "The message to prompt the llm"}
            },
            "required": ["filename", "message"]
        }
        },

        ]

        self.tools = server_tools + client_tools
        print("Tools ready.")

    # ----------------- Helpers -----------------

    def _rms(self, chunk: bytes) -> float:
        audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(audio ** 2))) if len(audio) else 0.0

    @staticmethod
    def _normalize_chunk(chunk: bytes) -> bytes:
        audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio * min(20000.0 / peak, 10.0)
        return audio.astype(np.int16).tobytes()

    def _whisper_transcribe(self, pcm_chunks: list[bytes]) -> str:
        raw = b"".join(pcm_chunks)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        result = self.whisper_model.transcribe(
            audio,
            language="en",
            fp16=False,
            condition_on_previous_text=False,
        )
        return result["text"].strip()

    def _is_farewell(self, text: str) -> bool:
        return any(word in text.lower() for word in self.FAREWELL_WORDS)

    # ----------------- Tool Executor -----------------

    def tool_executor(self, name: str, inputs: dict, loop: asyncio.AbstractEventLoop) -> str:
        print(f"[Tool] Executing: {name} inputs: {inputs}")
        if name in self.CLIENT_SIDE_TOOLS:
            if self.remote_tool is None:
                return "No client connected"
            future = asyncio.run_coroutine_threadsafe(
                self.remote_tool(name, inputs),
                loop
            )
            try:
                return future.result(timeout=15.0)
            except TimeoutError:
                return f"Tool {name} timed out waiting for client"

        fn = self.tool_map.get(name)
        if fn is None:
            return f"Unknown tool: {name}"
        result = fn.func(**inputs)
        print(f"[Tool] {name} returned: {result}")
        return str(result) if result is not None else "Done"

    # ----------------- Audio Processing -----------------

    async def process_audio(self, chunk: bytes) -> bytes:
        now = time.time()
        rms = self._rms(chunk)
        normalized = self._normalize_chunk(chunk)
        is_speech = rms > self.SILENCE_RMS_THRESHOLD

        # Phase 1: Wake-word detection via Vosk
        if not self.CONVERSATION_MODE:
            if self.recognizer.AcceptWaveform(normalized):
                text = json.loads(self.recognizer.Result()).get("text", "")
            else:
                text = json.loads(self.recognizer.PartialResult()).get("partial", "")

            if "hey jarvis" in text.lower():
                self.recognizer.Reset()
                self.CONVERSATION_MODE = True
                self.collecting_command = False
                self.command_buffer.clear()
                self.last_interaction = now
                print("[Vosk] Wake word detected")
                return self.voice.TTS_bytes("Yes, sir")
            return b""

        # Phase 2: Command collection + Whisper transcription
        if is_speech:
            self.command_buffer.append(normalized)
            self.last_voice_chunk_time = now
            self.collecting_command = True
        elif self.collecting_command:
            self.command_buffer.append(normalized)
            silence_duration = now - self.last_voice_chunk_time

            if silence_duration >= self.SILENCE_LIMIT:
                collected_duration = len(self.command_buffer) * self.CHUNK / self.RATE

                if collected_duration < self.MIN_COMMAND_DURATION:
                    self.command_buffer.clear()
                    self.collecting_command = False
                    return b""

                print(f"[Whisper] Transcribing {collected_duration:.1f}s of audio...")
                text = await asyncio.to_thread(
                    self._whisper_transcribe, list(self.command_buffer)
                )
                self.command_buffer.clear()
                self.collecting_command = False

                if not text:
                    return b""

                print(f"[Whisper] Recognized: {text}")
                print("[Jarvis] Calling _handle_command...")
                result = await self._handle_command(text, now)
                print(f"[Jarvis] _handle_command returned {len(result)} bytes")
                return result

        return b""

    # ----------------- Command Handler -----------------

    async def _handle_command(self, text: str, now: float) -> bytes:
        if self._is_farewell(text):
            self.stop_listening()
            return self.voice.TTS_bytes("Goodbye, sir.")

        self.message_history.append({"role": "user", "content": text})
        self.message_history = self.message_history[-self.MAX_HISTORY:]

        loop = asyncio.get_running_loop()
        print("[Jarvis] Calling Anthropic...")
        query = await asyncio.to_thread(self.run_with_tools, self.message_history, loop)
        print(f"[Jarvis] Anthropic returned: {query}")

        self.message_history.append({"role": "assistant", "content": query})
        with open("memory.json", "w") as f:
            json.dump(self.message_history, f, cls=AnthropicEncoder, indent=2)

        self.last_interaction = now

        print("[Jarvis] Generating TTS...")
        return self.voice.TTS_bytes(query)

    # ----------------- Tool Loop -----------------

    def run_with_tools(self, messages: list, loop: asyncio.AbstractEventLoop) -> str:
        messages = list(messages)
        try:
            while True:
                response = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=512,
                    tools=self.tools,
                    system=self.SYSTEM_PROMPT,
                    messages=messages
                )
                print(f"[Anthropic] stop_reason: {response.stop_reason}")

                if response.stop_reason == "end_turn":
                    return next((b.text for b in response.content if hasattr(b, "text")), "")

                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self.tool_executor(block.name, block.input, loop)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result) if result is not None else "Done"
                        })

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error: {e}"

    # ----------------- Cleanup -----------------

    def stop_listening(self):
        self.CONVERSATION_MODE = False
        self.collecting_command = False
        self.command_buffer.clear()
        print("[Jarvis] Waiting for wake word...")