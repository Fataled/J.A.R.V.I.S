# Project Ironman — Future Plans

A living document of the roadmap, hardware builds, and architectural vision for the full Project Ironman ecosystem.

---

## The Vision

A fully personal, self-hosted AI assistant ecosystem inspired by J.A.R.V.I.S. — spanning a wearable AR interface, a physical companion device (BMO), and a centralized AI brain. Thin clients everywhere, intelligence in one place.

---

## J.A.R.V.I.S. — AI Brain

The core intelligence layer that all devices talk to. Currently running on local hardware with Anthropic's API. Long-term goal is a fully self-hosted, offline-capable stack.

### TTS — Voxtral
- Replace ElevenLabs + Kokoro fallback with self-hosted **Voxtral-4B-TTS-2603** via vLLM-Omni
- OpenAI-compatible `/v1/audio/speech` endpoint — near drop-in replacement
- Voice cloning via reference WAV — use a personal voice recording for true J.A.R.V.I.S. feel
- 24kHz output, streaming support for low time-to-first-audio
- Fully offline, no API cost, CC BY-NC license (personal use fine)

### STT — Whisper + Vosk
- Whisper for high-accuracy transcription
- Vosk for low-latency streaming / wake word detection
- Benchmark both for conversational latency on local hardware

### LLM
- Evaluate self-hosted models (Llama, Mistral, Qwen) via Ollama or vLLM
- Goal: full offline capability as fallback when Anthropic API is unavailable
- VRAM constraint: balance LLM size against Voxtral TTS coexistence on GPU

### Full Local Stack Architecture
```
Mic input → Vosk (wake) → Whisper (STT) → LLM → Voxtral (TTS) → Speaker output
```
All on one machine, no external API calls.

---

## Hosting & Infrastructure

### The Problem
Pi (BMO) and AR glasses are thin clients — they can't run the stack. The brain needs to be reachable from anywhere.

### Option A — Home Server + Tailscale (Primary Plan)
- Run full stack on a dedicated home machine (target: GPU with 24GB+ VRAM, e.g. RTX 3090)
- Expose privately via **Tailscale** or WireGuard — Pi and glasses connect transparently over cellular/WiFi
- Zero cloud cost, full control, low latency on LAN
- Weakness: home internet upload speed, single point of failure

### Option B — Cloud GPU (Fallback / Testing)
- RunPod or Vast.ai spot instances for testing the full stack affordably
- A tiny always-on relay (AWS Lightsail ~$5/mo) handles wake signal + proxies until GPU instance is up
- Sleep/wake on demand to control cost

### Option C — Hybrid (Long-term)
- Home server as primary brain
- Cloud GPU as fallback if home is unreachable
- Pi detects connectivity and reroutes automatically
- True redundancy — J.A.R.V.I.S. never goes down

### Multi-device Orchestration
- WebSocket-based orchestration layer (AWS EC2 or self-hosted)
- All devices (glasses, BMO, desktop, phone) connect as clients
- Brain handles routing: commands go to PC, queries get answered, data gets relayed

---

## BMO — Physical Companion Device

A handheld/portable physical device modeled after BMO from Adventure Time. Serves as a portable J.A.R.V.I.S. terminal for when you're away from your desk.

### Hardware Plan
- **Compute**: Raspberry Pi (exact model TBD based on display needs)
- **Display**: Small screen on the "face" for expressions, status, text output
- **Mic**: MEMS mic array for noise rejection
- **Speaker**: Small driver for TTS audio output
- **Connectivity**: WiFi + cellular tethering to reach J.A.R.V.I.S. brain via Tailscale
- **Power**: LiPo battery, USB-C charging

### Software
- Thin client only — streams mic to brain, receives audio back
- Local wake word detection (Vosk/OpenWakeWord) so it's always listening without streaming constantly
- BMO face expressions driven by J.A.R.V.I.S. response state (thinking, speaking, idle)

---

## AR Glasses — Wearable Interface

DIY AR glasses built around existing prescription lenses. The most ambitious hardware build in the ecosystem.

### Frame & Optics
- Use prescription lenses from optometrist (already have correct vision)
- Frames: get spare set from doctor, or **3D print at school** (good practice, full control over internal routing)
- Display: tiny OLED/micro FPV screen + angled half-mirror beam splitter combiner for monocular AR overlay
- Monocular HUD — text, status, notifications. No need for full FOV

### Compute (On-Face)
- **Pi Zero 2W** or **ESP32-S3** — just enough for mic capture + Bluetooth/WiFi relay
- No local inference — everything streams to J.A.R.V.I.S. brain
- 3D printed temples with internal cavities for:
  - Compute board
  - LiPo cell
  - MEMS mic
  - Antenna

### Connectivity Architecture
- **Option A**: Glasses → Phone (Bluetooth) → Phone relays to J.A.R.V.I.S. brain
  - Phone is connectivity layer, glasses stay dumb and light
  - Works anywhere phone has signal
- **Option B**: Glasses → direct WiFi when on known networks
- Hybrid: auto-switch between both

### Interaction Model
- Mic always listening for wake word (local, on-device)
- Voice commands relay to J.A.R.V.I.S.
- Responses play via bone conduction or small in-ear speaker
- AR overlay shows text output, notifications, PC command confirmations

### PC Control
- J.A.R.V.I.S. receives voice command via glasses
- Routes to PC agent (existing IntelliJ plugin architecture, extended)
- Executes: open apps, query data, control media, system commands
- Confirmation shown in AR overlay

---

## Fabrication & Tinkering

- **3D Printing**: School printers for frames, BMO enclosure, component mounts
- **PCB Design**: Future goal — custom PCB for glasses compute/power board to replace off-the-shelf modules
- **Bone conduction mic**: Evaluate for glasses — better noise rejection in loud environments than MEMS

---

## Rough Priority Order

1. ✅ J.A.R.V.I.S. core (mostly done)
2. 🔧 Self-hosted TTS — Voxtral spinup + latency validation
3. 🔧 Self-hosted LLM — evaluate viable models within VRAM budget
4. 📋 Hosting decision — home server spec or cloud setup
5. 📋 BMO hardware build
6. 📋 AR glasses — frame design + optics prototype
7. 📋 Full thin-client orchestration layer
8. 📋 PCB design for glasses compute board