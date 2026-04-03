import base64
import io
import os
import numpy as np
from dotenv import load_dotenv
from kokoro import KPipeline
from mistralai.client import Mistral
from pydub import AudioSegment
AudioSegment.ffprobe = "/usr/bin/ffprobe"
AudioSegment.converter = "/usr/bin/ffmpeg"

load_dotenv()

SAMPLE_RATE = 24000
VOXTRAL_MODEL = "voxtral-mini-tts-2603"
VOXTRAL_VOICE = "casual_male"


class JarvisVoice:
    def __init__(self):
        self.pipeline = KPipeline(lang_code="b", repo_id='hexgrad/Kokoro-82M')
        self._init_voxtral()

    def _init_voxtral(self):
        api_key = os.getenv("VOXTRAL_API_KEY")
        if api_key:
            self.mistral = Mistral(api_key=api_key)
            self.voice_id = os.getenv("BMO_VOICE_ID")
            self.voxtral_available = True
            print("[JarvisVoice] Voxtral ready")
        else:
            self.mistral = None
            self.voxtral_available = False
            print("[JarvisVoice] No VOXTRAL_API_KEY — Kokoro only")

    def TTS_bytes(self, text: str) -> bytes:
        """Primary TTS. Returns raw PCM Int16 bytes at 24kHz mono."""
        if self.voxtral_available:
            result = self._voxtral_bytes(text)
            if result:
                return result
            print("[JarvisVoice] Voxtral failed, falling back to Kokoro")
        return self._kokoro_bytes(text)

    def TTS_stream(self, text: str, chunk_size_ms: int = 200):
        """Streaming TTS — yields PCM Int16 bytes in chunks."""
        if self.voxtral_available:
            success = False
            for chunk in self._voxtral_stream(text):
                success = True
                yield chunk
            if success:
                return
            print("[JarvisVoice] Voxtral stream failed, falling back to Kokoro")
        yield from self._kokoro_stream(text, chunk_size_ms)

    # ── Voxtral ───────────────────────────────────────────────────────────────

    def _voxtral_bytes(self, text: str) -> bytes | None:
        try:
            audio_chunks = []
            with self.mistral.audio.speech.complete(**self._voxtral_kwargs(text)) as stream:
                for event in stream:
                    if event.event == "speech.audio.delta":
                        audio_chunks.append(base64.b64decode(event.data.audio_data))
            if not audio_chunks:
                return None
            return self._opus_to_pcm(b"".join(audio_chunks))
        except Exception as e:
            print(f"[JarvisVoice] Voxtral error: {e}")
            return None

    def _voxtral_stream(self, text: str):
        try:
            accumulated = []
            with self.mistral.audio.speech.complete(**self._voxtral_kwargs(text)) as stream:
                for event in stream:
                    if event.event == "speech.audio.delta":
                        accumulated.append(base64.b64decode(event.data.audio_data))
            if accumulated:
                yield self._opus_to_pcm(b"".join(accumulated))
        except Exception as e:
            print(f"[JarvisVoice] Voxtral stream error: {e}")

    def _voxtral_kwargs(self, text: str) -> dict:
        kwargs = dict(model=VOXTRAL_MODEL, input=text, response_format="opus", stream=True)
        if self.voice_id:
            kwargs["voice_id"] = self.voice_id
        else:
            kwargs["voice"] = VOXTRAL_VOICE
        return kwargs

    @staticmethod
    def _opus_to_pcm(opus_bytes: bytes) -> bytes:
        audio = AudioSegment.from_file(io.BytesIO(opus_bytes))
        audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)
        return audio.raw_data

    # ── Kokoro fallback ───────────────────────────────────────────────────────

    def _kokoro_bytes(self, text: str) -> bytes:
        chunks = []
        for _, _, audio in self.pipeline(text=text, voice="bm_george"):
            chunks.append(audio)
        if not chunks:
            return b""
        return (np.concatenate(chunks) * 32767).astype(np.int16).tobytes()

    def _kokoro_stream(self, text: str, chunk_size_ms: int = 200):
        samples_per_batch = int(SAMPLE_RATE * chunk_size_ms / 1000)
        buffer, total = [], 0
        for _, _, audio in self.pipeline(text=text, voice="bm_george"):
            buffer.append(audio)
            total += len(audio)
            if total >= samples_per_batch:
                yield (np.concatenate(buffer) * 32767).astype(np.int16).tobytes()
                buffer, total = [], 0
        if buffer:
            yield (np.concatenate(buffer) * 32767).astype(np.int16).tobytes()