# Sub-project A: Draft Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a framed 1200×800 Draft Window to the Electron app with Screen 1 (draft phase analysis) and Screen 2 (post lock-in runes + team strategy), backed by new FastAPI endpoints proxying op.gg MCP.

**Architecture:** New Electron BrowserWindow (Draft Window) hosts its own React entrypoint (`draft.html` / `DraftApp.tsx`) with React Router for Screen 1/2 navigation. Backend gains a `backend/draft/` module with a FastAPI router mounted at `/draft` and an op.gg MCP HTTP client. LCU rune-apply gets its own router at `/lcu`. The existing overlay window and WebSocket loop are untouched.

**Tech Stack:** Electron 28, React 18, TypeScript, React Router v6, FastAPI, httpx (async), pytest, existing Groq/Anthropic LLM (`get_advice`).

---

## File Map

**Backend — create:**
- `backend/draft/__init__.py` — empty package marker
- `backend/draft/opgg_client.py` — async op.gg MCP calls with in-memory TTL cache
- `backend/draft/router.py` — FastAPI router: `/draft/champion-analysis`, `/draft/matchup`, `/draft/runes`, `/draft/team-strategy`
- `backend/lcu/__init__.py` — empty package marker
- `backend/lcu/router.py` — FastAPI router: `POST /lcu/apply-runes`
- `backend/tests/test_draft.py` — pytest tests for draft router + opgg_client
- `backend/tests/test_lcu.py` — pytest tests for lcu router

**Backend — modify:**
- `backend/main.py` — mount `draft_router` and `lcu_router`

**Frontend — create:**
- `frontend/src/draft/DraftApp.tsx` — React root for Draft Window (React Router provider)
- `frontend/src/draft/DraftRouter.tsx` — routes: `/` → Screen1, `/post-lock-in` → Screen2
- `frontend/src/draft/pages/DraftPage.tsx` — Screen 1: champion input + 3-panel analysis
- `frontend/src/draft/pages/PostLockInPage.tsx` — Screen 2: runes + team strategy + matchup + LCU button
- `frontend/src/draft/components/ChampionSlot.tsx` — single champion input slot with typeahead
- `frontend/src/draft/components/RecommendPanel.tsx` — top 5 role picks
- `frontend/src/draft/components/LaningPanel.tsx` — laning strength analysis
- `frontend/src/draft/components/SynergyPanel.tsx` — synergy/counter scores
- `frontend/src/draft/hooks/useDraftAnalysis.ts` — fetches `/draft/*` endpoints
- `frontend/src/draft/draft.html` — HTML entrypoint for Draft Window (Vite entry)
- `frontend/src/draft/draft-main.tsx` — Vite entry calling `ReactDOM.createRoot`

**Frontend — modify:**
- `frontend/vite.config.ts` — add `draft.html` as second Vite input
- `frontend/electron/main.ts` — create Draft Window on startup, add `Cmd+Shift+D` hotkey, add draft-specific preload events
- `frontend/electron/preload.ts` — expose draft IPC events

---

## Task 1: Backend — op.gg MCP client

**Files:**
- Create: `backend/draft/__init__.py`
- Create: `backend/draft/opgg_client.py`
- Create: `backend/tests/test_draft.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_draft.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_champion_analysis_returns_data():
    mock_response = {"win_rate": 52.3, "tier": "A", "counters": [], "synergies": [], "recommended_builds": []}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response):
        from backend.draft.opgg_client import get_champion_analysis
        result = await get_champion_analysis("Rumble", "TOP")
    assert result["win_rate"] == 52.3
    assert "tier" in result

@pytest.mark.asyncio
async def test_get_champion_analysis_cache_hit():
    """Second call with same args should NOT call _call_opgg_mcp again."""
    from backend.draft.opgg_client import _cache, get_champion_analysis
    _cache.clear()
    mock_response = {"win_rate": 50.0}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response) as mock_call:
        await get_champion_analysis("Garen", "TOP")
        await get_champion_analysis("Garen", "TOP")
    assert mock_call.call_count == 1

@pytest.mark.asyncio
async def test_get_matchup_returns_data():
    mock_response = {"laning_strength": 55.0, "early_advantage": "good", "tips": ["trade at level 3"]}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response):
        from backend.draft.opgg_client import get_matchup
        result = await get_matchup("Rumble", "Darius", "TOP")
    assert result["laning_strength"] == 55.0

@pytest.mark.asyncio
async def test_get_runes_returns_data():
    mock_response = {"primary_path": "Precision", "primary_runes": [8005, 9101], "secondary_path": "Sorcery", "secondary_runes": [8234, 8210], "shards": [5005, 5002, 5001]}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response):
        from backend.draft.opgg_client import get_runes
        result = await get_runes("Rumble", "TOP")
    assert result["primary_path"] == "Precision"
    assert len(result["shards"]) == 3
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
python -m pytest backend/tests/test_draft.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'backend.draft'`

- [ ] **Step 3: Create package marker**

```python
# backend/draft/__init__.py
```

- [ ] **Step 4: Implement op.gg MCP client**

```python
# backend/draft/opgg_client.py
import time
from typing import Any

import httpx

OPGG_MCP_URL = "https://mcp-api.op.gg/mcp"
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 600  # 10 minutes


async def _call_opgg_mcp(tool: str, arguments: dict) -> dict:
    """
    Calls op.gg MCP API. Implementer: verify the exact request format at
    https://github.com/opgginc/opgg-mcp before shipping.
    The pattern below follows the standard MCP HTTP/SSE JSON-RPC envelope.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(OPGG_MCP_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    # MCP result is nested under result.content[0].text (JSON string) or result directly
    result = data.get("result", data)
    if isinstance(result, dict) and "content" in result:
        import json as _json
        content = result["content"]
        if isinstance(content, list) and content:
            raw = content[0].get("text", "{}")
            return _json.loads(raw) if isinstance(raw, str) else raw
    return result


def _cache_key(tool: str, **kwargs) -> str:
    return f"{tool}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"


def _get_cached(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _set_cached(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


async def get_champion_analysis(champion: str, role: str) -> dict:
    key = _cache_key("lol_get_champion_analysis", champion=champion, role=role)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_get_champion_analysis", {"champion_name": champion, "position": role})
    _set_cached(key, result)
    return result


async def get_matchup(my_champion: str, enemy_champion: str, role: str) -> dict:
    key = _cache_key("lol_get_lane_matchup_guide", my=my_champion, enemy=enemy_champion, role=role)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp(
        "lol_get_lane_matchup_guide",
        {"champion_name": my_champion, "opponent_champion_name": enemy_champion, "position": role},
    )
    _set_cached(key, result)
    return result


async def get_runes(champion: str, role: str) -> dict:
    key = _cache_key("lol_get_champion_analysis_runes", champion=champion, role=role)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    # Rune data comes from champion analysis; extract rune fields
    analysis = await get_champion_analysis(champion, role)
    runes = analysis.get("runes", {})
    result = {
        "primary_path": runes.get("primary_path", ""),
        "primary_runes": runes.get("primary_runes", []),
        "secondary_path": runes.get("secondary_path", ""),
        "secondary_runes": runes.get("secondary_runes", []),
        "shards": runes.get("shards", []),
    }
    _set_cached(key, result)
    return result


async def list_meta_champions(role: str) -> list[dict]:
    key = _cache_key("lol_list_lane_meta_champions", role=role)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_list_lane_meta_champions", {"position": role})
    champions = result if isinstance(result, list) else result.get("champions", [])
    _set_cached(key, champions)
    return champions
```

- [ ] **Step 5: Run tests — expect pass**

```bash
python -m pytest backend/tests/test_draft.py -v
```

Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/draft/__init__.py backend/draft/opgg_client.py backend/tests/test_draft.py
git commit -m "feat: add op.gg MCP client with TTL cache"
```

---

## Task 2: Backend — draft router

**Files:**
- Create: `backend/draft/router.py`
- Modify: `backend/tests/test_draft.py` (add router tests)
- Modify: `backend/main.py` (mount router)

- [ ] **Step 1: Add router tests**

Append to `backend/tests/test_draft.py`:

```python
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

def _make_client():
    from backend.main import app
    return TestClient(app)

def test_draft_champion_analysis_endpoint():
    mock_data = {"win_rate": 52.0, "tier": "A", "counters": [], "synergies": [], "recommended_builds": []}
    with patch("backend.draft.opgg_client.get_champion_analysis", new_callable=AsyncMock, return_value=mock_data):
        client = _make_client()
        response = client.get("/draft/champion-analysis?champion=Rumble&role=TOP")
    assert response.status_code == 200
    assert response.json()["win_rate"] == 52.0

def test_draft_matchup_endpoint():
    mock_data = {"laning_strength": 55.0, "tips": []}
    with patch("backend.draft.opgg_client.get_matchup", new_callable=AsyncMock, return_value=mock_data):
        client = _make_client()
        response = client.get("/draft/matchup?my_champion=Rumble&enemy_champion=Darius&role=TOP")
    assert response.status_code == 200
    assert response.json()["laning_strength"] == 55.0

def test_draft_runes_endpoint():
    mock_data = {"primary_path": "Precision", "primary_runes": [], "secondary_path": "Sorcery", "secondary_runes": [], "shards": []}
    with patch("backend.draft.opgg_client.get_runes", new_callable=AsyncMock, return_value=mock_data):
        client = _make_client()
        response = client.get("/draft/runes?champion=Rumble&role=TOP")
    assert response.status_code == 200
    assert response.json()["primary_path"] == "Precision"

def test_draft_team_strategy_endpoint():
    with patch("backend.llm.advisor.get_advice", new_callable=AsyncMock, return_value="팀 전략: 후반 팀파이트를 노려라"):
        client = _make_client()
        body = {
            "ally": ["Rumble", "Vi", "Syndra", "Jinx", "Lulu"],
            "enemy": ["Darius", "Hecarim", "Zed", "Caitlyn", "Thresh"],
            "my_champion": "Rumble",
            "my_role": "TOP",
        }
        response = client.post("/draft/team-strategy", json=body)
    assert response.status_code == 200
    assert "strategy" in response.json()

def test_draft_meta_champions_endpoint():
    mock_data = [{"champion": "Rumble", "win_rate": 52.0, "tier": "A"}]
    with patch("backend.draft.opgg_client.list_meta_champions", new_callable=AsyncMock, return_value=mock_data):
        client = _make_client()
        response = client.get("/draft/meta-champions?role=TOP")
    assert response.status_code == 200
    assert len(response.json()) == 1
```

- [ ] **Step 2: Run tests — expect failures**

```bash
python -m pytest backend/tests/test_draft.py::test_draft_champion_analysis_endpoint -v
```

Expected: FAIL — router not mounted

- [ ] **Step 3: Create draft router**

```python
# backend/draft/router.py
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.draft.opgg_client import get_champion_analysis, get_matchup, get_runes, list_meta_champions
from backend.llm.advisor import get_advice
from backend.context.engine import ContextPacket

router = APIRouter(prefix="/draft", tags=["draft"])


class TeamStrategyRequest(BaseModel):
    ally: list[str]
    enemy: list[str]
    my_champion: str
    my_role: str


@router.get("/champion-analysis")
async def champion_analysis(champion: str = Query(...), role: str = Query(...)):
    try:
        return await get_champion_analysis(champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.get("/matchup")
async def matchup(
    my_champion: str = Query(...),
    enemy_champion: str = Query(...),
    role: str = Query(...),
):
    try:
        return await get_matchup(my_champion, enemy_champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.get("/runes")
async def runes(champion: str = Query(...), role: str = Query(...)):
    try:
        return await get_runes(champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.get("/meta-champions")
async def meta_champions(role: str = Query(...)):
    try:
        return await list_meta_champions(role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.post("/team-strategy")
async def team_strategy(body: TeamStrategyRequest):
    prompt = (
        f"아군 팀: {', '.join(body.ally)}\n"
        f"상대 팀: {', '.join(body.enemy)}\n"
        f"내 챔피언: {body.my_champion} ({body.my_role})\n\n"
        "이 드래프트의 승리 조건, 초반 우선순위, 핵심 스파이크, 전체 유불리를 2-3문장 한국어로 분석해줘."
    )
    # Build a minimal ContextPacket (no live game — draft phase)
    packet = ContextPacket(
        health_percent=100.0,
        gold=0.0,
        level=1,
        game_time_minutes=0.0,
        summary=f"Draft analysis request. My champion: {body.my_champion} {body.my_role}.",
    )
    try:
        advice = await get_advice(packet, user_query=prompt, language="ko")
        return {"strategy": advice}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
```

- [ ] **Step 4: Mount router in main.py**

Edit `backend/main.py` — add after existing imports and before `app = FastAPI(...)`:

```python
from backend.draft.router import router as draft_router
```

And after `app = FastAPI(title="RiftBuddy Backend")`:

```python
app.include_router(draft_router)
```

- [ ] **Step 5: Run all draft tests**

```bash
python -m pytest backend/tests/test_draft.py -v
```

Expected: `9 passed` (4 opgg_client + 5 router)

- [ ] **Step 6: Commit**

```bash
git add backend/draft/router.py backend/tests/test_draft.py backend/main.py
git commit -m "feat: add draft FastAPI router with op.gg MCP endpoints"
```

---

## Task 3: Backend — LCU rune-apply endpoint

**Files:**
- Create: `backend/lcu/__init__.py`
- Create: `backend/lcu/router.py`
- Create: `backend/tests/test_lcu.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_lcu.py
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from fastapi.testclient import TestClient


def _client():
    from backend.main import app
    return TestClient(app)


def test_apply_runes_success():
    mock_lockfile_content = "LeagueClient:12345:62345:test-password:https"
    rune_page = {
        "name": "RiftBuddy — Rumble TOP",
        "primaryStyleId": 8100,
        "subStyleId": 8300,
        "selectedPerkIds": [8112, 8143, 8138, 8135, 8304, 8345, 5007, 5002, 5001],
        "current": True,
    }
    with patch("builtins.open", mock_open(read_data=mock_lockfile_content)), \
         patch("backend.lcu.router._get_current_page_id", new_callable=AsyncMock, return_value=42), \
         patch("backend.lcu.router._delete_page", new_callable=AsyncMock), \
         patch("backend.lcu.router._create_page", new_callable=AsyncMock):
        response = _client().post("/lcu/apply-runes", json=rune_page)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_apply_runes_lockfile_not_found():
    rune_page = {
        "name": "RiftBuddy — Test",
        "primaryStyleId": 8100,
        "subStyleId": 8300,
        "selectedPerkIds": [8112, 8143, 8138, 8135, 8304, 8345, 5007, 5002, 5001],
        "current": True,
    }
    with patch("builtins.open", side_effect=FileNotFoundError):
        response = _client().post("/lcu/apply-runes", json=rune_page)
    assert response.status_code == 503
    assert "lockfile" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run — expect failures**

```bash
python -m pytest backend/tests/test_lcu.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Create LCU package and router**

```python
# backend/lcu/__init__.py
```

```python
# backend/lcu/router.py
import base64
import platform
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/lcu", tags=["lcu"])

LOCKFILE_PATHS = {
    "Darwin": Path("/Applications/League of Legends.app/Contents/LoL/lockfile"),
    "Windows": Path("C:/Riot Games/League of Legends/lockfile"),
}


class RunePage(BaseModel):
    name: str
    primaryStyleId: int
    subStyleId: int
    selectedPerkIds: list[int]
    current: bool = True


def _read_lockfile() -> tuple[int, str]:
    """Returns (port, password) from League lockfile."""
    path = LOCKFILE_PATHS.get(platform.system())
    if path is None:
        raise FileNotFoundError("Unsupported platform for LCU lockfile detection")
    content = open(path).read()
    # Format: ProcessName:PID:Port:Password:Protocol
    parts = content.strip().split(":")
    port = int(parts[2])
    password = parts[3]
    return port, password


def _lcu_headers(password: str) -> dict:
    token = base64.b64encode(f"riot:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


async def _get_current_page_id(base_url: str, headers: dict) -> Optional[int]:
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        response = await client.get(f"{base_url}/lol-perks/v1/currentpage", headers=headers)
        if response.status_code == 200:
            return response.json().get("id")
    return None


async def _delete_page(base_url: str, headers: dict, page_id: int) -> None:
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        await client.delete(f"{base_url}/lol-perks/v1/pages/{page_id}", headers=headers)


async def _create_page(base_url: str, headers: dict, rune_page: RunePage) -> None:
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        response = await client.post(
            f"{base_url}/lol-perks/v1/pages",
            headers=headers,
            json=rune_page.model_dump(by_alias=False),
        )
        response.raise_for_status()


@router.post("/apply-runes")
async def apply_runes(rune_page: RunePage):
    try:
        port, password = _read_lockfile()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"League lockfile not found: {exc}. Is League running?")

    base_url = f"https://127.0.0.1:{port}"
    headers = _lcu_headers(password)

    try:
        page_id = await _get_current_page_id(base_url, headers)
        if page_id is not None:
            await _delete_page(base_url, headers, page_id)
        await _create_page(base_url, headers, rune_page)
        return {"success": True, "message": "룬이 적용되었습니다 ✓"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LCU API error: {exc}")
```

- [ ] **Step 4: Mount LCU router in main.py**

Add to `backend/main.py` after draft_router import:

```python
from backend.lcu.router import router as lcu_router
```

And after `app.include_router(draft_router)`:

```python
app.include_router(lcu_router)
```

- [ ] **Step 5: Run LCU tests**

```bash
python -m pytest backend/tests/test_lcu.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/lcu/__init__.py backend/lcu/router.py backend/tests/test_lcu.py backend/main.py
git commit -m "feat: add LCU rune auto-apply endpoint"
```

---

## Task 4: Frontend — Vite multi-entry + Draft HTML

**Files:**
- Create: `frontend/src/draft/draft.html`
- Create: `frontend/src/draft/draft-main.tsx`
- Create: `frontend/src/draft/DraftApp.tsx`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Read existing vite config**

```bash
cat /Users/smk/Documents/GitHub/RiftBuddy/frontend/vite.config.ts
```

- [ ] **Step 2: Create draft HTML entrypoint**

```html
<!-- frontend/src/draft/draft.html -->
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RiftBuddy Draft</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { background: #0f1117; color: #e8e8e8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    </style>
  </head>
  <body>
    <div id="draft-root"></div>
    <script type="module" src="./draft-main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Create draft React entrypoint**

```tsx
// frontend/src/draft/draft-main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { DraftApp } from "./DraftApp";

ReactDOM.createRoot(document.getElementById("draft-root")!).render(
  <React.StrictMode>
    <DraftApp />
  </React.StrictMode>
);
```

- [ ] **Step 4: Create DraftApp with React Router**

```tsx
// frontend/src/draft/DraftApp.tsx
import { HashRouter, Route, Routes } from "react-router-dom";
import { DraftPage } from "./pages/DraftPage";
import { PostLockInPage } from "./pages/PostLockInPage";

export function DraftApp() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<DraftPage />} />
        <Route path="/post-lock-in" element={<PostLockInPage />} />
      </Routes>
    </HashRouter>
  );
}
```

- [ ] **Step 5: Add react-router-dom dependency**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npm install react-router-dom
```

- [ ] **Step 6: Update vite.config.ts for multi-entry**

Read current config first, then update the `build.rollupOptions.input` to include both entry points. The existing config likely has a single entry. Replace the entire `build` section to:

```typescript
// Add to vite.config.ts build section:
build: {
  rollupOptions: {
    input: {
      main: resolve(__dirname, "index.html"),
      draft: resolve(__dirname, "src/draft/draft.html"),
    },
  },
},
```

Also add at the top of the file: `import { resolve } from "path";`

- [ ] **Step 7: Verify build compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds with two entry points

- [ ] **Step 8: Commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add frontend/src/draft/draft.html frontend/src/draft/draft-main.tsx frontend/src/draft/DraftApp.tsx frontend/vite.config.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: add Draft Window Vite entry point and React Router setup"
```

---

## Task 5: Frontend — useDraftAnalysis hook

**Files:**
- Create: `frontend/src/draft/hooks/useDraftAnalysis.ts`

- [ ] **Step 1: Create hook**

```typescript
// frontend/src/draft/hooks/useDraftAnalysis.ts
import { useCallback, useState } from "react";

const API_BASE = (import.meta.env.VITE_RIFTBUDDY_API_URL as string | undefined) ?? "http://localhost:8001";

export interface ChampionAnalysis {
  win_rate?: number;
  tier?: string;
  counters?: string[];
  synergies?: string[];
  recommended_builds?: string[];
}

export interface Matchup {
  laning_strength?: number;
  early_advantage?: string;
  mid_advantage?: string;
  late_advantage?: string;
  tips?: string[];
}

export interface RuneData {
  primary_path?: string;
  primary_runes?: number[];
  secondary_path?: string;
  secondary_runes?: number[];
  shards?: number[];
}

export interface MetaChampion {
  champion: string;
  win_rate?: number;
  tier?: string;
}

export function useDraftAnalysis() {
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  const fetchJson = useCallback(async (url: string): Promise<unknown> => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }, []);

  const getChampionAnalysis = useCallback(
    async (champion: string, role: string): Promise<ChampionAnalysis> => {
      const key = `analysis-${champion}-${role}`;
      setLoading((l) => ({ ...l, [key]: true }));
      setError(null);
      try {
        const data = await fetchJson(
          `${API_BASE}/draft/champion-analysis?champion=${encodeURIComponent(champion)}&role=${encodeURIComponent(role)}`
        );
        return data as ChampionAnalysis;
      } catch (e) {
        setError("데이터를 불러올 수 없습니다");
        return {};
      } finally {
        setLoading((l) => ({ ...l, [key]: false }));
      }
    },
    [fetchJson]
  );

  const getMatchup = useCallback(
    async (myChampion: string, enemyChampion: string, role: string): Promise<Matchup> => {
      const key = `matchup-${myChampion}-${enemyChampion}`;
      setLoading((l) => ({ ...l, [key]: true }));
      setError(null);
      try {
        const data = await fetchJson(
          `${API_BASE}/draft/matchup?my_champion=${encodeURIComponent(myChampion)}&enemy_champion=${encodeURIComponent(enemyChampion)}&role=${encodeURIComponent(role)}`
        );
        return data as Matchup;
      } catch (e) {
        setError("매치업 데이터를 불러올 수 없습니다");
        return {};
      } finally {
        setLoading((l) => ({ ...l, [key]: false }));
      }
    },
    [fetchJson]
  );

  const getRunes = useCallback(
    async (champion: string, role: string): Promise<RuneData> => {
      setLoading((l) => ({ ...l, runes: true }));
      setError(null);
      try {
        const data = await fetchJson(
          `${API_BASE}/draft/runes?champion=${encodeURIComponent(champion)}&role=${encodeURIComponent(role)}`
        );
        return data as RuneData;
      } catch (e) {
        setError("룬 데이터를 불러올 수 없습니다");
        return {};
      } finally {
        setLoading((l) => ({ ...l, runes: false }));
      }
    },
    [fetchJson]
  );

  const getMetaChampions = useCallback(
    async (role: string): Promise<MetaChampion[]> => {
      setLoading((l) => ({ ...l, meta: true }));
      setError(null);
      try {
        const data = await fetchJson(`${API_BASE}/draft/meta-champions?role=${encodeURIComponent(role)}`);
        return data as MetaChampion[];
      } catch (e) {
        setError("메타 데이터를 불러올 수 없습니다");
        return [];
      } finally {
        setLoading((l) => ({ ...l, meta: false }));
      }
    },
    [fetchJson]
  );

  const getTeamStrategy = useCallback(
    async (ally: string[], enemy: string[], myChampion: string, myRole: string): Promise<string> => {
      setLoading((l) => ({ ...l, strategy: true }));
      setError(null);
      try {
        const response = await fetch(`${API_BASE}/draft/team-strategy`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ally, enemy, my_champion: myChampion, my_role: myRole }),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        return (data as { strategy: string }).strategy;
      } catch (e) {
        setError("팀 전략을 불러올 수 없습니다");
        return "";
      } finally {
        setLoading((l) => ({ ...l, strategy: false }));
      }
    },
    []
  );

  const applyRunes = useCallback(async (runePage: {
    name: string;
    primaryStyleId: number;
    subStyleId: number;
    selectedPerkIds: number[];
    current: boolean;
  }): Promise<{ success: boolean; message: string }> => {
    const response = await fetch(`${API_BASE}/lcu/apply-runes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(runePage),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail ?? "LCU error");
    return data as { success: boolean; message: string };
  }, []);

  const isLoading = useCallback((key: string) => loading[key] === true, [loading]);

  return { getChampionAnalysis, getMatchup, getRunes, getMetaChampions, getTeamStrategy, applyRunes, isLoading, error };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add frontend/src/draft/hooks/useDraftAnalysis.ts
git commit -m "feat: add useDraftAnalysis hook for draft API calls"
```

---

## Task 6: Frontend — ChampionSlot component

**Files:**
- Create: `frontend/src/draft/components/ChampionSlot.tsx`

- [ ] **Step 1: Create component**

```tsx
// frontend/src/draft/components/ChampionSlot.tsx
import { useState } from "react";

const DDRAGON_BASE = "https://ddragon.leagueoflegends.com/cdn/14.9.1/img/champion";

interface Props {
  value: string;
  onChange: (name: string) => void;
  placeholder?: string;
  team: "ally" | "enemy";
}

export function ChampionSlot({ value, onChange, placeholder = "챔피언", team }: Props) {
  const [input, setInput] = useState(value);

  const borderColor = team === "ally" ? "#00c8a0" : "#e84057";
  const iconUrl = value ? `${DDRAGON_BASE}/${value}.png` : null;

  const handleBlur = () => {
    onChange(input.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      onChange(input.trim());
      (e.target as HTMLInputElement).blur();
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, width: 80 }}>
      <div
        style={{
          width: 52,
          height: 52,
          borderRadius: 6,
          border: `2px solid ${borderColor}`,
          background: "#1a1d24",
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {iconUrl ? (
          <img src={iconUrl} alt={value} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          <span style={{ fontSize: 22, opacity: 0.3 }}>?</span>
        )}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        style={{
          width: 76,
          fontSize: 11,
          padding: "2px 4px",
          background: "#1a1d24",
          border: `1px solid ${borderColor}40`,
          borderRadius: 4,
          color: "#e8e8e8",
          textAlign: "center",
        }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add frontend/src/draft/components/ChampionSlot.tsx
git commit -m "feat: add ChampionSlot component with DDragon icon"
```

---

## Task 7: Frontend — Analysis panel components

**Files:**
- Create: `frontend/src/draft/components/RecommendPanel.tsx`
- Create: `frontend/src/draft/components/LaningPanel.tsx`
- Create: `frontend/src/draft/components/SynergyPanel.tsx`

- [ ] **Step 1: Create RecommendPanel**

```tsx
// frontend/src/draft/components/RecommendPanel.tsx
import type { MetaChampion } from "../hooks/useDraftAnalysis";

const DDRAGON_BASE = "https://ddragon.leagueoflegends.com/cdn/14.9.1/img/champion";

interface Props {
  champions: MetaChampion[];
  loading: boolean;
}

export function RecommendPanel({ champions, loading }: Props) {
  const tierColor = (tier?: string) => {
    if (tier === "S") return "#f0c040";
    if (tier === "A") return "#00c8a0";
    if (tier === "B") return "#7ea8c9";
    return "#888";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h3 style={{ fontSize: 12, color: "#00c8a0", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>
        추천 픽
      </h3>
      {loading && <span style={{ fontSize: 12, color: "#666" }}>불러오는 중...</span>}
      {!loading && champions.length === 0 && (
        <span style={{ fontSize: 12, color: "#666" }}>포지션을 선택하면 추천 픽이 표시됩니다.</span>
      )}
      {champions.slice(0, 5).map((champ) => (
        <div
          key={champ.champion}
          style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}
        >
          <img
            src={`${DDRAGON_BASE}/${champ.champion}.png`}
            alt={champ.champion}
            style={{ width: 32, height: 32, borderRadius: 4, border: "1px solid #333" }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{champ.champion}</div>
            <div style={{ fontSize: 11, color: "#aaa" }}>승률 {champ.win_rate?.toFixed(1) ?? "-"}%</div>
          </div>
          <span style={{ fontSize: 11, fontWeight: 700, color: tierColor(champ.tier) }}>{champ.tier ?? "-"}</span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create LaningPanel**

```tsx
// frontend/src/draft/components/LaningPanel.tsx
import type { Matchup } from "../hooks/useDraftAnalysis";

interface Props {
  matchup: Matchup | null;
  myChampion: string;
  enemyChampion: string;
  loading: boolean;
}

export function LaningPanel({ matchup, myChampion, enemyChampion, loading }: Props) {
  if (!myChampion || !enemyChampion) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <h3 style={{ fontSize: 12, color: "#00c8a0", textTransform: "uppercase", letterSpacing: 1 }}>라인전 분석</h3>
        <span style={{ fontSize: 12, color: "#666" }}>내 챔피언과 상대 라이너를 입력하면 분석이 표시됩니다.</span>
      </div>
    );
  }

  const strengthColor = (val?: number) => {
    if (!val) return "#888";
    if (val >= 55) return "#00c8a0";
    if (val >= 45) return "#f0c040";
    return "#e84057";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h3 style={{ fontSize: 12, color: "#00c8a0", textTransform: "uppercase", letterSpacing: 1 }}>라인전 분석</h3>
      <div style={{ fontSize: 13, color: "#aaa" }}>
        {myChampion} <span style={{ color: "#555" }}>vs</span> {enemyChampion}
      </div>
      {loading && <span style={{ fontSize: 12, color: "#666" }}>분석 중...</span>}
      {!loading && matchup && (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {[
              { label: "전체 강도", value: matchup.laning_strength },
              { label: "초반", value: matchup.early_advantage === "good" ? 60 : matchup.early_advantage === "bad" ? 40 : 50 },
            ].map(({ label, value }) => (
              <div key={label} style={{ background: "#1a1d24", borderRadius: 6, padding: "6px 10px", minWidth: 80 }}>
                <div style={{ fontSize: 10, color: "#888", marginBottom: 2 }}>{label}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: strengthColor(value) }}>
                  {typeof value === "number" ? `${value.toFixed(0)}%` : value ?? "-"}
                </div>
              </div>
            ))}
          </div>
          {matchup.tips && matchup.tips.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>팁</div>
              {matchup.tips.map((tip, i) => (
                <div key={i} style={{ fontSize: 12, color: "#c8c8c8", marginBottom: 3 }}>• {tip}</div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create SynergyPanel**

```tsx
// frontend/src/draft/components/SynergyPanel.tsx
import type { ChampionAnalysis } from "../hooks/useDraftAnalysis";

const DDRAGON_BASE = "https://ddragon.leagueoflegends.com/cdn/14.9.1/img/champion";

interface Props {
  myAnalysis: ChampionAnalysis | null;
  loading: boolean;
}

export function SynergyPanel({ myAnalysis, loading }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h3 style={{ fontSize: 12, color: "#00c8a0", textTransform: "uppercase", letterSpacing: 1 }}>시너지 / 카운터</h3>
      {loading && <span style={{ fontSize: 12, color: "#666" }}>분석 중...</span>}
      {!loading && !myAnalysis && (
        <span style={{ fontSize: 12, color: "#666" }}>내 챔피언을 입력하면 표시됩니다.</span>
      )}
      {!loading && myAnalysis && (
        <>
          {myAnalysis.synergies && myAnalysis.synergies.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: "#00c8a0", marginBottom: 4 }}>같이 하면 좋은 챔피언</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {myAnalysis.synergies.slice(0, 5).map((champ) => (
                  <div key={champ} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                    <img
                      src={`${DDRAGON_BASE}/${champ}.png`}
                      alt={champ}
                      style={{ width: 28, height: 28, borderRadius: 4, border: "1px solid #00c8a040" }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    <span style={{ fontSize: 9, color: "#aaa" }}>{champ}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {myAnalysis.counters && myAnalysis.counters.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, color: "#e84057", marginBottom: 4 }}>카운터</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {myAnalysis.counters.slice(0, 5).map((champ) => (
                  <div key={champ} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                    <img
                      src={`${DDRAGON_BASE}/${champ}.png`}
                      alt={champ}
                      style={{ width: 28, height: 28, borderRadius: 4, border: "1px solid #e8405740" }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    <span style={{ fontSize: 9, color: "#aaa" }}>{champ}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 5: Commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add frontend/src/draft/components/
git commit -m "feat: add draft analysis panel components"
```

---

## Task 8: Frontend — Screen 1 DraftPage

**Files:**
- Create: `frontend/src/draft/pages/DraftPage.tsx`

- [ ] **Step 1: Create DraftPage**

```tsx
// frontend/src/draft/pages/DraftPage.tsx
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ChampionSlot } from "../components/ChampionSlot";
import { LaningPanel } from "../components/LaningPanel";
import { RecommendPanel } from "../components/RecommendPanel";
import { SynergyPanel } from "../components/SynergyPanel";
import { useDraftAnalysis } from "../hooks/useDraftAnalysis";
import type { ChampionAnalysis, Matchup, MetaChampion } from "../hooks/useDraftAnalysis";

const ROLES = ["TOP", "JG", "MID", "BOT", "SUP"] as const;
type Role = (typeof ROLES)[number];

const ROLE_LABELS: Record<Role, string> = { TOP: "탑", JG: "정글", MID: "미드", BOT: "바텀", SUP: "서폿" };

const EMPTY_FIVE = ["", "", "", "", ""] as const;

export function DraftPage() {
  const navigate = useNavigate();
  const { getChampionAnalysis, getMatchup, getMetaChampions, isLoading, error } = useDraftAnalysis();

  const [role, setRole] = useState<Role>("TOP");
  const [myIndex, setMyIndex] = useState(0); // which ally slot is "me"
  const [ally, setAlly] = useState<string[]>([...EMPTY_FIVE]);
  const [enemy, setEnemy] = useState<string[]>([...EMPTY_FIVE]);
  const [metaChamps, setMetaChamps] = useState<MetaChampion[]>([]);
  const [myAnalysis, setMyAnalysis] = useState<ChampionAnalysis | null>(null);
  const [matchup, setMatchup] = useState<Matchup | null>(null);

  // Fetch meta champions when role changes
  useEffect(() => {
    getMetaChampions(role).then(setMetaChamps);
  }, [role, getMetaChampions]);

  // Fetch my champion analysis when my champion slot changes
  useEffect(() => {
    const myChamp = ally[myIndex];
    if (myChamp) {
      getChampionAnalysis(myChamp, role).then(setMyAnalysis);
    } else {
      setMyAnalysis(null);
    }
  }, [ally, myIndex, role, getChampionAnalysis]);

  // Fetch matchup when my champion and the first enemy lane opponent are set
  useEffect(() => {
    const myChamp = ally[myIndex];
    const enemyLaner = enemy[myIndex]; // same position index as mine
    if (myChamp && enemyLaner) {
      getMatchup(myChamp, enemyLaner, role).then(setMatchup);
    } else {
      setMatchup(null);
    }
  }, [ally, enemy, myIndex, role, getMatchup]);

  const updateAlly = useCallback((index: number, name: string) => {
    setAlly((prev) => prev.map((v, i) => (i === index ? name : v)));
  }, []);

  const updateEnemy = useCallback((index: number, name: string) => {
    setEnemy((prev) => prev.map((v, i) => (i === index ? name : v)));
  }, []);

  const filledCount = ally.filter(Boolean).length + enemy.filter(Boolean).length;
  const canProceed = filledCount >= 2; // at least my champ + one enemy

  const handleProceed = () => {
    navigate("/post-lock-in", {
      state: { ally, enemy, myChampion: ally[myIndex], myRole: role },
    });
  };

  return (
    <div style={{ width: "100%", height: "100vh", background: "#0f1117", display: "flex", flexDirection: "column" }}>
      {/* Header: champion slots */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", background: "#141720", borderBottom: "1px solid #1e2130" }}>
        <div style={{ display: "flex", gap: 8 }}>
          {ally.map((champ, i) => (
            <div key={i} style={{ position: "relative" }}>
              <ChampionSlot value={champ} onChange={(name) => updateAlly(i, name)} team="ally" placeholder={`아군 ${i + 1}`} />
              <button
                onClick={() => setMyIndex(i)}
                style={{
                  position: "absolute",
                  top: -6,
                  right: -6,
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: myIndex === i ? "#00c8a0" : "#333",
                  border: "none",
                  cursor: "pointer",
                  fontSize: 9,
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                title="내 챔피언으로 설정"
              >
                {myIndex === i ? "나" : i + 1}
              </button>
            </div>
          ))}
        </div>

        <span style={{ color: "#555", fontWeight: 700, fontSize: 16 }}>VS</span>

        <div style={{ display: "flex", gap: 8 }}>
          {enemy.map((champ, i) => (
            <ChampionSlot key={i} value={champ} onChange={(name) => updateEnemy(i, name)} team="enemy" placeholder={`상대 ${i + 1}`} />
          ))}
        </div>
      </div>

      {/* Role selector */}
      <div style={{ display: "flex", gap: 8, padding: "8px 24px", background: "#141720", borderBottom: "1px solid #1e2130" }}>
        {ROLES.map((r) => (
          <button
            key={r}
            onClick={() => setRole(r)}
            style={{
              padding: "4px 12px",
              borderRadius: 4,
              border: "1px solid",
              borderColor: role === r ? "#00c8a0" : "#333",
              background: role === r ? "#00c8a010" : "transparent",
              color: role === r ? "#00c8a0" : "#888",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            {ROLE_LABELS[r]}
          </button>
        ))}
        {error && <span style={{ marginLeft: "auto", fontSize: 11, color: "#e84057" }}>{error}</span>}
      </div>

      {/* Main 3-panel layout */}
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "25% 45% 30%", overflow: "hidden" }}>
        {/* Recommendations */}
        <div style={{ padding: 16, borderRight: "1px solid #1e2130", overflowY: "auto" }}>
          <RecommendPanel champions={metaChamps} loading={isLoading("meta")} />
        </div>

        {/* Laning Analysis */}
        <div style={{ padding: 16, borderRight: "1px solid #1e2130", overflowY: "auto" }}>
          <LaningPanel
            matchup={matchup}
            myChampion={ally[myIndex]}
            enemyChampion={enemy[myIndex]}
            loading={isLoading(`matchup-${ally[myIndex]}-${enemy[myIndex]}`)}
          />
        </div>

        {/* Synergy/Counter */}
        <div style={{ padding: 16, overflowY: "auto" }}>
          <SynergyPanel
            myAnalysis={myAnalysis}
            loading={isLoading(`analysis-${ally[myIndex]}-${role}`)}
          />
        </div>
      </div>

      {/* Footer */}
      <div style={{ display: "flex", justifyContent: "flex-end", padding: "12px 24px", background: "#141720", borderTop: "1px solid #1e2130" }}>
        <button
          onClick={handleProceed}
          disabled={!canProceed}
          style={{
            padding: "8px 24px",
            background: canProceed ? "#00c8a0" : "#333",
            color: canProceed ? "#0f1117" : "#666",
            border: "none",
            borderRadius: 6,
            cursor: canProceed ? "pointer" : "not-allowed",
            fontWeight: 700,
            fontSize: 14,
          }}
        >
          분석 완료 →
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npx tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 3: Commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add frontend/src/draft/pages/DraftPage.tsx
git commit -m "feat: add Screen 1 DraftPage with 3-panel layout"
```

---

## Task 9: Frontend — Screen 2 PostLockInPage

**Files:**
- Create: `frontend/src/draft/pages/PostLockInPage.tsx`

- [ ] **Step 1: Create PostLockInPage**

```tsx
// frontend/src/draft/pages/PostLockInPage.tsx
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useDraftAnalysis } from "../hooks/useDraftAnalysis";
import type { Matchup, RuneData } from "../hooks/useDraftAnalysis";

const DDRAGON_RUNE_BASE = "https://ddragon.leagueoflegends.com/cdn/img";

interface LocationState {
  ally: string[];
  enemy: string[];
  myChampion: string;
  myRole: string;
}

export function PostLockInPage() {
  const navigate = useNavigate();
  const { state } = useLocation() as { state: LocationState };
  const { getRunes, getMatchup, getTeamStrategy, applyRunes, isLoading } = useDraftAnalysis();

  const [runes, setRunes] = useState<RuneData | null>(null);
  const [matchup, setMatchup] = useState<Matchup | null>(null);
  const [strategy, setStrategy] = useState<string>("");
  const [runeApplyStatus, setRuneApplyStatus] = useState<"idle" | "applying" | "success" | "error">("idle");
  const [runeApplyMessage, setRuneApplyMessage] = useState("");
  const [disclaimerShown, setDisclaimerShown] = useState(false);

  const { ally, enemy, myChampion, myRole } = state ?? { ally: [], enemy: [], myChampion: "", myRole: "TOP" };
  const enemyLaner = enemy[ally.indexOf(myChampion)] ?? enemy[0] ?? "";

  useEffect(() => {
    if (myChampion && myRole) {
      getRunes(myChampion, myRole).then(setRunes);
    }
  }, [myChampion, myRole, getRunes]);

  useEffect(() => {
    if (myChampion && enemyLaner && myRole) {
      getMatchup(myChampion, enemyLaner, myRole).then(setMatchup);
    }
  }, [myChampion, enemyLaner, myRole, getMatchup]);

  useEffect(() => {
    if (ally.filter(Boolean).length > 0 && enemy.filter(Boolean).length > 0) {
      getTeamStrategy(ally, enemy, myChampion, myRole).then(setStrategy);
    }
  }, [ally, enemy, myChampion, myRole, getTeamStrategy]);

  const handleApplyRunes = async () => {
    if (!disclaimerShown) {
      setDisclaimerShown(true);
      return;
    }
    if (!runes || !runes.primary_runes || runes.primary_runes.length === 0) {
      setRuneApplyStatus("error");
      setRuneApplyMessage("룬 데이터가 없습니다.");
      return;
    }
    setRuneApplyStatus("applying");
    try {
      const result = await applyRunes({
        name: `RiftBuddy — ${myChampion} ${myRole}`,
        primaryStyleId: runes.primary_runes[0] ?? 8000,
        subStyleId: runes.secondary_runes?.[0] ?? 8000,
        selectedPerkIds: [...(runes.primary_runes ?? []), ...(runes.secondary_runes ?? []), ...(runes.shards ?? [])],
        current: true,
      });
      setRuneApplyStatus("success");
      setRuneApplyMessage(result.message);
    } catch (e: unknown) {
      setRuneApplyStatus("error");
      setRuneApplyMessage(e instanceof Error ? e.message : "알 수 없는 오류");
    }
  };

  return (
    <div style={{ width: "100%", height: "100vh", background: "#0f1117", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ padding: "16px 24px", background: "#141720", borderBottom: "1px solid #1e2130" }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#e8e8e8" }}>
          확정 드래프트 — 내 챔피언: {myChampion} {myRole}
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
          {ally.filter(Boolean).map((c) => <span key={c} style={{ fontSize: 12, color: "#00c8a0" }}>{c}</span>)}
          <span style={{ color: "#555" }}>vs</span>
          {enemy.filter(Boolean).map((c) => <span key={c} style={{ fontSize: 12, color: "#e84057" }}>{c}</span>)}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0, overflow: "hidden" }}>
        {/* Left: Runes */}
        <div style={{ padding: 16, borderRight: "1px solid #1e2130", overflowY: "auto" }}>
          <h3 style={{ fontSize: 12, color: "#00c8a0", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>추천 룬</h3>
          {isLoading("runes") && <span style={{ fontSize: 12, color: "#666" }}>룬 불러오는 중...</span>}
          {runes && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ fontSize: 13, color: "#aaa" }}>
                주 룬: <span style={{ color: "#e8e8e8", fontWeight: 600 }}>{runes.primary_path ?? "-"}</span>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {(runes.primary_runes ?? []).map((id) => (
                  <div key={id} style={{ width: 32, height: 32, background: "#1a1d24", borderRadius: 4, border: "1px solid #333", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: "#666" }}>
                    {id}
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 13, color: "#aaa", marginTop: 8 }}>
                보조 룬: <span style={{ color: "#e8e8e8", fontWeight: 600 }}>{runes.secondary_path ?? "-"}</span>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {(runes.secondary_runes ?? []).map((id) => (
                  <div key={id} style={{ width: 32, height: 32, background: "#1a1d24", borderRadius: 4, border: "1px solid #333", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: "#666" }}>
                    {id}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* LCU Apply button */}
          <div style={{ marginTop: 16 }}>
            {disclaimerShown && runeApplyStatus === "idle" && (
              <div style={{ marginBottom: 8, fontSize: 11, color: "#f0c040", background: "#f0c04010", border: "1px solid #f0c04040", borderRadius: 4, padding: "6px 8px" }}>
                ⚠️ 이 기능은 Riot Games의 공식 지원 기능이 아닙니다. LCU API를 사용합니다. 다시 눌러 적용하세요.
              </div>
            )}
            {runeApplyStatus === "success" && (
              <div style={{ marginBottom: 8, fontSize: 12, color: "#00c8a0" }}>{runeApplyMessage}</div>
            )}
            {runeApplyStatus === "error" && (
              <div style={{ marginBottom: 8, fontSize: 12, color: "#e84057" }}>{runeApplyMessage}</div>
            )}
            <button
              onClick={handleApplyRunes}
              disabled={runeApplyStatus === "applying"}
              style={{
                padding: "6px 14px",
                background: "transparent",
                border: "1px solid #f0c040",
                color: "#f0c040",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {runeApplyStatus === "applying" ? "적용 중..." : "룬 자동 적용 ⚠️ (비공식)"}
            </button>
          </div>
        </div>

        {/* Right: Team strategy + matchup */}
        <div style={{ padding: 16, overflowY: "auto" }}>
          <h3 style={{ fontSize: 12, color: "#00c8a0", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>팀 컴프 전략</h3>
          {isLoading("strategy") && <span style={{ fontSize: 12, color: "#666" }}>전략 생성 중...</span>}
          {strategy && <p style={{ fontSize: 13, color: "#c8c8c8", lineHeight: 1.6 }}>{strategy}</p>}

          {enemyLaner && (
            <>
              <h3 style={{ fontSize: 12, color: "#00c8a0", textTransform: "uppercase", letterSpacing: 1, margin: "16px 0 8px" }}>
                매치업: {myChampion} vs {enemyLaner}
              </h3>
              {isLoading(`matchup-${myChampion}-${enemyLaner}`) && <span style={{ fontSize: 12, color: "#666" }}>분석 중...</span>}
              {matchup && (
                <div>
                  {matchup.tips?.map((tip, i) => (
                    <div key={i} style={{ fontSize: 12, color: "#c8c8c8", marginBottom: 4 }}>• {tip}</div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ display: "flex", justifyContent: "space-between", padding: "12px 24px", background: "#141720", borderTop: "1px solid #1e2130" }}>
        <button
          onClick={() => navigate("/")}
          style={{ padding: "8px 18px", background: "transparent", border: "1px solid #555", color: "#aaa", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
        >
          ← 드래프트로 돌아가기
        </button>
        <button
          onClick={() => window.close()}
          style={{ padding: "8px 24px", background: "#00c8a0", color: "#0f1117", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 700, fontSize: 14 }}
        >
          경기 시작 준비 완료
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npx tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 3: Commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add frontend/src/draft/pages/PostLockInPage.tsx
git commit -m "feat: add Screen 2 PostLockInPage with runes and LCU apply"
```

---

## Task 10: Electron — Second Draft Window + hotkeys

**Files:**
- Modify: `frontend/electron/main.ts`
- Modify: `frontend/electron/preload.ts`

- [ ] **Step 1: Update main.ts**

Replace the full content of `frontend/electron/main.ts` with:

```typescript
import { app, BrowserWindow, globalShortcut } from "electron";
import path from "path";

const isDev = process.env.NODE_ENV === "development";
const isOverlay = process.env.RIFTBUDDY_OVERLAY === "1" || !isDev;

function createOverlayWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 520,
    height: 360,
    x: 1360,
    y: 90,
    transparent: isOverlay,
    frame: !isOverlay,
    alwaysOnTop: true,
    skipTaskbar: isOverlay,
    resizable: !isOverlay,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  win.setAlwaysOnTop(true, "screen-saver");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  if (isOverlay) {
    win.setIgnoreMouseEvents(true, { forward: true });
  }
  if (isDev) {
    win.loadURL("http://localhost:5173");
  } else {
    win.loadFile(path.join(__dirname, "index.html"));
  }
  return win;
}

function createDraftWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    transparent: false,
    frame: true,
    alwaysOnTop: true,
    title: "RiftBuddy Draft",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  if (isDev) {
    win.loadURL("http://localhost:5173/src/draft/draft.html");
  } else {
    win.loadFile(path.join(__dirname, "draft.html"));
  }
  return win;
}

app.whenReady().then(() => {
  const overlayWin = createOverlayWindow();
  const draftWin = createDraftWindow();

  globalShortcut.register("CommandOrControl+Shift+B", () => {
    overlayWin.webContents.send("riftbuddy:request-advice");
  });
  globalShortcut.register("CommandOrControl+Shift+Space", () => {
    overlayWin.webContents.send("riftbuddy:request-voice-question");
  });
  globalShortcut.register("CommandOrControl+Shift+L", () => {
    overlayWin.webContents.send("riftbuddy:toggle-language");
  });
  globalShortcut.register("CommandOrControl+Shift+D", () => {
    if (draftWin.isVisible()) {
      draftWin.hide();
    } else {
      draftWin.show();
    }
  });
});

app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => app.quit());
```

- [ ] **Step 2: Build Electron**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add frontend/electron/main.ts
git commit -m "feat: add Draft Window Electron BrowserWindow with Cmd+Shift+D hotkey"
```

---

## Task 11: Integration test — full draft flow

- [ ] **Step 1: Start backend in mock mode**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
RIFTBUDDY_TEST_MODE=1 RIFTBUDDY_LLM_PROVIDER=mock uvicorn backend.main:app --port 8001 --reload
```

- [ ] **Step 2: Run all backend tests**

```bash
python -m pytest backend/tests/ -v 2>&1 | tail -20
```

Expected: all tests pass (≥32 passed including new draft + lcu tests)

- [ ] **Step 3: Start frontend in dev mode**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend && npm run dev
```

- [ ] **Step 4: Manual smoke test**

Visit `http://localhost:5173/src/draft/draft.html` in browser.
- Enter "Rumble" in ally slot 1, click "나" button.
- Enter "Darius" in enemy slot 1.
- Select TOP role.
- Verify: loading spinners appear, panels populate (or show error if op.gg MCP unreachable).
- Click "분석 완료 →" → verify navigation to `/post-lock-in`.
- On Screen 2: verify rune panel loads, strategy text loads, "룬 자동 적용" button visible.

- [ ] **Step 5: Final commit**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
git add -A
git commit -m "chore: sub-project A complete — draft window smoke tested"
```
