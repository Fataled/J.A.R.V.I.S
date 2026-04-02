from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import numpy as np

class VoiceRecognition:

    def __init__(self):
        self.encoder = VoiceEncoder()
        if Path("../my_voice.npy").exists():
            self.speaker_embedding = np.load("../my_voice.npy")
        else:
            self.wavs = [preprocess_wav(p) for p in Path("../audio recordings").glob("j*.wav")]
            self.embeddings = [self.encoder.embed_utterance(wav) for wav in self.wavs]

            for i, e1 in enumerate(self.embeddings):
                for j, e2 in enumerate(self.embeddings):
                    sim = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
                    print(f"Clip {i} vs Clip {j}: {sim:.3f}")

            self.speaker_embedding = np.mean(self.embeddings, axis=0)
            np.save("../my_voice.npy", self.speaker_embedding)

    def compare(self, audio_input):
        #print(f"Input shape: {audio_input.shape}, min: {audio_input.min()}, max: {audio_input.max()}")
        audio_embedding = self.encoder.embed_utterance(audio_input)
        #print(f"Embedding norm: {np.linalg.norm(audio_embedding)}")
        #print(f"Speaker norm: {np.linalg.norm(self.speaker_embedding)}")
        return np.dot(self.speaker_embedding, audio_embedding) / (np.linalg.norm(self.speaker_embedding) * np.linalg.norm(audio_embedding))

