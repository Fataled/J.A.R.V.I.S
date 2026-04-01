import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer

# Use the correct path to your vosk model
model = Model("models/vosk-small/vosk-model-small-en-us-0.15")
recognizer = KaldiRecognizer(model, 16000)

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

# Record 5 seconds of audio
with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    print("Say something!")
    for _ in range(0, int(16000 / 8000 * 5)):  # 5 seconds
        data = q.get()
        if recognizer.AcceptWaveform(data):
            print(json.loads(recognizer.Result())["text"])
        else:
            print(json.loads(recognizer.PartialResult())["partial"])
    print(json.loads(recognizer.FinalResult())["text"])