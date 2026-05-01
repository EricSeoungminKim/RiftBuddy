# RiftBuddy MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working v1 of RiftBuddy — Riot Live Client API → LLM advice → voice output → Electron overlay — with freemium auth scaffolding, no vision system yet.

**Architecture:** Python FastAPI backend handles Riot API polling, context aggregation, LLM inference, and STT/TTS. Electron + React frontend renders a transparent in-game overlay and communicates with the backend via WebSocket. Supabase handles auth and user data for freemium gating.

**Tech Stack:** Python 3.11, FastAPI, faster-whisper, ElevenLabs API, Anthropic SDK (claude-sonnet-4-6), Electron 28, React 18, TypeScript, Supabase, PyInstaller, Electron Builder

---

## File Structure

```
riftbuddy/
├── backend/
│   ├── main.py                    # FastAPI app entry, WebSocket endpoint
│   ├── config.py                  # Env var loading + validation
│   ├── riot/
│   │   ├── __init__.py
│   │   └── live_client.py         # Polls localhost:2999, returns GameState
│   ├── context/
│   │   ├── __init__.py
│   │   └── engine.py              # Aggregates GameState → ContextPacket
│   ├── llm/
│   │   ├── __init__.py
│   │   └── advisor.py             # Anthropic SDK call, prompt caching
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── stt.py                 # faster-whisper wake word + query STT
│   │   └── tts.py                 # ElevenLabs TTS → audio bytes
│   ├── auth/
│   │   ├── __init__.py
│   │   └── supabase_client.py     # Supabase auth verification middleware
│   └── tests/
│       ├── test_live_client.py
│       ├── test_engine.py
│       ├── test_advisor.py
│       └── test_voice.py
├── frontend/
│   ├── electron/
│   │   └── main.ts                # Electron main process, transparent window
│   ├── src/
│   │   ├── App.tsx                # Root component
│   │   ├── components/
│   │   │   ├── Overlay.tsx        # Transparent HUD wrapper
│   │   │   ├── AdviceCard.tsx     # Displays LLM advice text
│   │   │   └── StatusBar.tsx      # Connection + game state indicator
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts    # WS connection + message parsing
│   │   └── types.ts               # Shared TypeScript types
│   ├── package.json
│   └── tsconfig.json
├── requirements.txt
├── .env.example
└── README.md
```

---

## Task 1: Project Scaffolding + Config

**Files:**

- Create: `backend/config.py`
- Create: `backend/main.py`
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Create `.env.example`**

```bash
ANTHROPIC_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
RIOT_API_KEY=your_riot_api_key
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi[standard]==0.128.0
uvicorn[standard]==0.46.0
httpx==0.28.1
anthropic==0.97.0
elevenlabs==2.45.0
faster-whisper==1.2.1
sounddevice==0.5.5
numpy==2.4.4
supabase==2.29.0
python-dotenv==1.2.2
pytest==9.0.3
pytest-asyncio==1.3.0
```

- [ ] **Step 3: Create `backend/config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED = [
    "ANTHROPIC_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
]

def load_config() -> dict:
    missing = [k for k in REQUIRED if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")
    return {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
        "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID"),
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY"),
        "riot_api_key": os.getenv("RIOT_API_KEY", ""),
    }

CONFIG = load_config()
```

- [ ] **Step 4: Create `backend/main.py`** (skeleton — filled in Task 7)

```python
from fastapi import FastAPI
from backend.config import CONFIG

app = FastAPI(title="RiftBuddy Backend")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Install dependencies**

```bash
cd backend
pip install -r ../requirements.txt
```

- [ ] **Step 6: Verify health endpoint**

```bash
uvicorn backend.main:app --reload
# In another terminal:
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example backend/config.py backend/main.py
git commit -m "feat: project scaffolding and config loading"
```

---

## Task 2: Riot Live Client Poller

**Files:**

- Create: `backend/riot/__init__.py`
- Create: `backend/riot/live_client.py`
- Create: `backend/tests/test_live_client.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_live_client.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.riot.live_client import fetch_game_state, GameState

@pytest.mark.asyncio
async def test_fetch_game_state_returns_game_state():
    mock_response = {
        "activePlayer": {
            "championStats": {"currentHealth": 1200, "maxHealth": 2000},
            "currentGold": 1500,
            "level": 8,
        },
        "events": {"Events": []},
        "gameData": {"gameTime": 420.0},
    }
    with patch("backend.riot.live_client._get", new=AsyncMock(return_value=mock_response)):
        state = await fetch_game_state()
    assert isinstance(state, GameState)
    assert state.current_health == 1200
    assert state.gold == 1500
    assert state.level == 8
    assert state.game_time == 420.0

@pytest.mark.asyncio
async def test_fetch_game_state_returns_none_when_client_down():
    with patch("backend.riot.live_client._get", new=AsyncMock(side_effect=Exception("Connection refused"))):
        state = await fetch_game_state()
    assert state is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_live_client.py -v
# Expected: FAIL — ModuleNotFoundError or ImportError
```

- [ ] **Step 3: Create `backend/riot/__init__.py`**

```python

```

- [ ] **Step 4: Create `backend/riot/live_client.py`**

```python
from dataclasses import dataclass
from typing import Optional
import httpx

LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata"

@dataclass(frozen=True)
class GameState:
    current_health: float
    max_health: float
    gold: float
    level: int
    game_time: float

async def _get(path: str) -> dict:
    async with httpx.AsyncClient(verify=False, timeout=2.0) as client:
        response = await client.get(f"{LIVE_CLIENT_URL}{path}")
        response.raise_for_status()
        return response.json()

async def fetch_game_state() -> Optional[GameState]:
    try:
        data = await _get("/allgamedata")
        player = data["activePlayer"]
        stats = player["championStats"]
        return GameState(
            current_health=stats["currentHealth"],
            max_health=stats["maxHealth"],
            gold=player["currentGold"],
            level=player["level"],
            game_time=data["gameData"]["gameTime"],
        )
    except Exception:
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest backend/tests/test_live_client.py -v
# Expected: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/riot/ backend/tests/test_live_client.py
git commit -m "feat: Riot Live Client API poller with GameState dataclass"
```

---

## Task 3: Context Engine

**Files:**

- Create: `backend/context/__init__.py`
- Create: `backend/context/engine.py`
- Create: `backend/tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_engine.py
import pytest
from backend.context.engine import build_context_packet, ContextPacket
from backend.riot.live_client import GameState

def test_build_context_packet_healthy_player():
    state = GameState(
        current_health=1800, max_health=2000, gold=2500, level=10, game_time=600.0
    )
    packet = build_context_packet(state)
    assert isinstance(packet, ContextPacket)
    assert packet.health_percent == 90.0
    assert packet.gold == 2500
    assert packet.game_time_minutes == 10.0
    assert "healthy" in packet.summary.lower()

def test_build_context_packet_low_health():
    state = GameState(
        current_health=400, max_health=2000, gold=800, level=5, game_time=300.0
    )
    packet = build_context_packet(state)
    assert packet.health_percent == 20.0
    assert "low health" in packet.summary.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_engine.py -v
# Expected: FAIL — ImportError
```

- [ ] **Step 3: Create `backend/context/__init__.py`**

```python

```

- [ ] **Step 4: Create `backend/context/engine.py`**

```python
from dataclasses import dataclass
from backend.riot.live_client import GameState

@dataclass(frozen=True)
class ContextPacket:
    health_percent: float
    gold: float
    level: int
    game_time_minutes: float
    summary: str

def build_context_packet(state: GameState) -> ContextPacket:
    health_percent = round((state.current_health / state.max_health) * 100, 1)
    game_time_minutes = round(state.game_time / 60, 1)

    if health_percent < 30:
        health_status = "low health"
    elif health_percent < 60:
        health_status = "moderate health"
    else:
        health_status = "healthy"

    summary = (
        f"Player is {health_status} ({health_percent}% HP). "
        f"Gold: {state.gold}. Level: {state.level}. "
        f"Game time: {game_time_minutes} minutes."
    )
    return ContextPacket(
        health_percent=health_percent,
        gold=state.gold,
        level=state.level,
        game_time_minutes=game_time_minutes,
        summary=summary,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest backend/tests/test_engine.py -v
# Expected: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/context/ backend/tests/test_engine.py
git commit -m "feat: context engine aggregates GameState into ContextPacket"
```

---

## Task 4: LLM Advisor (Claude API + Prompt Caching)

**Files:**

- Create: `backend/llm/__init__.py`
- Create: `backend/llm/advisor.py`
- Create: `backend/tests/test_advisor.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_advisor.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.llm.advisor import get_advice
from backend.context.engine import ContextPacket

@pytest.mark.asyncio
async def test_get_advice_returns_string():
    packet = ContextPacket(
        health_percent=45.0, gold=1800, level=7,
        game_time_minutes=8.5,
        summary="Player is moderate health (45% HP). Gold: 1800. Level: 7. Game time: 8.5 minutes."
    )
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Consider recalling to base to restore health.")]

    with patch("backend.llm.advisor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        advice = await get_advice(packet, user_query=None)

    assert isinstance(advice, str)
    assert len(advice) > 0

@pytest.mark.asyncio
async def test_get_advice_with_user_query():
    packet = ContextPacket(
        health_percent=80.0, gold=3200, level=11,
        game_time_minutes=15.0,
        summary="Player is healthy (80% HP). Gold: 3200. Level: 11. Game time: 15.0 minutes."
    )
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="You should push the wave and take dragon.")]

    with patch("backend.llm.advisor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        advice = await get_advice(packet, user_query="should I push or freeze?")

    assert isinstance(advice, str)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_advisor.py -v
# Expected: FAIL — ImportError
```

- [ ] **Step 3: Create `backend/llm/__init__.py`**

```python

```

- [ ] **Step 4: Create `backend/llm/advisor.py`**

```python
from typing import Optional
import anthropic
from backend.config import CONFIG
from backend.context.engine import ContextPacket

anthropic_client = anthropic.AsyncAnthropic(api_key=CONFIG["anthropic_api_key"])

SYSTEM_PROMPT = """You are RiftBuddy, an expert League of Legends duo partner and coach.
You give concise, actionable macro advice in 1-2 sentences.
Be encouraging and direct. Never give generic advice — always tie it to the current game state."""

async def get_advice(packet: ContextPacket, user_query: Optional[str]) -> str:
    user_content = f"Current game state:\n{packet.summary}"
    if user_query:
        user_content += f"\n\nPlayer asks: {user_query}"
    else:
        user_content += "\n\nWhat should I focus on right now?"

    message = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    return message.content[0].text
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest backend/tests/test_advisor.py -v
# Expected: 2 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/llm/ backend/tests/test_advisor.py
git commit -m "feat: LLM advisor with Claude claude-sonnet-4-6 and prompt caching"
```

---

## Task 5: TTS (ElevenLabs)

**Files:**

- Create: `backend/voice/__init__.py`
- Create: `backend/voice/tts.py`
- Create: `backend/tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_voice.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.voice.tts import text_to_speech_bytes

@pytest.mark.asyncio
async def test_text_to_speech_returns_bytes():
    fake_audio = b"fake_audio_data_bytes"
    mock_response = MagicMock()
    mock_response.content = fake_audio

    with patch("backend.voice.tts.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await text_to_speech_bytes("Hello summoner")

    assert isinstance(result, bytes)
    assert len(result) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_voice.py::test_text_to_speech_returns_bytes -v
# Expected: FAIL — ImportError
```

- [ ] **Step 3: Create `backend/voice/__init__.py`**

```python

```

- [ ] **Step 4: Create `backend/voice/tts.py`**

```python
import httpx
from backend.config import CONFIG

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

async def text_to_speech_bytes(text: str) -> bytes:
    voice_id = CONFIG["elevenlabs_voice_id"]
    headers = {
        "xi-api-key": CONFIG["elevenlabs_api_key"],
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{ELEVENLABS_URL}/{voice_id}",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.content
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest backend/tests/test_voice.py -v
# Expected: 1 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/voice/tts.py backend/voice/__init__.py backend/tests/test_voice.py
git commit -m "feat: ElevenLabs TTS returning audio bytes"
```

---

## Task 6: STT Wake Word Detection (faster-whisper)

**Files:**

- Modify: `backend/voice/stt.py`
- Modify: `backend/tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to backend/tests/test_voice.py

import numpy as np
from backend.voice.stt import transcribe_audio_chunk, contains_wake_word

def test_contains_wake_word_positive():
    assert contains_wake_word("hey buddy should I push this wave") is True
    assert contains_wake_word("Hey Buddy, what do I do?") is True

def test_contains_wake_word_negative():
    assert contains_wake_word("I think we should push") is False
    assert contains_wake_word("") is False

def test_transcribe_audio_chunk_returns_string():
    # faster-whisper can't be easily mocked at unit level; this is an integration smoke test
    # Pass silent audio — should return empty or near-empty string
    silent_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence at 16kHz
    result = transcribe_audio_chunk(silent_audio)
    assert isinstance(result, str)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_voice.py::test_contains_wake_word_positive -v
# Expected: FAIL — ImportError
```

- [ ] **Step 3: Create `backend/voice/stt.py`**

```python
import numpy as np
from faster_whisper import WhisperModel

WAKE_WORDS = {"hey buddy", "hey, buddy"}

_model: WhisperModel | None = None

def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    return _model

def transcribe_audio_chunk(audio: np.ndarray) -> str:
    model = _get_model()
    segments, _ = model.transcribe(audio, beam_size=1, language="en")
    return " ".join(segment.text.strip() for segment in segments).lower()

def contains_wake_word(transcript: str) -> bool:
    lower = transcript.lower().strip()
    return any(wake in lower for wake in WAKE_WORDS)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/test_voice.py -v
# Expected: 3 passed (transcribe test may download tiny.en model on first run ~40MB)
```

- [ ] **Step 5: Commit**

```bash
git add backend/voice/stt.py backend/tests/test_voice.py
git commit -m "feat: faster-whisper STT with hey buddy wake word detection"
```

---

## Task 7: FastAPI WebSocket Endpoint (Core Loop)

**Files:**

- Modify: `backend/main.py`

- [ ] **Step 1: Update `backend/main.py` with full WebSocket loop**

```python
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from backend.config import CONFIG
from backend.riot.live_client import fetch_game_state
from backend.context.engine import build_context_packet
from backend.llm.advisor import get_advice
from backend.voice.tts import text_to_speech_bytes

app = FastAPI(title="RiftBuddy Backend")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive message from frontend (user query or poll trigger)
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            msg = json.loads(raw)
            user_query = msg.get("query")  # None = proactive advice

            game_state = await fetch_game_state()
            if game_state is None:
                await websocket.send_json({"type": "error", "message": "Game not running"})
                continue

            packet = build_context_packet(game_state)
            advice = await get_advice(packet, user_query=user_query)
            audio_bytes = await text_to_speech_bytes(advice)

            await websocket.send_json({
                "type": "advice",
                "text": advice,
                "context": {
                    "health_percent": packet.health_percent,
                    "gold": packet.gold,
                    "level": packet.level,
                    "game_time_minutes": packet.game_time_minutes,
                },
            })
            # Send audio as binary frame
            await websocket.send_bytes(audio_bytes)

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
```

- [ ] **Step 2: Test the endpoint manually**

```bash
# Start backend
uvicorn backend.main:app --reload

# In another terminal, use wscat or websocat:
# Install: npm install -g wscat
wscat -c ws://localhost:8000/ws
# Send: {"query": null}
# Expected: JSON advice message + binary audio frame
# Note: game_state will return None if LoL is not running — that's correct behavior
```

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: WebSocket endpoint wiring Riot API -> context -> LLM -> TTS"
```

---

## Task 8: Electron Frontend Scaffold

**Files:**

- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/electron/main.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "riftbuddy-overlay",
  "version": "0.1.0",
  "private": true,
  "main": "dist/electron/main.js",
  "scripts": {
    "dev": "concurrently \"vite\" \"wait-on http://localhost:5173 && electron .\"",
    "build": "vite build && tsc -p tsconfig.electron.json",
    "electron:pack": "electron-builder"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "concurrently": "^8.2.0",
    "electron": "^28.0.0",
    "electron-builder": "^24.9.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "wait-on": "^7.2.0"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create `frontend/electron/main.ts`**

```typescript
import { app, BrowserWindow } from "electron";
import path from "path";

const isDev = process.env.NODE_ENV === "development";

function createWindow(): void {
  const win = new BrowserWindow({
    width: 400,
    height: 200,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  win.setIgnoreMouseEvents(true, { forward: true });

  if (isDev) {
    win.loadURL("http://localhost:5173");
  } else {
    win.loadFile(path.join(__dirname, "../index.html"));
  }
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => app.quit());
```

- [ ] **Step 4: Create `frontend/src/types.ts`**

```typescript
export interface AdviceMessage {
  type: "advice";
  text: string;
  context: {
    health_percent: number;
    gold: number;
    level: number;
    game_time_minutes: number;
  };
}

export interface ErrorMessage {
  type: "error";
  message: string;
}

export type ServerMessage = AdviceMessage | ErrorMessage;
```

- [ ] **Step 5: Create `frontend/src/App.tsx`** (placeholder — filled in Task 9)

```tsx
export default function App() {
  return <div>RiftBuddy loading...</div>;
}
```

- [ ] **Step 6: Install frontend dependencies**

```bash
cd frontend
npm install
```

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: Electron frontend scaffold with transparent overlay window"
```

---

## Task 9: React Overlay Components + WebSocket Hook

**Files:**

- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/components/Overlay.tsx`
- Create: `frontend/src/components/AdviceCard.tsx`
- Create: `frontend/src/components/StatusBar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create `frontend/src/hooks/useWebSocket.ts`**

```typescript
import { useEffect, useRef, useState, useCallback } from "react";
import type { ServerMessage } from "../types";

const WS_URL = "ws://localhost:8000/ws";

export function useWebSocket() {
  const [lastAdvice, setLastAdvice] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [audioQueue, setAudioQueue] = useState<ArrayBuffer[]>([]);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => setIsConnected(true);
    socket.onclose = () => setIsConnected(false);

    socket.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg: ServerMessage = JSON.parse(event.data);
        if (msg.type === "advice") {
          setLastAdvice(msg.text);
        }
      } else if (event.data instanceof Blob) {
        event.data
          .arrayBuffer()
          .then((buf) => setAudioQueue((q) => [...q, buf]));
      }
    };

    return () => socket.close();
  }, []);

  const sendQuery = useCallback((query: string | null) => {
    ws.current?.send(JSON.stringify({ query }));
  }, []);

  return { lastAdvice, isConnected, audioQueue, sendQuery };
}
```

- [ ] **Step 2: Create `frontend/src/components/AdviceCard.tsx`**

```tsx
interface Props {
  text: string;
}

export function AdviceCard({ text }: Props) {
  return (
    <div
      style={{
        background: "rgba(0, 0, 0, 0.75)",
        borderRadius: 8,
        padding: "10px 14px",
        color: "#FFD700",
        fontSize: 14,
        fontFamily: "sans-serif",
        maxWidth: 360,
        lineHeight: 1.4,
      }}
    >
      <span style={{ color: "#00BFFF", fontWeight: "bold" }}>Buddy: </span>
      {text}
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/StatusBar.tsx`**

```tsx
interface Props {
  isConnected: boolean;
}

export function StatusBar({ isConnected }: Props) {
  return (
    <div
      style={{
        fontSize: 11,
        color: isConnected ? "#00FF88" : "#FF4444",
        fontFamily: "monospace",
        padding: "2px 6px",
      }}
    >
      {isConnected ? "● LIVE" : "○ OFFLINE"}
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/Overlay.tsx`**

```tsx
import { useEffect } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { AdviceCard } from "./AdviceCard";
import { StatusBar } from "./StatusBar";

export function Overlay() {
  const { lastAdvice, isConnected, audioQueue } = useWebSocket();

  useEffect(() => {
    if (audioQueue.length === 0) return;
    const buf = audioQueue[audioQueue.length - 1];
    const blob = new Blob([buf], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play().catch(() => {});
    return () => URL.revokeObjectURL(url);
  }, [audioQueue]);

  return (
    <div style={{ padding: 8 }}>
      <StatusBar isConnected={isConnected} />
      {lastAdvice && <AdviceCard text={lastAdvice} />}
    </div>
  );
}
```

- [ ] **Step 5: Update `frontend/src/App.tsx`**

```tsx
import { Overlay } from "./components/Overlay";

export default function App() {
  return <Overlay />;
}
```

- [ ] **Step 6: Run frontend dev mode**

```bash
cd frontend
npm run dev
# Open http://localhost:5173 — should show "○ OFFLINE" if backend not running
# Start backend in parallel: uvicorn backend.main:app --reload
# Reload — should show "● LIVE"
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: Overlay components with WebSocket hook and audio playback"
```

---

## Task 10: Supabase Auth Scaffolding (Freemium Gate)

**Files:**

- Create: `backend/auth/__init__.py`
- Create: `backend/auth/supabase_client.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create `backend/auth/__init__.py`**

```python

```

- [ ] **Step 2: Create `backend/auth/supabase_client.py`**

```python
from supabase import create_client, Client
from backend.config import CONFIG

_client: Client | None = None

def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(CONFIG["supabase_url"], CONFIG["supabase_anon_key"])
    return _client

async def verify_token(jwt: str) -> dict | None:
    """Returns user dict if valid, None if invalid."""
    try:
        supabase = get_supabase()
        response = supabase.auth.get_user(jwt)
        return response.user.model_dump() if response.user else None
    except Exception:
        return None
```

- [ ] **Step 3: Add auth gate to WebSocket in `backend/main.py`**

Replace the `@app.websocket("/ws")` handler with:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    # Verify auth token passed as query param: ws://localhost:8000/ws?token=JWT
    user = await verify_token(token) if token else None
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    try:
        while True:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            msg = json.loads(raw)
            user_query = msg.get("query")

            game_state = await fetch_game_state()
            if game_state is None:
                await websocket.send_json({"type": "error", "message": "Game not running"})
                continue

            packet = build_context_packet(game_state)
            advice = await get_advice(packet, user_query=user_query)
            audio_bytes = await text_to_speech_bytes(advice)

            await websocket.send_json({
                "type": "advice",
                "text": advice,
                "context": {
                    "health_percent": packet.health_percent,
                    "gold": packet.gold,
                    "level": packet.level,
                    "game_time_minutes": packet.game_time_minutes,
                },
            })
            await websocket.send_bytes(audio_bytes)

    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
```

Also add to imports at top of `backend/main.py`:

```python
from backend.auth.supabase_client import verify_token
```

- [ ] **Step 4: Verify backend starts without error**

```bash
uvicorn backend.main:app --reload
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

- [ ] **Step 5: Commit**

```bash
git add backend/auth/ backend/main.py
git commit -m "feat: Supabase JWT auth gate on WebSocket endpoint"
```

---

## Task 11: End-to-End Smoke Test

**Goal:** Run everything together and verify the full loop works.

- [ ] **Step 1: Start backend**

```bash
uvicorn backend.main:app --reload --port 8000
```

- [ ] **Step 2: Start Electron overlay in dev mode**

```bash
cd frontend
NODE_ENV=development npm run dev
```

- [ ] **Step 3: Launch League of Legends and enter a game**

The Riot Live Client API starts at `https://127.0.0.1:2999` once a game begins.

- [ ] **Step 4: Connect WebSocket with valid Supabase token**

From browser console or wscat:

```
wscat -c "ws://localhost:8000/ws?token=YOUR_SUPABASE_JWT"
> {"query": "should I push or freeze?"}
```

Expected: JSON advice message + binary audio plays in overlay.

- [ ] **Step 5: Verify overlay shows advice text and "● LIVE" status**

- [ ] **Step 6: Run full test suite**

```bash
pytest backend/tests/ -v
# Expected: all tests pass
```

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "feat: end-to-end smoke test verified, RiftBuddy MVP complete"
```

---

## What's Deferred (Post-MVP)

| Feature                   | Reason Deferred                             |
| ------------------------- | ------------------------------------------- |
| YOLOv8 vision             | Complexity — add after core loop proven     |
| Hey Buddy microphone loop | Needs sounddevice integration + threading   |
| Draft Consultant          | Requires Riot match data API (separate key) |
| Post-game analysis        | Needs match history API                     |
| Freemium tier limits      | Supabase schema + usage tracking            |
| PyInstaller packaging     | Package after features stabilized           |
