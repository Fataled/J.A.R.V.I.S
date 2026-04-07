# BMO
> Your helpful lil game console

A voice-activated AI assistant inspired by Tony Stark's JARVIS — featuring real-time voice interaction, full PC control, Spotify integration, and a WebSocket architecture that lets the brain run on a server while the client runs on any device.

---

## Features

- 🎙️ **Wake Word Detection** — Passive listening for "Hey BMO" via OpenWakeWord (custom model)
- 🗣️ **Accurate Transcription** — Commands transcribed via Whisper after wake word detection
- 🖥️ **System Control** — Open/close applications, volume control, system stats — executed on the client device
- 🎵 **Spotify Control** — Play, pause, resume, and search tracks by name and artist
- 🌐 **Web Access** — DuckDuckGo search and browser tab opening on the client device
- 🔊 **TTS via Piper** — Fast, offline voice synthesis
- 🧠 **Local LLM Brain** — Powered by Ollama; defaults to `qwen2.5:7b-instruct`, swap to any model you like
- 💬 **Conversation Mode** — Sustained dialogue after wake word with silence-based timeout
- 📄 **Active File Reading** — Read the currently open file in your IDE via `/tmp/bmo_active_file`
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
│  BMO.py — core brain            │◄──────►│  bmo_client.py                   │
│  • OpenWakeWord wake detection  │  WS    │  • Mic capture (PyAudio)         │
│  • Whisper transcription        │        │  • Audio resampling (48k→16k)    │
│  • Ollama LLM tool use          │        │  • TTS playback                  │
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

| Category    | Examples                                                                                   | Runs On                       |
|-------------|--------------------------------------------------------------------------------------------|-------------------------------|
| Server-side | So far nothing needed on server explicitly.                                                | Server (direct function call) |
| Client-side | open_app, volume, system stats, browser, git, analyzing captured photos,  Spotify, Weather | Client (RPC over WebSocket)   |

BMO receives schemas for all tools. When a client-side tool is called, the server sends a `tool_call` JSON frame to the client, the client executes it locally and returns a `tool_result` frame, and the server continues the tool loop with the result.

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

| Component       | Technology                                        |
|-----------------|---------------------------------------------------|
| LLM             | Ollama (`qwen2.5:7b-instruct` default, swappable) |
| Wake Word       | OpenWakeWord (custom "Hey BMO" model)             |
| Transcription   | Whisper (`base`)                                  |
| TTS             | Piper                                             |
| Music           | Spotipy (Spotify Web API)                         |
| Web Search      | DDGS (DuckDuckGo)                                 |
| Audio I/O       | PyAudio                                           |
| Server          | FastAPI + Uvicorn + WebSockets                    |
| Audio Resample  | SciPy                                             |

---

## Project Structure

```
BMO/
├── client/
│   ├── bmo_git.py               # Git tools — status, commit, push
│   ├── bmo_system.py            # System tools — apps, volume, stats, recording
│   ├── bmo_vision.py            # Screen capture and image analysis
│   ├── bmo_web_access.py        # DuckDuckGo search and browser control
│   ├── main.py                  # Client entry — mic capture, TTS playback, local tool execution
│   ├── requirements.txt
│   └── .env
├── server/
│   ├── models/                  # OpenWakeWord model directory
│   ├── BMO.py                   # Core brain — wake word, transcription, Ollama tool loop
│   ├── bmo_spotify.py           # Spotify playback and search tools
│   ├── bmo_voice.py             # Piper TTS
│   ├── bmo_weather.py           # Weather API
│   ├── memory.json              # Persistent conversation history
│   ├── voice_recognition.py     # Wake word and STT pipeline
│   ├── websocket.py             # FastAPI WebSocket server — audio streaming, RPC dispatch
│   ├── requirements.txt
│   └── .env
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
- Ollama installed and running (`ollama serve`)
- Spotify Premium (required for playback control)
- Server and client can be the same machine or different devices on the same network

### Installation

```bash
git clone https://github.com/Fataled/BMO.git
cd BMO
python3.12 -m venv .venv
source .venv/bin/activate
# cd into client and server and run in both
pip install -r requirements.txt
```

### Ollama Model

BMO defaults to `qwen2.5:7b-instruct` but works with any model Ollama supports:

```bash
ollama pull qwen2.5:7b-instruct
```

To swap models, update `MODEL` in `BMO.py`:

```python
MODEL = "qwen2.5:7b-instruct"  # or llama3.3, mistral, deepseek-r1, etc.
```

### Environment Variables

Create a `.env` file in the project root:

```
SPOTIFY_ID=your_spotify_client_id
SPOTIFY_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
OPENWEATHER_API_KEY=your_weather_api_key
```

---

## Usage

### Start Ollama

```bash
ollama serve
```

### Start the server

```bash
source .venv/bin/activate
python ws-server.py
```

### Start the client (same machine or any device on the network)

```bash
# If running on a different machine, update WS_URL in bmo_client.py
# WS_URL = "ws://<server-ip>:8000/bmo/ws"
python bmo_client.py
```

Say **"Hey BMO"** to activate. BMO enters conversation mode and listens until silence is detected. Say a farewell phrase to dismiss early.

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
- *"That's all, BMO"*

---

## Roadmap

- [ ] Speaker verification — respond only to enrolled voice
- [ ] Twilio integration for SMS and calls
- [X] Camera/vision support
- [ ] Shazam integration
- [ ] Run tests and report results
- [ ] Spotify AI playlist generation (pending Spotify API support)
- [ ] Add a proactive mode where BMO speaks unprompted to give updates
- [ ] Swap Piper for Voxtral TTS (self-hosted, open-weight, matches ElevenLabs v3 quality)

---

## Long-Term Vision: Fine-Tuning

BMO's tool-calling logic is entirely prompt-driven — the LLM receives tool schemas, picks the right one, and the WebSocket layer dispatches it. Because the orchestration layer is model-agnostic, swapping models requires only changing a single config value.

The planned progression:

**1. Quantization** — Experiment with GGUF, AWQ, and GPTQ formats to understand the quality/performance tradeoffs at different bit depths.

**2. Fine-tuning with LoRA/QLoRA** — Train on BMO-specific tool usage patterns. Every conversation and tool selection the system makes is implicitly a training sample — over time this becomes a dataset for teaching a model to be better at *these specific tools and command patterns*. LoRA makes the weight modifications transparent and inspectable, which is the core learning goal.

The end goal is full local ownership of the stack: wake word → STT → LLM → tool execution → TTS, with no external API dependencies and the ability to inspect and modify every layer.

---

## Notes

- Mic capture runs at 48kHz (native USB mic rate) and is resampled to 16kHz before being sent to the server
- TTS audio is delivered in 32KB chunks over the WebSocket and reassembled on the client before playback
- Client-side tools execute locally on the client machine via a lightweight RPC protocol — the server never needs direct access to the client filesystem or hardware
- The screen recorder rotates every 5 minutes to prevent unbounded file growth; clips always capture the last 30 seconds
- Spotify Premium is required for playback control via the Spotify Web API
