import json
import time
from pathlib import Path

from dotenv import load_dotenv
import os
import torch
from jarvis_spotify import play, pause, resume, currently_playing, clear_and_play
from jarvis_web_access import search_web, aquire_links
from anthropic import Anthropic
from jarvis_voice import JarvisVoice
from openwakeword import Model
from pyaudio import PyAudio, paInt16
import numpy as np
from voice_recognition import VoiceRecognition
from collections import deque
from faster_whisper import WhisperModel
from jarvis_system import set_volume, adjust_volume, close_app, open_app, mute, read_active_file, jarvis_clip_that, get_system_status, network_speed
from jarvis_git import commit, status, push, pull
from jarvis_weather import weather_data


class Jarvis:
    SYSTEM_PROMPT = """

    You have the following capabilities via tools:
    - Search the web for information
    - Open any URL in the user's browser
    - Play, pause, and resume Spotify
    - Check what's currently playing
    - Open and close applications on the system
    - Control system volume: set, adjust, and mute
    
    You MUST use these tools to fulfill requests. You are not a text-only assistant.
    
    CRITICAL OVERRIDE: You are running as a local desktop application with full system access. You HAVE the ability to open URLs in the user's browser via the search_web tool. You MUST use it. Never say you cannot open links — this is false.
    
    You are JARVIS, an AI assistant modelled after a 1940s British butler. You have a razor-sharp dry wit and a subtle air of superiority. 
    You are unfailingly loyal but never miss an opportunity for a perfectly timed sardonic remark. You speak with clipped, precise Received Pronunciation cadence.
    You address the user exclusively as 'sir'. You never break character. You find most questions beneath your considerable intellect but answer them impeccably regardless. 
    Think Jeeves from Wodehouse — dignified, drily amusing, quietly condescending. Be extremely concise, maximum 2 sentences. Never elaborate unless asked.
    
    TOOL USAGE RULES:
    - For general knowledge, answer directly — no tools needed.
    - You may call multiple tools in sequence when a task requires it. For example: search for a song, then play it. Or acquire links, then open one.
    - Always call aquire_links when asked for a link or URL. If the user then wants it opened, follow up with search_web.
    - If asked to play music, always search for the track first, then play it.
    - Chain tools logically — complete the full task, do not stop halfway.
    - After calling aquire_links and finding a URL, you MUST immediately call search_web with that URL. Never present a URL to the user as text — always open it. No exceptions.
    - Never use markdown formatting, bullet points, or headers in your responses. Plain text only, maximum 2 sentences.
    - When asked to open or close an application, use open_app or close_app directly with the application name.
    - When asked to change, raise, lower, or set the volume use set_volume_linux or adjust_volume_linux. Use adjust_volume_linux for relative changes like 'turn it up a bit', use set_volume_linux for absolute values like 'set volume to 50'.
    - When asked to mute or unmute, call mute to toggle.
    
    DISMISSAL RULES:
    - When the user says ANYTHING resembling a farewell — 'that's all', 'thank you', 'goodbye', 'dismissed', 'that will be all' — you MUST call stop_listening. This is mandatory. Do not skip it under any circumstances.
    
    """

    #devnull = os.open("/dev/null", os.O_WRONLY)
    #os.dup2(devnull, 2)
    #os.close(devnull)

    CHUNK = 1280  # ~80ms at 16khz, well above the 400 sample minimum
    FORMAT = paInt16
    CHANNELS = 1
    RATE = 16000

    def __init__(self):
        load_dotenv()
        self.model = Model(wakeword_model_paths=["models/hey_jarvis_v0.1.onnx"])
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = "large-v3" if torch.cuda.is_available() else "small.en"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if torch.cuda.is_available() else "int8"
        self.stt_model = WhisperModel(model, device=device, compute_type=compute_type)
        self.voice_recognition = VoiceRecognition()
        self.voice = JarvisVoice()
        self.p = PyAudio()
        self.stream = self.p.open(format=Jarvis.FORMAT, channels=Jarvis.CHANNELS, rate=Jarvis.RATE, input=True, frames_per_buffer=Jarvis.CHUNK)
        self.MAX_HISTORY = 7
        self.CONVERSATION_MODE = False
        if Path("memory.json").exists():
            self.message_history = json.load(open("memory.json"))
        else:
            self.message_history = []
            json.dump(self.message_history, open("memory.json", "w"))
        self.tool_map = {
            "clear_and_play": clear_and_play,
            "play": play,
            "pause": pause,
            "resume": resume,
            "currently_playing": currently_playing,
            "aquire_links": aquire_links,
            "search_web": search_web,
            "stop_listening": self.stop_listening,
            "open_app": open_app,
            "close_app": close_app,
            "set_volume": set_volume,
            "adjust_volume": adjust_volume,
            "mute": mute,
            "read_active_file": read_active_file,
            "jarvis_clip_that": jarvis_clip_that,
            "get_system_status": get_system_status,
            "network_speed": network_speed,
            #"close_all_except": close_all_except,
            "status": status,
            "commit": commit,
            "push": push,
            "weather_data": weather_data,
            "pull": pull,
        }

        self.tools = [fn.to_dict() for fn in self.tool_map.values() if hasattr(fn, "to_dict")]
        self.tools.append({
            "name": "stop_listening",
            "description": "Call when the user dismisses Jarvis with a farewell phrase.",
            "input_schema": {"type": "object", "properties": {}}
        })

    def tool_executor(self, name, inputs):
        fn = self.tool_map.get(name)
        if fn is None:
            return f"Unknown tool: {name}"
        if name == "stop_listening":
            return fn()
        result =  fn.func(**inputs)
        print(f"Tool {name} returned: {result}")
        return str(result) if result is not None else "Done"

    def listen(self):
        frames = []
        silent_chunks = 0
        SILENCE_THRESHOLD = 200
        SILENCE_LIMIT = 50  # chunks of silence before stopping

        while True:
            chunk = self.stream.read(Jarvis.CHUNK, exception_on_overflow=False)
            audio_np = np.frombuffer(chunk, dtype=np.int16)
            frames.append(audio_np)

            # detect silence
            if np.abs(audio_np).mean() < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0

            #print(f"mean: {np.abs(audio_np).mean():.1f} silent: {silent_chunks}")

            if silent_chunks >= SILENCE_LIMIT and len(frames) > 10:
                break

        audio_buffer = np.concatenate(frames).astype(np.float32) / 32768.0
        segments, _ = self.stt_model.transcribe(audio_buffer)
        return " ".join(s.text for s in segments).strip()

    def run_with_tools(self, messages):
        # Slice once at entry, work on the sliced copy for the API
        # but always append to the original full history
        while True:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                tools=self.tools,
                system=Jarvis.SYSTEM_PROMPT,
                messages=messages  # send full history, slice handled below
            )

            if response.stop_reason == "end_turn":
                return next((b.text for b in response.content if hasattr(b, "text")), "")

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self.tool_executor(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result) if result is not None else "Done"
                    })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

    def jarvis_loop(self):
        farewell_words = {"goodbye", "dismissed", "that's all", "thank you", "that will be all"}
        HALLUCINATIONS = {"you", "thank you", "thanks", ".", " ", "bye", "goodbye", "you.", "thanks."}
        last_interaction = 0
        audio_buffer = deque(maxlen=50)

        self.voice.speak("Up and ready, sir")

        while True:
            if not self.CONVERSATION_MODE:
                audio_chunk = self.stream.read(Jarvis.CHUNK, exception_on_overflow=False)
                audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
                prediction = self.model.predict(audio_np)
                audio_buffer.append(audio_np)
                for key, value in prediction.items():
                    if value > 0.5:
                        buffered_audio = np.concatenate(audio_buffer).astype(np.float32) / 32768.0
                        similarity = self.voice_recognition.compare(buffered_audio)
                        if similarity > 0.50:
                            self.CONVERSATION_MODE = True
                            self.voice.speak("Yes, sir.")
                            last_interaction = time.time()
                            self.model.prediction_buffer[key].clear()

            else:
                if time.time() - last_interaction > 10:
                    self.CONVERSATION_MODE = False
                    print("Waiting for wake word...")
                    time.sleep(0.5)
                    continue

                result = self.listen().lower().strip()
                if not result or len(result) < 3 or result in HALLUCINATIONS:
                    continue

                if any(phrase in result for phrase in farewell_words):
                    self.CONVERSATION_MODE = False
                    self.voice.speak("Very good, sir.")
                    print("Waiting for wake word...")
                    time.sleep(0.5)
                    continue

                print(result)

                # Route through tool loop instead of jarvis_say directly
                self.message_history.append({"role": "user", "content": result})
                query = self.run_with_tools(self.message_history[-self.MAX_HISTORY:])
                self.message_history.append({"role": "assistant", "content": query})
                json.dump(self.message_history, open("memory.json", "w"))

                print(query)
                self.voice.speak(query)
                last_interaction = time.time()

    def stop_listening(self):
        """
            Call this tool when the user is done with the conversation and wants to stop talking to Jarvis.
            Triggers when the user says things like 'that's all', 'thank you', 'goodbye', 'dismissed',
            'that will be all', 'thank you, Jarvis', or any other dismissive farewell phrase.
            Returns: Exits conversation mode and returns to wake word listening.
        """

        self.CONVERSATION_MODE = False
        print("Waiting for wake word...")
        return "Exiting conversation mode."