# Project Proposal: RiftBuddy

## The AI-Powered "Duo Partner" for League of Legends

**Lead Developer:** Seoungmin Kim  
**Status:** In-Development  
**Target Platform:** Cross-Platform (Windows/macOS)

---

## 1. Executive Summary

RiftBuddy is an innovative, real-time AI companion designed to solve the "loneliness" and "macro-blindness" of the solo-queue experience in League of Legends. Unlike traditional stat-trackers that offer static data, RiftBuddy acts as a living "Duo Partner" that interacts via low-latency voice. By fusing official Riot Games API data with real-time Computer Vision (YOLOv8), RiftBuddy provides contextual advice on wave management, jungle pathing, and strategic decision-making while remaining 100% compliant with Riot’s developer policies.

## 2. Core Objectives

- **Companionship:** Transform solo gameplay into a cooperative experience through a natural voice interface ("Hey Buddy").
- **Macro Mastery:** Bridge the gap between mechanical skill and strategic decision-making.
- **Contextual Awareness:** Use hybrid data (API + Vision) to understand game states that APIs alone cannot capture (e.g., minion wave freezes).
- **Accessibility:** Provide a hands-free coaching experience that doesn't require tabbing out or distracting the player during intense combat.

## 3. Technical Architecture

RiftBuddy utilizes a modular architecture optimized for both performance and safety.

### A. The "Eyes" (Vision & API Hybrid)

- **Riot Live Client API:** Polls `localhost:2999` for precise gold, itemization, and health stats.
- **YOLOv8 Vision Suite:** Processes screen captures to detect minion positioning, enemy movement on the minimap, and objective status.
- **Compliance Filter:** Ensures the AI only processes information visible on the player's screen to avoid "information gap" violations.

### B. The "Brain" (Logic & LLM)

- **Context Engine:** Aggregates vision and API data into a compact state representation.
- **Logic Layer:** Evaluates current game state against historical win-rate data and patch-specific meta trends.
- **LLM Integration:** Uses high-speed inference (Gemini 1.5 Flash / local LLM) to generate conversational, personality-driven advice.

### C. The "Voice" (Interaction)

- **STT (Speech-to-Text):** Deepgram or Whisper for real-time "Hey Buddy" wake-word and query processing.
- **TTS (Text-to-Speech):** ElevenLabs for a natural, high-fidelity companion voice that doesn't sound robotic.

## 4. Key Features

1. **Dynamic Draft Consultant:** Real-time pick/counter-pick suggestions based on team synergy and current win rates.
2. **"Hey Buddy" Voice Queries:** Hands-free interaction (e.g., "Hey Buddy, should I push this or freeze?").
3. **Live Macro Overlays:** Integrated Electron-based UI showing jungle timers and gold leads.
4. **Automated Loadouts:** LCU-driven rune and item set configuration based on chosen strategy.
5. **Post-Game Evolution:** Breakdown of performance decay points and actionable improvement goals.

## 5. Market Landscape & Competitive Analysis

RiftBuddy competes in the growing "AI Coaching" space, differentiating itself through **real-time voice interaction** and **computer vision context**.

| Service      | Focus                      | RiftBuddy Advantage                                             |
| :----------- | :------------------------- | :-------------------------------------------------------------- |
| **iTero**    | Macro Database & Drafting  | Real-time voice interaction and in-game visual awareness.       |
| **OP.GG**    | Statistics & Match History | Live coaching and situational decision support.                 |
| **DeepLoL**  | AI Performance Analysis    | Contextual "Duo Partner" persona vs. cold statistical analysis. |
| **Blitz.gg** | Automation & Overlays      | Voice-driven interaction that reduces UI clutter.               |

## 6. Project Roadmap

- **Milestone 1:** Establish Hybrid Data Pipeline (Riot API + YOLOv8).
- **Milestone 2:** Integrate "Hey Buddy" Voice-to-Logic loop.
- **Milestone 3:** Develop Electron.js overlay for cross-platform transparency.
- **Milestone 4:** Riot Developer Portal audit and production API key approval.

## 7. References & Competitors

- **Official Documentation:**
  - [Riot Games Developer Portal](https://developer.riotgames.com/docs/lol)
  - [Riot Developer Policy](https://www.riotgames.com/en/devtools/policies-and-rules)
- **Market Benchmarks:**
  - [iTero.gg - Advanced AI Drafting](https://www.itero.gg/)
  - [OP.GG - Global Stat Leader](https://op.gg/ko)
  - [DeepLoL - AI Performance Analysis](https://www.deeplol.gg/)
  - [Mobalytics - Visual Overlays](https://mobalytics.gg/)

---

_Generated for RiftBuddy Project CLI Tool_
