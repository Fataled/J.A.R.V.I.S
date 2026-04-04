import time
from pathlib import Path
from dotenv import load_dotenv
from piper import PiperVoice
from scipy.signal import resample_poly
from math import gcd
import numpy as np

load_dotenv()

SAMPLE_RATE = 24000


class BMOVoice:
    def __init__(self):
        self.piper_voice = PiperVoice.load(Path("models/bmo.onnx"))

    def _resample(self, audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        g = gcd(from_rate, to_rate)
        resampled = resample_poly(audio, to_rate // g, from_rate // g)
        return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()

    def _piper_bytes(self, text: str) -> bytes:
        chunks = []
        for chunk in self.piper_voice.synthesize(text):
            chunks.append(self._resample(chunk.audio_int16_bytes, 22050, SAMPLE_RATE))
        return b"".join(chunks)

    def _piper_stream(self, text: str):
        for chunk in self.piper_voice.synthesize(text):
            yield self._resample(chunk.audio_int16_bytes, 22050, SAMPLE_RATE)

    def TTS_bytes(self, text: str) -> bytes:
            return self._piper_bytes(text)

