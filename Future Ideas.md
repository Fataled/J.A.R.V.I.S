# Project BMO — Future Plans

A living document of the roadmap, hardware builds, and architectural vision for the full Project BMO ecosystem.

---

## The Vision

A fully personal, self-hosted AI assistant ecosystem inspired by J.A.R.V.I.S. — spanning a wearable AR interface, a physical companion device (BMO), and a centralized AI brain. Thin clients everywhere, intelligence in one place.

---

## BMO — AI Brain

The core intelligence layer that all devices talk to. Currently running fully local via Ollama (`qwen2.5:7b-instruct` default, swappable). Long-term goal is a fine-tuned, fully self-hosted stack with no external dependencies.

### LLM
- Currently: Ollama with `qwen2.5:7b-instruct` as default — swap to any supported model via a single config value
- Evaluate larger models (Llama 3.3, Mistral, DeepSeek-R1) as VRAM budget allows
- Fine-tune with LoRA/QLoRA on BMO-specific tool usage patterns — every conversation is implicitly a training sample
- VRAM constraint: balance LLM size against TTS coexistence on GPU

### TTS — Piper → Voxtral
- Currently: **Piper** (fast, offline, lightweight)
- Target upgrade: self-hosted **Voxtral-4B-TTS** via vLLM-Omni
  - OpenAI-compatible `/v1/audio/speech` endpoint — near drop-in replacement
  - Voice cloning via reference WAV for a true personalized feel
  - 24kHz output, streaming support for low time-to-first-audio
  - Fully offline, no API cost

### STT
- Whisper for high-accuracy transcription (current)
- Benchmark for conversational latency on local hardware

### Wake Word
- Currently: **OpenWakeWord** with a custom "Hey BMO" model
- Local, offline, always listening without streaming constantly

### Full Local Stack Architecture
```
Mic input → OpenWakeWord (wake) → Whisper (STT) → Ollama LLM → Piper/Voxtral (TTS) → Speaker output
```
All on one machine, no external API calls.

---

## Hosting & Infrastructure

### The Problem
Pi (BMO device) and AR glasses are thin clients — they can't run the stack. The brain needs to be reachable from anywhere.

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
- True redundancy — BMO never goes down

### Multi-device Orchestration
- WebSocket-based orchestration layer (self-hosted or AWS EC2)
- All devices (glasses, BMO device, desktop, phone) connect as clients
- Brain handles routing: commands go to PC, queries get answered, data gets relayed

---

## BMO Device — Physical Companion

A handheld/portable physical device modeled after BMO from Adventure Time. Serves as a portable terminal for when you're away from your desk.

### Hardware Plan
- **Compute**: Raspberry Pi (exact model TBD based on display needs)
- **Display**: Small screen on the "face" for expressions, status, text output
- **Mic**: MEMS mic array for noise rejection
- **Speaker**: Small driver for TTS audio output
- **Connectivity**: WiFi + cellular tethering to reach BMO brain via Tailscale
- **Power**: LiPo battery, USB-C charging

### Software
- Thin client only — streams mic to brain, receives audio back
- Local wake word detection via OpenWakeWord so it's always listening without streaming constantly
- BMO face expressions driven by response state (thinking, speaking, idle)

---

## AR Glasses — Wearable Interface

DIY AR glasses built around existing prescription lenses. The most ambitious hardware build in the ecosystem.

### Frame & Optics
- Use prescription lenses from optometrist
- Frames: spare set from doctor, or **3D print at school** (full control over internal routing)
- Display: tiny OLED/micro FPV screen + angled half-mirror beam splitter combiner for monocular AR overlay
- Monocular HUD — text, status, notifications. No need for full FOV

### Compute (On-Face)
- **Pi Zero 2W** or **ESP32-S3** — just enough for mic capture + Bluetooth/WiFi relay
- No local inference — everything streams to BMO brain
- 3D printed temples with internal cavities for:
  - Compute board
  - LiPo cell
  - MEMS mic
  - Antenna

### Connectivity Architecture
- **Option A**: Glasses → Phone (Bluetooth) → Phone relays to BMO brain
  - Phone is connectivity layer, glasses stay dumb and light
  - Works anywhere phone has signal
- **Option B**: Glasses → direct WiFi when on known networks
- Hybrid: auto-switch between both

### Interaction Model
- Mic always listening for wake word (local, on-device via OpenWakeWord)
- Voice commands relay to BMO brain
- Responses play via bone conduction or small in-ear speaker
- AR overlay shows text output, notifications, PC command confirmations

### PC Control
- BMO receives voice command via glasses
- Routes to PC agent
- Executes: open apps, query data, control media, system commands
- Confirmation shown in AR overlay

---

## Fabrication & Tinkering

- **3D Printing**: School printers for frames, BMO enclosure, component mounts
- **PCB Design**: Future goal — custom PCB for glasses compute/power board to replace off-the-shelf modules
- **Bone conduction mic**: Evaluate for glasses — better noise rejection in loud environments than MEMS

---

## Rough Priority Order

1. ✅ BMO core (done — fully local, Ollama + OpenWakeWord + Piper)
2. 🔧 Self-hosted TTS upgrade — Voxtral spinup + latency validation
3. 🔧 Fine-tuning — LoRA on BMO tool usage patterns
4. 📋 Hosting decision — home server spec or cloud setup
5. 📋 BMO physical device build
6. 📋 AR glasses — frame design + optics prototype
7. 📋 Full thin-client orchestration layer
8. 📋 PCB design for glasses compute board
