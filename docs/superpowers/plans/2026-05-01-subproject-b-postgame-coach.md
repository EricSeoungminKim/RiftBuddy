# Post-game Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Screen 3 (Post-game Coach) to the Draft Window — triggered when the Live Client returns 404 (game ended) — showing strengths, improvements, key moments, and next-game goals derived from in-game GameState snapshots via LLM.

**Architecture:** Backend stores GameState snapshots in-memory during game (every 30s). On game end, `POST /postgame/coach` feeds snapshots to the existing LLM advisor and returns structured JSON. Frontend Draft Window navigates to `/postgame` and renders four sections. Backend also exposes `POST /game/snapshot` (internal polling) and `DELETE /game/snapshots`. Game-end detection runs in the existing WebSocket loop via a new `game_session.py` module.

**Tech Stack:** FastAPI, Python in-memory list, existing `get_advice()` LLM advisor, React 18 + TypeScript, React Router v6 (HashRouter already added in Sub-project A), existing `useWebSocket` WebSocket for game-end broadcast.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/game_session.py` | Create | In-memory snapshot store + game-end detection |
| `backend/postgame/router.py` | Create | FastAPI router: `/game/snapshot`, `/postgame/coach`, `/delete/game/snapshots` |
| `backend/postgame/__init__.py` | Create | Package marker |
| `backend/main.py` | Modify | Mount postgame router + call snapshot store on WS loop |
| `frontend/src/draft/pages/PostGamePage.tsx` | Create | Screen 3 UI: strengths / improvements / moments / goals |
| `frontend/src/draft/hooks/usePostGame.ts` | Create | Fetch `/postgame/coach`, state management |
| `frontend/src/draft/DraftApp.tsx` | Modify | Add `/postgame` route, navigate on WS game-end event |

---

## Task 1: In-memory snapshot store (`backend/game_session.py`)

**Files:**
- Create: `backend/game_session.py`
- Test: `tests/test_game_session.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_game_session.py
import pytest
from backend.game_session import GameSession
from backend.riot.live_client import GameState


def _make_state(game_time: float = 300.0, kills: int = 2) -> GameState:
    return GameState(
        current_health=1500,
        max_health=2000,
        gold=3000,
        level=9,
        game_time=game_time,
        champion_name="Rumble",
        kills=kills,
        deaths=1,
        assists=3,
        creep_score=80,
    )


def test_add_snapshot_stores_state():
    session = GameSession()
    state = _make_state()
    session.add_snapshot(state)
    assert len(session.snapshots) == 1
    assert session.snapshots[0] is state


def test_add_snapshot_caps_at_60():
    session = GameSession()
    for i in range(65):
        session.add_snapshot(_make_state(game_time=float(i * 30)))
    assert len(session.snapshots) == 60


def test_clear_removes_all():
    session = GameSession()
    session.add_snapshot(_make_state())
    session.add_snapshot(_make_state(game_time=60.0))
    session.clear()
    assert len(session.snapshots) == 0


def test_is_empty_initial():
    session = GameSession()
    assert session.is_empty is True


def test_is_empty_after_add():
    session = GameSession()
    session.add_snapshot(_make_state())
    assert session.is_empty is False


def test_summary_lines_format():
    session = GameSession()
    session.add_snapshot(_make_state(game_time=180.0, kills=2))
    lines = session.summary_lines()
    assert len(lines) == 1
    assert "3:00" in lines[0]
    assert "킬 2" in lines[0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
python -m pytest tests/test_game_session.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `game_session` does not exist yet.

- [ ] **Step 3: Implement `backend/game_session.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.riot.live_client import GameState

MAX_SNAPSHOTS = 60


@dataclass
class GameSession:
    snapshots: list["GameState"] = field(default_factory=list)

    def add_snapshot(self, state: "GameState") -> None:
        if len(self.snapshots) >= MAX_SNAPSHOTS:
            self.snapshots.pop(0)
        self.snapshots.append(state)

    def clear(self) -> None:
        self.snapshots.clear()

    @property
    def is_empty(self) -> bool:
        return len(self.snapshots) == 0

    def summary_lines(self) -> list[str]:
        lines = []
        for s in self.snapshots:
            minutes = int(s.game_time // 60)
            seconds = int(s.game_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"
            hp_pct = round((s.current_health / s.max_health) * 100, 1) if s.max_health else 0
            lines.append(
                f"[{timestamp}] 챔피언 {s.champion_name} | HP {hp_pct}% | "
                f"골드 {s.gold:g} | 킬 {s.kills}/{s.deaths}/{s.assists} | "
                f"CS {s.creep_score} | 최근이벤트: {', '.join(s.recent_events) if s.recent_events else '없음'}"
            )
        return lines
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_game_session.py -v
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/game_session.py tests/test_game_session.py
git commit -m "feat(postgame): add in-memory GameSession snapshot store"
```

---

## Task 2: Postgame FastAPI router (`backend/postgame/`)

**Files:**
- Create: `backend/postgame/__init__.py`
- Create: `backend/postgame/router.py`
- Test: `tests/test_postgame_router.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_postgame_router.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from backend.main import app  # router will be mounted in Task 3
# These tests will fail until Task 3 mounts the router — that's expected.
# Run them again after Task 3 to verify full integration.

client = TestClient(app)


def test_snapshot_endpoint_stores_state():
    payload = {
        "current_health": 1500,
        "max_health": 2000,
        "gold": 3000,
        "level": 9,
        "game_time": 300.0,
        "champion_name": "Rumble",
        "kills": 2,
        "deaths": 1,
        "assists": 3,
        "creep_score": 80,
        "recent_events": ["DragonKill"],
    }
    # First clear any existing snapshots
    client.delete("/game/snapshots")
    response = client.post("/game/snapshot", json=payload)
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_delete_snapshots_clears_store():
    response = client.delete("/game/snapshots")
    assert response.status_code == 200
    assert response.json()["cleared"] is True


def test_postgame_coach_returns_structured_json():
    # Seed one snapshot
    client.delete("/game/snapshots")
    payload = {
        "current_health": 1500,
        "max_health": 2000,
        "gold": 3000,
        "level": 9,
        "game_time": 300.0,
        "champion_name": "Rumble",
        "kills": 2,
        "deaths": 1,
        "assists": 3,
        "creep_score": 80,
        "recent_events": [],
    }
    client.post("/game/snapshot", json=payload)

    mock_response = '{"strengths": ["좋은 CS"], "improvements": ["시야 부족"], "moments": ["5:00 — 갱 회피"], "goals": ["CS 90 유지"]}'
    with patch("backend.postgame.router.get_advice", new=AsyncMock(return_value=mock_response)):
        response = client.post("/postgame/coach")
    assert response.status_code == 200
    data = response.json()
    assert "strengths" in data
    assert "improvements" in data
    assert "moments" in data
    assert "goals" in data


def test_postgame_coach_empty_returns_error():
    client.delete("/game/snapshots")
    response = client.post("/postgame/coach")
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_postgame_router.py -v
```

Expected: `ImportError` or `404` — router not mounted yet.

- [ ] **Step 3: Create `backend/postgame/__init__.py`**

```python
```

(empty file)

- [ ] **Step 4: Create `backend/postgame/router.py`**

```python
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.context.engine import ContextPacket
from backend.game_session import GameSession
from backend.llm.advisor import get_advice

router = APIRouter()
logger = logging.getLogger(__name__)

# Module-level singleton shared with main.py
_session = GameSession()


def get_session() -> GameSession:
    return _session


class SnapshotPayload(BaseModel):
    current_health: float
    max_health: float
    gold: float
    level: int
    game_time: float
    champion_name: str = "Unknown"
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    creep_score: int = 0
    recent_events: list[str] = []


@router.post("/game/snapshot")
async def add_snapshot(payload: SnapshotPayload):
    from backend.riot.live_client import GameState

    state = GameState(
        current_health=payload.current_health,
        max_health=payload.max_health,
        gold=payload.gold,
        level=payload.level,
        game_time=payload.game_time,
        champion_name=payload.champion_name,
        kills=payload.kills,
        deaths=payload.deaths,
        assists=payload.assists,
        creep_score=payload.creep_score,
        recent_events=tuple(payload.recent_events),
    )
    _session.add_snapshot(state)
    return {"count": len(_session.snapshots)}


@router.delete("/game/snapshots")
async def clear_snapshots():
    _session.clear()
    return {"cleared": True}


@router.post("/postgame/coach")
async def generate_coach_report():
    if _session.is_empty:
        raise HTTPException(status_code=422, detail="스냅샷이 없습니다. 경기 데이터가 없습니다.")

    summary_lines = _session.summary_lines()
    snapshot_text = "\n".join(summary_lines)

    prompt = (
        "다음은 이번 경기 중 수집된 게임 상태 스냅샷입니다:\n"
        f"{snapshot_text}\n\n"
        "다음 항목을 한국어로 분석해주세요:\n"
        "1. 잘한 점 3가지\n"
        "2. 개선할 점 3가지\n"
        "3. 핵심 순간 3가지 (타임스탬프 포함)\n"
        "4. 다음 경기 집중 목표 2가지\n\n"
        "반드시 JSON 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '{"strengths": ["...","...","..."], "improvements": ["...","...","..."], '
        '"moments": ["...","...","..."], "goals": ["...","..."]}'
    )

    dummy_packet = ContextPacket(
        health_percent=50.0,
        gold=0.0,
        level=18,
        game_time_minutes=0.0,
        summary=prompt,
    )

    raw_response = await get_advice(dummy_packet, user_query=prompt, language="ko")

    try:
        start = raw_response.index("{")
        end = raw_response.rindex("}") + 1
        data = json.loads(raw_response[start:end])
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse coach JSON: %s — raw: %s", exc, raw_response[:200])
        raise HTTPException(status_code=500, detail="LLM 응답 파싱 실패")

    return data
```

- [ ] **Step 5: Run tests to verify they pass (after Task 3 mounts router)**

Skip for now — run again after Task 3.

- [ ] **Step 6: Commit**

```bash
git add backend/postgame/__init__.py backend/postgame/router.py
git commit -m "feat(postgame): add coach + snapshot endpoints"
```

---

## Task 3: Mount postgame router + game-end detection in `backend/main.py`

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_postgame_router.py` (re-run from Task 2)

The WebSocket loop already polls Live Client. We extend it to:
1. Store snapshots every 30s during active game.
2. Detect game-end (Live Client 404) and broadcast a `game_end` WebSocket event.

- [ ] **Step 1: Read current `backend/main.py`** (already read above — lines 1–80)

- [ ] **Step 2: Add postgame router import and mount to `backend/main.py`**

Find the `app = FastAPI(...)` section. After the `from backend.riot.live_client import fetch_game_state` import line, add:

```python
from backend.postgame.router import router as postgame_router, get_session as get_game_session
```

After `app = FastAPI(title="RiftBuddy Backend")`, add:

```python
app.include_router(postgame_router)
```

- [ ] **Step 3: Add snapshot tracking + game-end detection to the WebSocket loop**

Inside the `websocket_endpoint` function, locate the polling section where `fetch_game_state` is called. Add snapshot tracking logic. The current loop is in the `action == "advice"` branch — add a separate periodic background task instead.

Add a module-level variable after `active_websockets`:

```python
_last_snapshot_time: float = 0.0
_game_was_active: bool = False
```

Add a helper function before `startup`:

```python
async def _game_poll_loop() -> None:
    global _last_snapshot_time, _game_was_active
    import time
    session = get_game_session()
    while True:
        await asyncio.sleep(5)
        try:
            state = await fetch_game_state()
            now = time.monotonic()
            if state is not None:
                _game_was_active = True
                if now - _last_snapshot_time >= 30:
                    session.add_snapshot(state)
                    _last_snapshot_time = now
            else:
                # state is None → Live Client returned 404 → game ended
                if _game_was_active:
                    _game_was_active = False
                    _last_snapshot_time = 0.0
                    await _broadcast_game_end()
        except Exception:
            pass


async def _broadcast_game_end() -> None:
    dead = set()
    for ws in active_websockets:
        try:
            await ws.send_json({"type": "game_end"})
        except Exception:
            dead.add(ws)
    active_websockets.difference_update(dead)
```

Update `startup` to also start the poll loop:

```python
@app.on_event("startup")
async def startup() -> None:
    global wake_word_task
    if CONFIG["wake_word"] == "1":
        wake_word_task = asyncio.create_task(run_wake_word_loop(broadcast_wake_ack, broadcast_voice_question))
    asyncio.create_task(_game_poll_loop())
```

- [ ] **Step 4: Check `fetch_game_state` return type**

Read `backend/riot/live_client.py` to confirm `fetch_game_state` returns `GameState | None` (returns `None` on 404).

```bash
grep -n "async def fetch_game_state" /Users/smk/Documents/GitHub/RiftBuddy/backend/riot/live_client.py
```

If it raises on 404 instead of returning `None`, wrap the call in `_game_poll_loop` with `except httpx.HTTPStatusError`.

- [ ] **Step 5: Run postgame router tests**

```bash
python -m pytest tests/test_postgame_router.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest --tb=short -q
```

Expected: all existing tests still pass + 4 new.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py
git commit -m "feat(postgame): mount router + game-end detection loop"
```

---

## Task 4: `usePostGame` hook (`frontend/src/draft/hooks/usePostGame.ts`)

**Files:**
- Create: `frontend/src/draft/hooks/usePostGame.ts`

- [ ] **Step 1: Create the hook**

```typescript
// frontend/src/draft/hooks/usePostGame.ts
import { useState, useCallback } from "react";

const API_BASE = (import.meta.env.VITE_RIFTBUDDY_API_URL as string) ?? "http://localhost:8000";

export interface CoachReport {
  strengths: string[];
  improvements: string[];
  moments: string[];
  goals: string[];
}

export interface UsePostGameResult {
  report: CoachReport | null;
  loading: boolean;
  error: string | null;
  fetchReport: () => Promise<void>;
  clearSnapshots: () => Promise<void>;
}

export function usePostGame(): UsePostGameResult {
  const [report, setReport] = useState<CoachReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/postgame/coach`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data: CoachReport = await res.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류");
    } finally {
      setLoading(false);
    }
  }, []);

  const clearSnapshots = useCallback(async () => {
    await fetch(`${API_BASE}/game/snapshots`, { method: "DELETE" }).catch(() => {});
    setReport(null);
    setError(null);
  }, []);

  return { report, loading, error, fetchReport, clearSnapshots };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/draft/hooks/usePostGame.ts
git commit -m "feat(postgame): add usePostGame hook"
```

---

## Task 5: `PostGamePage.tsx` — Screen 3 UI

**Files:**
- Create: `frontend/src/draft/pages/PostGamePage.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/draft/pages/PostGamePage.tsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { usePostGame } from "../hooks/usePostGame";

const COLORS = {
  bg: "#0f1117",
  card: "#1a1d26",
  border: "#2a2d3a",
  teal: "#00c8a0",
  red: "#e84057",
  text: "#e8e8e8",
  muted: "#8888aa",
};

function Section({ title, items, color }: { title: string; items: string[]; color?: string }) {
  return (
    <div
      style={{
        background: COLORS.card,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 8,
        padding: 16,
        flex: 1,
      }}
    >
      <h3 style={{ margin: "0 0 12px", color: color ?? COLORS.teal, fontSize: 14, fontWeight: 700 }}>
        {title}
      </h3>
      <ul style={{ margin: 0, padding: "0 0 0 16px", listStyle: "disc" }}>
        {items.map((item, i) => (
          <li key={i} style={{ color: COLORS.text, fontSize: 13, lineHeight: 1.6, marginBottom: 6 }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PostGamePage() {
  const navigate = useNavigate();
  const { report, loading, error, fetchReport, clearSnapshots } = usePostGame();

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleNewGame = async () => {
    await clearSnapshots();
    navigate("/");
  };

  if (loading) {
    return (
      <div style={{ background: COLORS.bg, minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: COLORS.muted, fontSize: 16 }}>경기 분석 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ background: COLORS.bg, minHeight: "100vh", padding: 32 }}>
        <p style={{ color: COLORS.red }}>{error}</p>
        <button
          onClick={handleNewGame}
          style={{ marginTop: 16, padding: "10px 24px", background: COLORS.teal, border: "none", borderRadius: 6, color: "#000", fontWeight: 700, cursor: "pointer" }}
        >
          새 경기 시작 →
        </button>
      </div>
    );
  }

  return (
    <div style={{ background: COLORS.bg, minHeight: "100vh", padding: 24, fontFamily: "sans-serif" }}>
      <h2 style={{ color: COLORS.teal, margin: "0 0 20px", fontSize: 20, fontWeight: 700 }}>
        경기 분석
      </h2>

      {report ? (
        <>
          {/* Top row: strengths + improvements */}
          <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
            <Section title="✅ 잘한 점" items={report.strengths} color={COLORS.teal} />
            <Section title="⚠️ 개선할 점" items={report.improvements} color={COLORS.red} />
          </div>

          {/* Key moments */}
          <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: 16, marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 12px", color: "#f0c040", fontSize: 14, fontWeight: 700 }}>
              ⚡ 핵심 순간들
            </h3>
            <ul style={{ margin: 0, padding: "0 0 0 16px" }}>
              {report.moments.map((m, i) => (
                <li key={i} style={{ color: COLORS.text, fontSize: 13, lineHeight: 1.6, marginBottom: 6 }}>
                  {m}
                </li>
              ))}
            </ul>
          </div>

          {/* Goals */}
          <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: 16, marginBottom: 24 }}>
            <h3 style={{ margin: "0 0 12px", color: COLORS.teal, fontSize: 14, fontWeight: 700 }}>
              🎯 다음 경기 집중 목표
            </h3>
            <ul style={{ margin: 0, padding: "0 0 0 16px" }}>
              {report.goals.map((g, i) => (
                <li key={i} style={{ color: COLORS.text, fontSize: 13, lineHeight: 1.6, marginBottom: 6 }}>
                  {g}
                </li>
              ))}
            </ul>
          </div>
        </>
      ) : (
        <p style={{ color: COLORS.muted }}>분석 데이터가 없습니다.</p>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          onClick={handleNewGame}
          style={{
            padding: "12px 32px",
            background: COLORS.teal,
            border: "none",
            borderRadius: 8,
            color: "#000",
            fontWeight: 700,
            fontSize: 15,
            cursor: "pointer",
          }}
        >
          새 경기 시작 →
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/draft/pages/PostGamePage.tsx
git commit -m "feat(postgame): add PostGamePage Screen 3"
```

---

## Task 6: Wire `/postgame` route + game-end navigation in `DraftApp.tsx`

**Files:**
- Modify: `frontend/src/draft/DraftApp.tsx`

`DraftApp.tsx` was created in Sub-project A. It contains a `HashRouter` with routes for `/` (DraftPage) and `/post-lock-in` (PostLockInPage). We add `/postgame` and listen for the `game_end` WebSocket event to auto-navigate.

- [ ] **Step 1: Read current `DraftApp.tsx`**

```bash
cat /Users/smk/Documents/GitHub/RiftBuddy/frontend/src/draft/DraftApp.tsx
```

- [ ] **Step 2: Add `/postgame` route and game-end listener**

Replace the contents of `DraftApp.tsx` with:

```tsx
// frontend/src/draft/DraftApp.tsx
import { HashRouter, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { DraftPage } from "./pages/DraftPage";
import { PostLockInPage } from "./pages/PostLockInPage";
import { PostGamePage } from "./pages/PostGamePage";

const WS_URL = (import.meta.env.VITE_RIFTBUDDY_WS_URL as string) ?? "ws://localhost:8000/ws";

function GameEndListener() {
  const navigate = useNavigate();

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}?token=bypass`);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string);
        if (msg.type === "game_end") {
          navigate("/postgame");
        }
      } catch {
        // ignore non-JSON
      }
    };
    return () => ws.close();
  }, [navigate]);

  return null;
}

export function DraftApp() {
  return (
    <HashRouter>
      <GameEndListener />
      <Routes>
        <Route path="/" element={<DraftPage />} />
        <Route path="/post-lock-in" element={<PostLockInPage />} />
        <Route path="/postgame" element={<PostGamePage />} />
      </Routes>
    </HashRouter>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Build frontend**

```bash
npm run build
```

Expected: build succeeds, `dist/draft.html` and `dist/index.html` both present.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/draft/DraftApp.tsx
git commit -m "feat(postgame): add /postgame route + game-end WebSocket listener"
```

---

## Task 7: Integration smoke test

**No new files — manual verification steps.**

- [ ] **Step 1: Run backend**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
RIFTBUDDY_BYPASS_AUTH=1 RIFTBUDDY_LLM_PROVIDER=mock uvicorn backend.main:app --reload
```

- [ ] **Step 2: Seed fake snapshots via curl**

```bash
curl -s -X POST http://localhost:8000/game/snapshot \
  -H "Content-Type: application/json" \
  -d '{"current_health":1500,"max_health":2000,"gold":3000,"level":9,"game_time":300.0,"champion_name":"Rumble","kills":2,"deaths":1,"assists":3,"creep_score":80,"recent_events":["DragonKill"]}' | python3 -m json.tool

curl -s -X POST http://localhost:8000/game/snapshot \
  -H "Content-Type: application/json" \
  -d '{"current_health":800,"max_health":2000,"gold":4200,"level":12,"game_time":900.0,"champion_name":"Rumble","kills":4,"deaths":2,"assists":5,"creep_score":130,"recent_events":["PlayerDied"]}' | python3 -m json.tool
```

Expected: `{"count": 1}`, then `{"count": 2}`.

- [ ] **Step 3: Call coach endpoint**

```bash
curl -s -X POST http://localhost:8000/postgame/coach | python3 -m json.tool
```

Expected: JSON with `strengths`, `improvements`, `moments`, `goals` keys. With mock LLM the response may be a placeholder — verify structure parses without 500 error.

- [ ] **Step 4: Clear snapshots**

```bash
curl -s -X DELETE http://localhost:8000/game/snapshots | python3 -m json.tool
```

Expected: `{"cleared": true}`.

- [ ] **Step 5: Verify Draft Window navigates to `/postgame`**

Start Electron dev:

```bash
npm run dev
```

Open Draft Window (`Cmd+Shift+D`). In another terminal, send a `game_end` event by simulating it via WebSocket or temporarily calling `_broadcast_game_end()` from a test endpoint. Verify the Draft Window automatically navigates to Screen 3 and shows loading state, then the coach report.

- [ ] **Step 6: Run full test suite**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
python -m pytest --tb=short -q
```

Expected: all tests pass (existing 30 + new ~10).

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "test(postgame): smoke test steps verified"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `POST /game/snapshot` → Task 2 + 3
- [x] `POST /postgame/coach` with structured JSON response → Task 2
- [x] `DELETE /game/snapshots` → Task 2
- [x] In-memory store, max 60 snapshots → Task 1
- [x] LLM prompt structure matches spec → Task 2, router.py
- [x] Screen 3 layout: strengths / improvements / moments / goals → Task 5
- [x] "새 경기 시작" clears snapshots + navigates to Screen 1 → Task 5 + 6
- [x] Game-end detection (Live Client 404) broadcasts `game_end` WS event → Task 3
- [x] Draft Window auto-navigates to `/postgame` on `game_end` → Task 6

**Type consistency:**
- `CoachReport` defined in `usePostGame.ts` — used only in `PostGamePage.tsx` via same import
- `GameSession` in `game_session.py` — used in `postgame/router.py` via `get_session()`
- `SnapshotPayload` Pydantic model matches `GameState` fields

**No placeholders:** All code blocks are complete.
