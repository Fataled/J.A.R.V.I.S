# J.A.R.V.I.S
> Just A Rather Very Intelligent System

A voice-activated AI assistant inspired by Tony Stark's JARVIS — featuring real-time voice interaction, speaker verification, full PC control, and deep integration with productivity and lifestyle services via the Claude API.

---

## Features

- 🎙️ **Wake Word Detection** — Passive listening for "Hey Jarvis" via OpenWakeWord
- 🔒 **Voice Recognition** — Speaker verification using Resemblyzer; only responds to your voice
- 🖥️ **Full PC Control** — Launch applications, manage files, and automate system tasks
- 📅 **Calendar Integration** — Create, read, and manage calendar events via natural language
- 📧 **Email Integration** — Read, compose, and send emails hands-free
- 🎵 **Spotify Control** — Play, pause, resume, and search tracks by name and artist
- 🌐 **Web Search** — Real-time search via DuckDuckGo
- 🔊 **ElevenLabs TTS** — Natural voice responses with a custom British butler persona
- 🧠 **Claude Haiku Brain** — Fast, intelligent responses with native tool use via the Anthropic API
- 💬 **Conversation Mode** — Sustained dialogue after wake word with automatic timeout

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Claude Haiku (Anthropic API) |
| Speech Recognition | Whisper (whisper-mic) |
| Wake Word | OpenWakeWord (`hey_jarvis`) |
| Voice Verification | Resemblyzer |
| Text to Speech | ElevenLabs |
| Music | Spotipy (Spotify API) |
| Web Search | DuckDuckGo Search |
| Audio I/O | PyAudio |

---

## Project Structure

```
Jarvis/
├── main.py                  # Core loop — wake word, voice verification, conversation mode
├── jarvis_spotify.py        # Spotify wrapper and tool definitions
├── jarvis_voice.py          # ElevenLabs TTS
├── jarvis_recognition.py    # Resemblyzer speaker verification
├── jarvis_system.py         # PC control and system automation
├── jarvis_calendar.py       # Calendar integration
├── jarvis_email.py          # Email integration
├── .env                     # API keys (not committed)
└── my_voice.npy             # Voice embedding (not committed)
```

---

## Setup

### Prerequisites

- Python 3.12
- WSL2 (Ubuntu 20.04) or Linux
- Spotify Premium (required for playback control)

### Installation

```bash
git clone https://github.com/Fataled/jarvis.git
cd jarvis
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```
ANTHROPIC_API_KEY=your_key
SPOTIFY_ID=your_spotify_client_id
SPOTIFY_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
ELEVENLABS_API_KEY=your_key
HF_TOKEN=your_huggingface_token
```

### Voice Enrollment

Record 5-10 short clips of your voice and place them in a folder, then run the enrollment script to generate your voice embedding:

```bash
python enroll.py --samples ./my_samples
```

This generates `my_voice.npy` which is used for speaker verification on every interaction.

### Wake Word Models

Download the required OpenWakeWord models into your project directory:

```bash
wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/hey_jarvis_v0.1.onnx
wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx
wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx
```

---

## Usage

```bash
source venv/bin/activate
python main.py
```

Say **"Hey Jarvis"** to activate. Jarvis will verify your voice and enter conversation mode. Say *"that's all"* or *"goodbye"* to dismiss and return to passive listening.

### Example Commands

- *"Play Blinding Lights by The Weeknd"*
- *"What's on my calendar tomorrow?"*
- *"Send an email to John saying the meeting is at 3pm"*
- *"Open Rider"*
- *"Search for the latest news on AI"*

---

## Roadmap

- [ ] Twilio integration for SMS and calls
- [ ] Google Contacts lookup
- [ ] Weather API
- [ ] Multi-device WebSocket server — run Jarvis brain on a server, connect from any device
- [ ] Camera/vision via Claude's vision API

---

## Notes

- Spotify Premium is required for playback control via the Spotify API
- ElevenLabs free tier (~10k credits/month) is sufficient for personal use
- ALSA warnings on WSL2 are cosmetic and do not affect functionality
