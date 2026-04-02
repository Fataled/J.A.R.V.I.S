# J.A.R.V.I.S
> Just A Rather Very Intelligent System

A voice-activated AI assistant inspired by Tony Stark's JARVIS — featuring real-time voice interaction, full PC control, Spotify integration, and a WebSocket architecture that lets the brain run on a server while the client runs on any device.

---

## Features

- 🎙️ **Wake Word Detection** — Passive listening for "Hey Jarvis" via Vosk (lightweight, offline)
- 🗣️ **Accurate Transcription** — Commands transcribed via Whisper after wake word detection
- 🖥️ **System Control** — Open/close applications, volume control, system stats — executed on the client device
- 🎵 **Spotify Control** — Play, pause, resume, and search tracks by name and artist
- 🌐 **Web Access** — DuckDuckGo search and browser tab opening on the client device
- 🔊 **TTS via Kokoro** — Offline voice synthesis using Kokoro (`bm_george` voice)
- 🧠 **Claude Haiku Brain** — Fast, intelligent responses with native tool use via the Anthropic API
- 💬 **Conversation Mode** — Sustained dialogue after wake word with silence-based timeout
- 📄 **Active File Reading** — Read the currently open file in your IDE via `/tmp/jarvis_active_file`
- 💾 **Git Integration** — Git status, commit, and push from voice
- 🔴 **Clip That** — Clip the last 30 seconds of your active monitor on command
- 🌤️ **Weather** — Real-time weather data via OpenWeather API
- 🔌 **WebSocket Architecture** — Brain runs on a server; any device can connect as a client over the network

---

## Architecture

```
┌─────────────────────────────────┐        ┌──────────────────────────────────┐
│          SERVER                 │        │           CLIENT                 │
│                                 │        │                                  │
│  Jarvis.py — core brain         │◄──────►│  jarvis_client.py                │
│  • Vosk wake word detection     │  WS    │  • Mic capture (PyAudio)         │
│  • Whisper transcription        │        │  • Audio resampling (48k→16k)    │
│  • Claude Haiku tool use        │        │  • TTS playback                  │
│  • Spotify / Git / Weather      │        │  • System tool execution         │
│                                 │        │  • Browser control               │
│  websocket.py — FastAPI WS      │        │  • Volume / app control          │
│  • Audio streaming              │        │                                  │
│  • RPC tool dispatch            │        │                                  │
│  • TTS chunked delivery         │        │                                  │
└─────────────────────────────────┘        └──────────────────────────────────┘
```

### Tool Execution Model

Tools are split into two categories:

| Category | Examples                                                                | Runs On |
|----------|-------------------------------------------------------------------------|---------|
| Server-side | Spotify, Weather                                                        | Server (direct function call) |
| Client-side | open_app, volume, system stats, browser, git, analyzing captured photos | Client (RPC over WebSocket) |

Claude receives schemas for all tools. When a client-side tool is called, the server sends a `tool_call` JSON frame to the client, the client executes it locally and returns a `tool_result` frame, and the server continues the Claude tool loop with the result.

### WebSocket Message Protocol

```
Audio:       binary frames (raw PCM int16, 16kHz mono)
TTS chunk:   {"type": "tts",         "data": "<base64 PCM>"}
TTS end:     {"type": "tts_end"}
Tool call:   {"type": "tool_call",   "id": "abc123", "name": "open_app", "inputs": {...}}
Tool result: {"type": "tool_result", "id": "abc123", "result": "..."}
```

---

## Tech Stack

| Component       | Technology                                  |
|-----------------|---------------------------------------------|
| LLM             | Claude Haiku (`claude-haiku-4-5-20251001`)  |
| Wake Word       | Vosk (`vosk-model-small-en-us-0.15`)        |
| Transcription   | Whisper (`base`)                            |
| TTS             | Kokoro (`bm_george`)                        |
| Music           | Spotipy (Spotify Web API)                   |
| Web Search      | DDGS (DuckDuckGo)                           |
| Audio I/O       | PyAudio                                     |
| Server          | FastAPI + Uvicorn + WebSockets              |
| Audio Resample  | SciPy                                       |

---

## Project Structure

```
J.A.R.V.I.S/
├── client/
│   ├── jarvis_git.py            # Git tools — status, commit, push
│   ├── jarvis_system.py         # System tools — apps, volume, stats, recording
│   ├── jarvis_vision.py         # Screen capture and image analysis
│   ├── jarvis_web_access.py     # DuckDuckGo search and browser control
│   ├── main.py                  # Client entry — mic capture, TTS playback, local tool execution
│   ├── requirements.txt
│   └── .env
├── server/
│   ├── models/                  # Vosk model directory
│   ├── Jarvis.py                # Core brain — wake word, transcription, Claude tool loop
│   ├── jarvis_spotify.py        # Spotify playback and search tools
│   ├── jarvis_voice.py          # Kokoro TTS
│   ├── jarvis_weather.py        # Weather API
│   ├── memory.json              # Persistent conversation history
│   ├── voice_recognition.py     # Wake word and STT pipeline
│   ├── websocket.py             # FastAPI WebSocket server — audio streaming, RPC dispatch
│   ├── requirements.txt
│   └── .env
├── audio recordings/
├── Dockerfile
├── .dockerignore
├── .gitignore
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.12
- Linux (Arch recommended) or Windows
- Spotify Premium (required for playback control)
- Server and client can be the same machine or different devices on the same network

### Installation

```bash
git clone https://github.com/Fataled/J.A.R.V.I.S.git
cd J.A.R.V.I.S
python3.12 -m venv .venv
source .venv/bin/activate
cd into client and sever and run in both
pip install -r requirements.txt
```

### Vosk Model

```bash
mkdir -p models/vosk-small
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip -d models/vosk-small
```

### Environment Variables

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_key
SPOTIFY_ID=your_spotify_client_id
SPOTIFY_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
OPENWEATHER_API_KEY=your_weather_api_key
```

---

## Usage

### Start the server

```bash
source .venv/bin/activate
python websocket.py
```

### Start the client (same machine or any device on the network)

```bash
# If running on a different machine, update WS_URL in jarvis_client.py
# WS_URL = "ws://<server-ip>:8000/jarvis/ws"
python jarvis_client.py
```

Say **"Hey Jarvis"** to activate. Jarvis enters conversation mode and listens until silence is detected. Say a farewell phrase to dismiss early.

### Example Commands

- *"Play Blinding Lights by The Weeknd"*
- *"Pause the music"*
- *"Turn the volume up a bit"*
- *"Set the volume to 50"*
- *"Open Firefox"*
- *"Search for the latest news on AI"*
- *"What's my CPU and GPU doing?"*
- *"Read my active file"*
- *"Commit all files with the message auth bug fixed"*
- *"What's the weather in Toronto?"*
- *"Clip that"*
- *"That's all, Jarvis"*

---

## Roadmap

- [ ] Speaker verification — respond only to enrolled voice
- [ ] Twilio integration for SMS and calls
- [X] Camera/vision via Claude's vision API
- [ ] Shazam integration
- [ ] Run tests and report results
- [ ] Spotify AI playlist generation (pending Spotify API support)
- [ ] Add a proactive mode where he speaks unprompted to give updates

---

## Notes

- Mic capture runs at 48kHz (native USB mic rate) and is resampled to 16kHz before being sent to the server
- TTS audio is delivered in 32KB chunks over the WebSocket and reassembled on the client before playback
- Client-side tools execute locally on the client machine via a lightweight RPC protocol — the server never needs direct access to the client filesystem or hardware
- The screen recorder rotates every 5 minutes to prevent unbounded file growth; clips always capture the last 30 seconds
- Spotify Premium is required for playback control via the Spotify Web API