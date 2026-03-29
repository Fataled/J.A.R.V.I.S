from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import os
from elevenlabs.play import play


load_dotenv()

class JarvisVoice:
    def __init__(self):
        self.elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    def speak(self, text):
        response = self.elevenlabs.text_to_speech.convert(
            voice_id="5vpmAScR72nJ1oEJtE8f",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_v3"
        )

        play(response)
