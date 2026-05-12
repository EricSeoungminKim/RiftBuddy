# Project 1 — RiftBuddy 2.0

## Real-time AI League Coach Platform

### Career Positioning

**Target story:**  
RiftBuddy is a real-time AI coaching system for League of Legends that combines live game telemetry, event detection, champion/matchup knowledge retrieval, and low-latency LLM advice inside an Electron overlay.

**Career signal:**

- AI product engineering
- Real-time backend systems
- LLM application engineering
- Gaming/esports domain passion
- WebSocket + FastAPI + Electron architecture
- Multi-provider LLM integration

---

## 1. Current Project Strengths

The current RiftBuddy repo already has strong foundations:

- Riot Live Client API integration
- FastAPI backend
- WebSocket streaming to frontend
- Electron overlay interface
- LLM provider abstraction
- Anthropic, Groq, Gemini, and mock provider support
- Korean League-specific prompt tuning
- TTS / voice coaching direction
- Backend/frontend/docs/tests separation

The project is already more than a simple AI wrapper. It has the foundation of a real-time decision-support system.

---

## 2. Current Weaknesses to Fix

### 2.1 Game Intelligence Layer Is Thin

Current flow is mostly:

```text
Game state → LLM prompt → Advice
```

Professional version should be:

```text
Game state → Event detection → Knowledge retrieval → Advice planning → LLM → Evaluation
```

### 2.2 Session Memory Needs More Structure

Current session tracking is useful, but it should become a timeline intelligence layer.

Add:

- event timeline
- repeated mistake detection
- objective timer awareness
- gold spike tracking
- recall window detection

### 2.3 README Needs Recruiter-Friendly Packaging

Add:

- demo GIF/video
- architecture diagram
- key technical challenges
- evaluation results
- latency metrics
- clear career-oriented project summary

### 2.4 Testing and Evaluation Need to Become Visible

Add automated evals for:

- advice quality
- latency
- Korean terminology
- game-state grounding
- response length
- dangerous-state handling

---

## 3. Target Architecture

```text
Electron Overlay
    |
    | WebSocket
    v
FastAPI Backend
    |
    +-- Riot Live Client Adapter
    |       - active player
    |       - all players
    |       - events
    |       - items
    |       - gold estimate
    |
    +-- Game State Normalizer
    |       - typed GameState
    |       - position/champion normalization
    |
    +-- Timeline / Event Detector
    |       - death detected
    |       - objective spawn soon
    |       - recall timing
    |       - gold spike
    |       - low HP danger
    |
    +-- Knowledge / RAG Layer
    |       - champion matchup notes
    |       - item spike rules
    |       - lane macro rules
    |
    +-- Advice Planner
    |       - choose prompt template
    |       - rank urgent issues
    |       - generate short action call
    |
    +-- LLM Provider Layer
    |       - Anthropic
    |       - Gemini
    |       - Groq
    |       - mock
    |
    +-- TTS Layer
    |
    v
Advice + Audio + Context Metadata
```

---

## 4. Recommended Folder Structure

```text
backend/
    advice/
        __init__.py
        planner.py
        rules.py
        evaluator.py
        schemas.py

    timeline/
        __init__.py
        event_detector.py
        objective_tracker.py
        session_store.py
        detectors/
            low_health.py
            gold_spike.py
            death_streak.py
            item_completion.py
            recall_window.py

    knowledge/
        __init__.py
        retriever.py
        schemas.py
        data/
            champions/
                rumble.json
                ahri.json
                lee_sin.json
            matchups/
                rumble_vs_tryndamere.json
            macro_rules/
                top_lane.yaml
                jungle_tracking.yaml
                objective_setup.yaml

    llm/
        advisor.py
        providers.py
        prompts.py

    riot/
        live_client.py

    voice/
        tts.py

docs/
    architecture.md
    demo-script.md
    evaluation.md
    roadmap.md

tests/
    unit/
    integration/
    evals/
```

---

## 5. Feature Roadmap

## Phase 1 — Professional Refactor

### Goal

Make the repo look like a real production-style AI product repo.

### Tasks

- [ ] Create `backend/advice/`
- [ ] Create `backend/timeline/`
- [ ] Create `backend/knowledge/`
- [ ] Move prompt-building logic into dedicated prompt module
- [ ] Define typed schemas for:
  - `GameState`
  - `DetectedEvent`
  - `AdviceRequest`
  - `AdviceResponse`
  - `KnowledgeSnippet`
- [ ] Add `docs/architecture.md`
- [ ] Add `docs/demo-script.md`
- [ ] Add `docs/evaluation.md`
- [ ] Add GitHub Actions CI
- [ ] Add test badges to README

### Output

```text
Professional repo structure
Architecture doc
CI pipeline
Cleaner separation of game state, advice, timeline, and knowledge
```

---

## Phase 2 — Event Intelligence Layer

### Goal

Avoid sending raw game state directly to the LLM. Add deterministic game event detection first.

### Event Detectors to Add

- [ ] LowHealthDetector
- [ ] GoldSpikeDetector
- [ ] DeathStreakDetector
- [ ] ObjectiveTimerDetector
- [ ] RecallWindowDetector
- [ ] EnemyJungleUnknownDetector
- [ ] ItemCompletionDetector
- [ ] CSDropDetector
- [ ] VisionWarningDetector

### Example Detected Event

```json
{
  "event_type": "GOLD_SPIKE",
  "severity": "HIGH",
  "reason": "Player has 2750 gold and should recall before next objective",
  "recommended_action": "Push one safe wave and reset"
}
```

### Implementation Notes

Create a common interface:

```python
class BaseDetector:
    def detect(self, current_state: GameState, session: GameSession) -> list[DetectedEvent]:
        raise NotImplementedError
```

Then compose detectors:

```python
class EventDetectorPipeline:
    def __init__(self, detectors: list[BaseDetector]):
        self.detectors = detectors

    def run(self, state: GameState, session: GameSession) -> list[DetectedEvent]:
        events = []
        for detector in self.detectors:
            events.extend(detector.detect(state, session))
        return sorted(events, key=lambda e: e.severity, reverse=True)
```

### Output

```text
Game-state-aware event detection
Prioritized coaching signals
Better LLM prompts
More professional AI system architecture
```

---

## Phase 3 — Champion Knowledge / RAG Layer

### Goal

Make RiftBuddy more than generic LLM advice by adding champion, matchup, and macro knowledge.

### Data Structure

```text
backend/knowledge/data/
    champions/
        rumble.json
        ahri.json
        lee_sin.json
    matchups/
        rumble_vs_tryndamere.json
    macro_rules/
        top_lane.yaml
        jungle_tracking.yaml
        objective_setup.yaml
```

### Example Champion Profile

```json
{
  "champion": "Rumble",
  "role": "TOP",
  "identity": "AP lane bully with strong level 6 objective fight",
  "spikes": ["Level 6", "Liandry completion", "Sorcerer Shoes"],
  "weaknesses": ["No dash", "vulnerable to ganks when pushed"],
  "advice_rules": [
    "Track enemy jungler before overheating for trades",
    "Use Equalizer for objective choke points"
  ]
}
```

### First Implementation

Start simple:

- [ ] Load JSON/YAML files
- [ ] Match by champion name and role
- [ ] Match by lane matchup
- [ ] Return top 3 relevant snippets

### Later Upgrade

- [ ] Add embeddings
- [ ] Add local vector store
- [ ] Add matchup retrieval
- [ ] Add versioned knowledge base

### Output

```text
RAG-style knowledge layer
Champion-aware advice
Better OpenAI/Anthropic applied engineering story
```

---

## Phase 4 — Advice Planner

### Goal

Create an intermediate planning layer before calling the LLM.

### Planner Responsibilities

- [ ] Rank detected events by urgency
- [ ] Select relevant knowledge snippets
- [ ] Choose prompt template
- [ ] Decide response length
- [ ] Decide whether advice should be defensive, aggressive, macro-focused, or recall-focused

### Example Planner Output

```json
{
  "mode": "DEFENSIVE",
  "priority_event": "LOW_HEALTH_DANGER",
  "knowledge_used": ["rumble_top_profile", "enemy_jungle_tracking_rule"],
  "instruction": "Give one short Korean sentence with immediate action only."
}
```

### Output

```text
More controlled LLM behavior
Less generic coaching
Cleaner AI system design
```

---

## Phase 5 — Evaluation System

### Goal

Show that you can evaluate AI output quality, not just generate text.

### Eval Tests

- [ ] Advice is short
- [ ] Advice references actual game state
- [ ] Advice is not generic
- [ ] Korean terminology is correct
- [ ] Low-health state returns defensive advice
- [ ] High-gold state recommends reset
- [ ] Objective-spawn state recommends preparation
- [ ] Response latency is measured

### Example Evaluation Table for README

```text
Evaluation Results
- 42/45 scenario tests passed
- Avg advice latency: 1.8s with mock provider
- Avg advice latency: 2.9s with remote LLM
- Korean terminology validation: 100% pass on core LoL terms
```

### Output

```text
AI eval suite
Portfolio-ready quality metrics
Stronger AI engineering signal
```

---

## Phase 6 — Demo and README Polish

### README Structure

```text
# RiftBuddy — Real-time AI League Coach

[Demo GIF]

## What it does
RiftBuddy watches your live League game, detects urgent events, retrieves champion/matchup knowledge, and gives short voice + overlay advice.

## Why it matters
Most game assistants show static stats. RiftBuddy turns live telemetry into real-time decision support.

## Architecture
[diagram]

## Key Features
- Riot Live Client telemetry
- WebSocket game-state streaming
- Event detection pipeline
- Champion/matchup knowledge retrieval
- Multi-provider LLM advice planner
- Korean/English voice coaching
- Electron overlay
- Evaluation suite

## Technical Challenges
- Low-latency advice generation
- Noisy live game telemetry
- Prompt grounding
- Real-time overlay UX
- Advice quality evaluation

## Evaluation Results
[table]

## Demo
[video link]
```

### Demo Script

1. Start backend
2. Open Electron overlay
3. Simulate or enter a League match
4. Show live game state detection
5. Trigger low-health / gold spike / objective event
6. Show Korean voice advice
7. Show evaluation tests passing

---

## 6. Resume Bullets

### Standard Version

Built a real-time AI League of Legends coaching overlay using FastAPI, WebSockets, Electron, Riot Live Client API, and multi-provider LLM integration; added event detection, champion knowledge retrieval, TTS, and automated advice-quality evaluations.

### Stronger Version

Designed a real-time AI decision-support system for League of Legends that transforms live game telemetry into prioritized coaching events, retrieves champion/matchup knowledge, and streams low-latency LLM + TTS advice through an Electron overlay.

---

## 7. Vibe Coding Checklist

### Start Here

- [ ] Rewrite README title and intro
- [ ] Add architecture diagram placeholder
- [ ] Create `timeline/`, `knowledge/`, `advice/` folders
- [ ] Add typed schemas
- [ ] Implement one detector first: `LowHealthDetector`
- [ ] Add one champion profile: Rumble
- [ ] Connect detector output to prompt
- [ ] Add one eval test
- [ ] Record short demo GIF

### Best First Feature

Implement `LowHealthDetector` because it is easy to test and visually obvious in a demo.

### Best Second Feature

Implement `GoldSpikeDetector` because it shows real game knowledge: when the player has enough gold, the coach should recommend reset timing.

---

## 8. Final Portfolio Positioning

RiftBuddy should become your **AI product engineering flagship**.

Use it for:

- OpenAI applied engineering
- Anthropic product engineering
- gaming AI tools
- Riot / Discord / Twitch / Roblox
- AI startup roles
- frontend/backend full-stack roles with real-time systems

One-line pitch:

**RiftBuddy is a real-time AI League coach that converts live game telemetry into grounded, low-latency voice advice using event detection, champion knowledge retrieval, and LLM planning.**
