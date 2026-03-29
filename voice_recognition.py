from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import numpy as np

class VoiceRecognition:

    def __init__(self):
        self.encoder = VoiceEncoder()
        self.wavs = [preprocess_wav(p) for p in Path("voiceRecordings").glob("*.wav")]
        self.embeddings = [self.encoder.embed_utterance(wav) for wav in self.wavs]
        self.speaker_embedding = np.mean(self.embeddings, axis=0)

    def compare(self, audio_input):
        audio_embedding = self.encoder.embed_utterance(audio_input)
        return np.dot(self.speaker_embedding, audio_embedding) / (np.linalg.norm(self.speaker_embedding) * np.linalg.norm(audio_embedding))

