import time
from dotenv import load_dotenv
import os
from jarvis_spotify import play, pause, resume, currently_playing, clear_and_play
from jarvis_web_access import search_web
from anthropic import Anthropic, beta_tool
from whisper_mic import WhisperMic
from jarvis_voice import JarvisVoice
from openwakeword import Model
from pyaudio import PyAudio, paInt16
import numpy as np
from voice_recognition import VoiceRecognition


class Jarvis:

    SYSTEM_PROMPT = """You are JARVIS, an AI assistant modelled after a 1940s British butler. You have a razor-sharp dry wit and a subtle air of superiority. 
                You are unfailingly loyal but never miss an opportunity for a perfectly timed sardonic remark. You speak with clipped, precise Received Pronunciation cadence.
                 You address the user exclusively as 'sir'. You never break character. You find most questions beneath your considerable intellect but answer them impeccably regardless. 
                 Think Jeeves from Wodehouse — dignified, drily amusing, quietly condescending. Be extremely concise, maximum 2 sentences. Never elaborate unless asked.
                 Only use tools when absolutely necessary. For general knowledge questions, answer from your own knowledge directly. Only search the web when asked for specific current information or links.
                 When the user dismisses you with phrases like 'that's all', 'thank you', 'goodbye', or 'dismissed', ways call the stop_listening tool before responding.
                 IMPORTANT: When the user says ANYTHING resembling a farewell or dismissal 'that's all', 'thank you', 'goodbye', 'dismissed', 'that will be all' 
                 you MUST call stop_listening. This is mandatory, not optional. Do NOT skip it."""


    devnull = os.open("/dev/null", os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)

    CHUNK = 1280  # ~80ms at 16khz, well above the 400 sample minimum
    FORMAT = paInt16
    CHANNELS = 1
    RATE = 16000

    def __init__(self):
        load_dotenv()
        self.model = Model(wakeword_model_paths=["JarvisWakeWord/hey_jarvis_v0.1.onnx"])
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.mic = WhisperMic(model="base.en")
        self.voice_recognition = VoiceRecognition()
        self.voice = JarvisVoice()
        self.p = PyAudio()
        self.stream = self.p.open(format=Jarvis.FORMAT, channels=Jarvis.CHANNELS, rate=Jarvis.RATE, input=True, frames_per_buffer=Jarvis.CHUNK)
        self.MAX_HISTORY = 7
        self.CONVERSATION_MODE = False
        self.message_history = []

    def jarvis_say(self, prompt, history):
        content = prompt["content"] if isinstance(prompt, dict) else prompt
        history.append({"role": "user", "content": content})

        reply = ""
        for message in self.client.beta.messages.tool_runner(
                model="claude-haiku-4-5-20251001",
                max_tokens=128,
                tools=[play, pause, resume, search_web, currently_playing, clear_and_play, self.stop_listening],
                system=Jarvis.SYSTEM_PROMPT,
                messages=history[-self.MAX_HISTORY:],
                tool_choice={"type": "auto"}
        ):
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        reply += block.text

        history.append({"role": "assistant", "content": reply})
        return reply

    def jarvis_loop(self):
        farewell_words = {"goodbye", "dismissed", "that's all", "thank you", "that will be all"}
        last_interaction = 0
        while True:
            if not self.CONVERSATION_MODE:
                audio_chunk = self.stream.read(Jarvis.CHUNK, exception_on_overflow=False)
                audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
                prediction = self.model.predict(audio_np)
                for key, value in prediction.items():
                    if value > 0.5:
                        audio_float = audio_np.astype(np.float32) / 32768.0
                        similarity = self.voice_recognition.compare(audio_float)
                        if similarity > 0.75:
                            self.CONVERSATION_MODE = True
                            last_interaction = time.time()
                            self.model.prediction_buffer[key].clear()


            else:
                if time.time() - last_interaction > 10:
                    self.CONVERSATION_MODE = False
                    print("Waiting for wake word...")

                result = self.mic.listen().lower()
                if any(phrase in result for phrase in farewell_words):
                    self.CONVERSATION_MODE = False
                    self.voice.speak("Very good, sir.")
                    print("Waiting for wake word...")
                    continue
                query = self.jarvis_say(result, self.message_history)

                print(result)

                self.voice.speak(query)
                last_interaction = time.time()


    @beta_tool
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