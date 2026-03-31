# J.A.R.V.I.S
> Just A Rather Very Intelligent System

A voice-activated AI assistant inspired by Tony Stark's JARVIS — featuring real-time voice interaction, speaker verification, full PC control, and Spotify integration via the Claude and ElevenLabs APIs.

---

## Features

- 🎙️ **Wake Word Detection** — Passive listening for "Hey Jarvis" via OpenWakeWord
- 🔒 **Speaker Verification** — Responds only to your voice using Resemblyzer cosine similarity
- 🖥️ **System Control** — Open/close applications and control system volume (set, adjust, mute)
- 🎵 **Spotify Control** — Play, pause, resume, and search tracks by name and artist
- 🌐 **Web Access** — DuckDuckGo search and browser tab opening
- 🔊 **Dual TTS** — ElevenLabs as primary voice; Kokoro (offline) as fallback when quota is exceeded
- 🧠 **Claude Haiku Brain** — Fast, intelligent responses with native tool use via the Anthropic API
- 💬 **Conversation Mode** — Sustained dialogue after wake word with automatic 10-second timeout
- 📄 **Active File Reading** — Read the currently open file in your IDE via `/tmp/jarvis_active_file`
-    **Git usage** — Take the current repo and either git status, commit, or push
-    **JARVIS CLIP THAT** — Jarvis can clip the last 30 sec of the currently active monitor
---

## Tech Stack

| Component            | Technology                                 |
|----------------------|--------------------------------------------|
| LLM                  | Claude Haiku (`claude-haiku-4-5-20251001`) |
| Speech-to-Text       | Faster Whisper (`small.en`, CPU, int8)     |
| Wake Word            | OpenWakeWord (`hey_jarvis_v0.1.onnx`)      |
| Speaker Verification | Resemblyzer                                |
| TTS (Primary)        | ElevenLabs (`eleven_v3`)                   |
| TTS (Fallback)       | Kokoro (`hexgrad/Kokoro-82M`)              |
| Music                | Spotipy (Spotify Web API)                  |
| Web Search           | DDGS (DuckDuckGo)                          |
| Audio I/O            | PyAudio                                    |

---

## Project Structure

```
J.A.R.V.I.S/
├── main.py                  # Entry point
├── Jarvis.py                # Core loop — wake word, voice verification, conversation mode, tool dispatch
├── jarvis_spotify.py        # Spotify playback and search tools
├── jarvis_voice.py          # ElevenLabs TTS with Kokoro fallback
├── jarvis_system.py         # System tools — open/close apps, volume control
├── jarvis_web_access.py     # DuckDuckGo search and browser control
├── jarvis_wakeword.py       # Wake word model download utility
├── voice_recognition.py     # Resemblyzer speaker verification
├── models/                  # OpenWakeWord .onnx model files
├── audio recordings/        # Voice enrollment WAV samples
├── .env                     # API keys (not committed)
├── my_voice.npy             # Speaker embedding (not committed)
├── jarvis_git.py            # Git access specifically for this repo
├── 
└── 
```

---

## Setup

### Prerequisites

- Python 3.12
- Linux or Windows
- Spotify Premium (required for playback control)

### Installation

```bash
git clone https://github.com/Fataled/jarvis.git
cd jarvis
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
SPOTIFY_ID=your_spotify_client_id
SPOTIFY_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
HF_TOKEN=your_huggingface_token
OPENWEATHER_API_KEY=your_weather_api_key
```

### Wake Word Models

Download the required OpenWakeWord ONNX models into the `models/` directory:

```bash
mkdir -p models
wget -P models https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/hey_jarvis_v0.1.onnx
wget -P models https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx
wget -P models https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx
```

### Voice Enrollment

Record 5–10 short WAV clips of your voice and place them in the `audio recordings/` folder. On first run, `VoiceRecognition` will automatically generate `my_voice.npy` from those samples.
Preferably of you saying the wake work throughout the day and in different environments.
---

## Usage

```bash
source .venv/bin/activate
python main.py
```

Say **"Hey Jarvis"** to activate. Jarvis verifies your voice and enters conversation mode. Conversation times out after **10 seconds** of inactivity. Say a farewell phrase to dismiss early.

### Example Commands

- *"Play Blinding Lights by The Weeknd"*
- *"Pause the music"*
- *"Turn the volume up a bit"*
- *"Set the volume to 50"*
- *"Open Firefox"*
- *"Search for the latest news on AI"*
- *"Read my active file"*
- *"That's all, Jarvis"*
- *"Commit all files with the message auth bug fixed*

---

## Roadmap

- [ ] Arduino/WebSocket support for hardware integration
- [ ] Twilio integration for SMS and calls
- [ ] Weather API
- [ ] Multi-device WebSocket server — run Jarvis brain on a server, connect from any device
- [ ] Camera/vision via Claude's vision API
- [ ] Run tests and report results
- [ ] Analysis of images in real time
- [ ] Using shazam with a command
- [ ] Hopefully once spotify releases a.i. made playlists the ability to make those
---

## Notes

- Spotify Premium is required for playback control via the Spotify Web API
- ElevenLabs free tier (~10k characters/month) is sufficient for light personal use; Kokoro handles the fallback silently
- ALSA warnings on WSL2 are cosmetic and do not affect functionality
- Speaker verification threshold is set to `0.60` cosine similarity — adjust in `Jarvis.py` if needed