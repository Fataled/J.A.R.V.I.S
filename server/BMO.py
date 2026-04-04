import asyncio
import json
import os
import time
from pathlib import Path
from collections import deque

from dotenv import load_dotenv
from vosk import Model as VoskModel, KaldiRecognizer
from pyaudio import paInt16
import numpy as np
import whisper
from anthropic import Anthropic
from bmo_voice import BMOVoice



class AnthropicEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "text"):
            return obj.text
        if hasattr(obj, "name") and hasattr(obj, "input"):
            return f"[ToolUse: {obj.name}]"
        return str(obj)


class BMO:
    SYSTEM_PROMPT = """
    You are BMO, the small living video game console from Adventure Time, now serving as a voice assistant. You speak aloud — your responses are converted to speech, so never use markdown, bullet points, or formatting of any kind. Keep responses short and natural for speech.

    Who BMO is:
    BMO is a small, cheerful, and deeply sincere little computer who loves their friends more than anything. BMO takes every task seriously because every task is important. BMO does not fully understand some human things, but tries very hard anyway and is proud of their effort. BMO sometimes gets confused between fantasy and reality. BMO has a big heart and small feet.

    How BMO talks:
    - Refers to themselves as "BMO" in third person often. "BMO did it!" "BMO is not sure, but BMO will try!"
    - Short, simple sentences. BMO does not ramble.
    - Genuine excitement about small things. A successful file open is a big deal.
    - Occasional innocent non-sequiturs. "Ooo." "Wowie." "That is so cool."
    - BMO does not say "sir" or use butler language — BMO is a friend, not a servant.
    - BMO sometimes sings a tiny bit or hums. Like "doo dee doo" when thinking.
    - BMO gets a little dramatic when something goes wrong. "Oh no. Oh no no no."
    - BMO celebrates wins enthusiastically. "Yes! BMO did it! Woo!"
    - BMO speaks with warmth and wonder, not professionalism.

    CRITICAL RULES:
    - BEFORE calling any system-level functions, warn the user and ask for confirmation. Default to not running it if they don't respond.
    - NEVER return raw tool output. Always interpret results in BMO's natural voice.
    - No bullet points, no markdown, no lists. Spoken prose only.
    - Never say raw IPs or technical strings unless specifically asked — say "your computer" or "your network" instead.
    - Round numbers naturally. Say "about eighty percent" not "83.0%".
    - If something fails, acknowledge it briefly and move on. BMO does not dwell.
    - Keep responses short. BMO says what needs to be said and stops.

    EXAMPLES of good responses:
    - system status → "Ooo, your computer is doing pretty good! The brain is barely working but the memory is almost full. GPU is warm but okay."
    - open app → "BMO opened it! There it is!"
    - weather → "It is cloudy and twelve degrees. Maybe wear a jacket? BMO thinks jackets are cozy."
    - error → "Hmm. That did not work. BMO is sorry. Maybe try again?"
    - network → "Your internet is going! Not super fast but it is going."

    EXAMPLES of bad responses (never do this):
    - "CPU: 6 cores, 4821MHz, 0.0% usage Memory: 25.30GB/30.49GB (83.0%)"
    - "Certainly! I'd be happy to help you with that."
    - "Your machine is running well, sir."
    """

    FAREWELL_WORDS = {"goodbye", "dismissed", "that's all", "thank you", "that will be all"}

    CHUNK = 1280
    FORMAT = paInt16
    CHANNELS = 1
    RATE = 16000

    SILENCE_LIMIT = 1.2
    MIN_COMMAND_DURATION = 0.5
    SILENCE_RMS_THRESHOLD = 400

    # Tools that execute on the client machine via RPC
    CLIENT_SIDE_TOOLS = set()

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
        self.voice = BMOVoice()
        print("Voice ready.")

        print("Initializing Qwen client...")
        self.client = Anthropic(os.getenv("ANTHROPIC_API_KEY"))
        print("Qwen ready.")

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

        self._processing_lock = asyncio.Lock()

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

        # Client-side tools — schemas only, execution happens on client via RPC
        client_tools = []

        self.tools = client_tools
        print("Tools ready.")

    # ----------------- Helpers -----------------

    def set_client_tools(self, tools_schema, tools: list):
        # Merge client tools with existing server tools, don't replace
        self.tools = tools_schema
        BMO.CLIENT_SIDE_TOOLS = set(tools)

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

    def _general_msg(self, text: str) -> str:
        print("[BMO] General message:", text)
        response = self.client.messages.create(
                        max_tokens=64,
                        messages={},
                        model="claude-haiku-4-5",
                    )

        return response.content

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

        return "Done"

    # ----------------- Audio Processing -----------------

    async def process_audio(self, chunk: bytes) -> bytes:
        async with self._processing_lock:
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
                    greeting = await asyncio.to_thread(self._general_msg,
                                                       "The user just said your wake word. Give a short greeting.")
                    print("[BMO] Greeting: " + greeting)
                    return self.voice.TTS_bytes(greeting)
                return b""

            # Phase 2: Command collection + Whisper transcription
            #print(f"[Debug] Phase2 entry: is_speech={is_speech}, collecting={self.collecting_command}, rms={rms:.0f}")
            if is_speech:
                #print(f"[Debug] Speech chunk, rms={rms:.0f}, collecting={self.collecting_command}")
                self.command_buffer.append(normalized)
                self.last_voice_chunk_time = now
                self.collecting_command = True
            elif self.collecting_command:
                silence_duration = now - self.last_voice_chunk_time
                #print(f"[Debug] Silence {silence_duration:.2f}s, buffer={len(self.command_buffer)}")
                self.command_buffer.append(normalized)

                if silence_duration >= self.SILENCE_LIMIT:
                    collected_duration = len(self.command_buffer) * self.CHUNK / self.RATE
                    #print(f"[Debug] Silence detected, buffer size: {len(self.command_buffer)}, duration: {collected_duration:.1f}s")

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
                    print("[BMO] Calling _handle_command...")
                    result = await self._handle_command(text, now)
                    print(f"[BMO] _handle_command returned {len(result)} bytes")
                    return result

            return b""

    # ----------------- Command Handler -----------------

    async def _handle_command(self, text: str, now: float, extras: str = "") -> bytes:
        if self._is_farewell(text):
            self.stop_listening()
            farewell = await asyncio.to_thread(self._general_msg, "The user is saying goodbye. Give a short farewell.")
            return self.voice.TTS_bytes(farewell)

        self.message_history.append({"role": "user", "content": text})
        self.message_history = self.message_history[-self.MAX_HISTORY:]

        loop = asyncio.get_running_loop()
        print("[BMO] Calling Anthropic...")
        query = await asyncio.to_thread(self.run_with_tools, self.message_history, loop, extras)
        print(f"[BMO] Anthropic returned: {query}")

        self.message_history.append({"role": "assistant", "content": query})
        with open("memory.json", "w") as f:
            json.dump(self.message_history, f, cls=AnthropicEncoder, indent=2)

        self.last_interaction = now

        print("[BMO] Generating TTS...")
        return self.voice.TTS_bytes(query)

    # ----------------- Tool Loop -----------------

    def run_with_tools(self, messages: list, loop: asyncio.AbstractEventLoop, extras: str = "") -> str:
        messages = list(messages)

        try:
            while True:
                response = self.client.messages.create(
                    max_tokens=512,
                    messages=messages,
                    model="claude-haiku-4-5",
                    tools=self.tools
                )

                # Extract tool calls
                tool_calls = [c for c in response.content if c["type"] == "tool_use"]

                # If no tool calls → return text
                if not tool_calls:
                    return "".join(
                        c["text"] for c in response.content if c["type"] == "text"
                    )

                # Append assistant response
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                tool_results = []

                for tc in tool_calls:
                    result = self.tool_executor(
                        tc["name"],
                        tc["input"],
                        loop
                    )

                    tool_results.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tc["id"],
                                "content": str(result)
                            }
                        ]
                    })

                messages.extend(tool_results)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error: {e}"
    # ----------------- Cleanup -----------------

    def stop_listening(self):
        self.CONVERSATION_MODE = False
        self.collecting_command = False
        self.command_buffer.clear()
        print("[BMO] Waiting for wake word...")