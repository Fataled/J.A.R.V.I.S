import numpy as np
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import os
from elevenlabs.play import play
from kokoro import KPipeline
import sounddevice as sd

load_dotenv()

class JarvisVoice:
    def __init__(self):
        self.elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        self.pipeline = KPipeline(lang_code="b", repo_id='hexgrad/Kokoro-82M')

    def speak(self, text):
        try:
            response = self.elevenlabs.text_to_speech.convert(
                voice_id="5vpmAScR72nJ1oEJtE8f",
                output_format="mp3_22050_32",
                text=text,
                model_id="eleven_v3"
            )

            play(response)
        except Exception as e:
            if "quota_exceeded" in str(e):
                print(f"Elevenlabs quota hit: {e}")
                generator = self.pipeline(text=text, voice="bm_george")
                for _, _, audio in generator:
                    sd.play(audio, samplerate=24000)
                    sd.wait()

    def TTS_bytes(self, text):
        chunks = []
        generator = self.pipeline(text=text, voice="bm_george")
        for _, _, audio in generator:
            chunks.append(audio)
        if not chunks:
            return b""
        audio = np.concatenate(chunks)
        return (audio * 32767).astype(np.int16).tobytes()
