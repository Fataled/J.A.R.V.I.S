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

    def TTS_stream(self, text, chunk_size_ms=200):
        """Yield PCM in ~200ms batches instead of one tiny chunk at a time."""
        samples_per_batch = int(24000 * chunk_size_ms / 1000)  # 4800 samples @ 200ms
        buffer = []
        total_samples = 0

        for _, _, audio in self.pipeline(text=text, voice="bm_george"):
            buffer.append(audio)
            total_samples += len(audio)
            if total_samples >= samples_per_batch:
                combined = np.concatenate(buffer)
                yield (combined * 32767).astype(np.int16).tobytes()
                buffer = []
                total_samples = 0

        # flush remainder
        if buffer:
            combined = np.concatenate(buffer)
            yield (combined * 32767).astype(np.int16).tobytes()
