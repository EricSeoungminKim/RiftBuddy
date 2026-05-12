# RiftBuddy — Codex Handoff

**Date:** 2026-05-12  
**Branch:** main  
**Last commit:** `10dc453` feat(postgame): add op_score_timeline trend analysis to after-game seeds

---

## What RiftBuddy Is

Real-time AI coaching overlay for League of Legends. Electron desktop app with a FastAPI backend.

- Reads live game state from the Riot Live Client API every 3 seconds
- Detects in-game events (low health, CS drop, death streak, etc.)
- Fetches OP.GG matchup/counter data via MCP HTTP API
- Retrieves relevant knowledge snippets from ChromaDB (champion tips + past performance seeds)
- Sends enriched context to an LLM (Anthropic/Groq/Gemini) and pushes advice to the Electron overlay over WebSocket
- After each game, saves a performance seed to ChromaDB with OP.GG stats, op_score, timeline trend

---

## Current Architecture

```
Riot Live Client API
        ↓
   GameState (backend/riot/live_client.py)
        ↓
  ContextPacket (backend/context/engine.py)
        ↓
EventDetectorPipeline (backend/timeline/)       ← 9 detectors
        ↓
_fetch_opgg_snippets()                          ← OP.GG MCP live matchup/fed-enemy
        ↓
KnowledgeRetriever (backend/knowledge/)         ← ChromaDB RAG
        ↓
AdvicePlanner (backend/advice/planner.py)
        ↓
LLM (backend/llm/advisor.py)                   ← Anthropic / Groq / Gemini
        ↓
WebSocket → Electron Overlay (frontend/)
```

**Key files:**
- `backend/main.py` — FastAPI app, polling loop, WebSocket handler, `send_advice()`
- `backend/opgg/client.py` — OP.GG MCP HTTP client (no API key needed)
- `backend/opgg/snippets.py` — OP.GG response → KnowledgeSnippet converters
- `backend/knowledge/performance_seeds.py` — GameSummary dataclass, seed text generation, ChromaDB embed
- `backend/timeline/proactive_coach.py` — death pattern extraction, danger window clustering, LLM warning generation
- `backend/postgame/router.py` — `/postgame/coach` endpoint, OP.GG match fetch, seed save
- `frontend/src/components/Overlay.tsx` — main overlay UI, hotkey handlers
- `frontend/src/hooks/useWebSocket.ts` — WebSocket message handling
- `frontend/src/types.ts` — ServerMessage union type

**Hotkeys (in-game):**
- `Cmd+Shift+B` — general game state advice
- `Cmd+Shift+C` — OP.GG matchup stats only (`opgg_only=True`)
- `Cmd+Shift+1` — item recommendation
- `Cmd+Shift+2` — macro/objective advice

**WebSocket message types from backend:**
- `advice` — standard LLM advice response
- `proactive_warning` — auto-triggered danger window warning (no user prompt)
- `transcript` — STT transcript echo
- `game_state` — live game state broadcast
- `game_end` — game over signal
- `error` — error message

**Environment variables required (`.env`):**
```
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
SUPABASE_URL=
SUPABASE_ANON_KEY=
RIOT_GAME_NAME=        # Riot ID game name (e.g. "Hide on bush")
RIOT_TAG_LINE=         # Riot ID tag (e.g. "KR1")
RIOT_REGION=KR
LLM_PROVIDER=anthropic # or groq, gemini, mock
RIFTBUDDY_RESPONSE_LANGUAGE=ko
```

---

## Tasks to Complete

### Task 1 — Proactive Warning UI distinction

**Problem:** `proactive_warning` WebSocket messages are displayed identically to regular `advice` messages in the overlay. Users can't tell it's an automatic pattern-based warning vs. a requested advice.

**What to do:**
- In `frontend/src/hooks/useWebSocket.ts`: add a `isProactive: boolean` field to `ChatMessage` interface and set it `true` when `msg.type === "proactive_warning"`
- In `frontend/src/components/Overlay.tsx`: render proactive warning messages with a distinct style — amber/yellow color, `⚠️` prefix, and slightly different background. Regular advice stays white/default.
- In `frontend/src/types.ts`: `ProactiveWarningMessage` already exists — no changes needed there.

**Files to change:** `frontend/src/hooks/useWebSocket.ts`, `frontend/src/components/Overlay.tsx`

---

### Task 2 — OP.GG cs_per_min field validation and fix

**Problem:** `backend/knowledge/performance_seeds.py` → `save_game_seed()` tries to read `avg_stats.cs_per_min` from the OP.GG `lol_get_champion_analysis` response to compute `cs_vs_avg_pct`. This field name is unverified — the actual OP.GG API may use a different key.

**Current code in `save_game_seed()`:**
```python
avg_cs_per_min = avg_data.get("cs_per_min")
if avg_cs_per_min and summary.game_duration_minutes > 0:
    my_cs_per_min = summary.avg_cs / summary.game_duration_minutes
    summary.cs_vs_avg_pct = my_cs_per_min / avg_cs_per_min
```

**What to do:**
1. In `backend/opgg/client.py` → `get_champion_analysis_for_comparison()`, update `desired_output_fields` to also request `data.summary.average_stats` broadly (remove field filtering or add more candidates):
   ```python
   "desired_output_fields": [
       "data.summary.average_stats",
       "data.summary.positions[].stats.{win_rate,kda,cs_per_min,minion_kill_per_game}",
   ]
   ```
2. In `backend/knowledge/performance_seeds.py` → `save_game_seed()`, try multiple field name candidates with fallback:
   ```python
   avg_cs_per_min = (
       avg_data.get("cs_per_min")
       or avg_data.get("minion_kill_per_game")
       or avg_data.get("cs")
   )
   ```
3. Add a log line so when the field is found it prints the actual key name — helps confirm which one OP.GG uses.

**Files to change:** `backend/opgg/client.py`, `backend/knowledge/performance_seeds.py`

---

### Task 3 — Overlay UI improvement

**Problem:** The overlay chat log is a plain text list. There's no visual hierarchy between proactive warnings, OP.GG matchup responses, and regular advice. The UI needs to communicate type and priority at a glance.

**What to do:**
- Read `frontend/src/components/Overlay.tsx` in full first to understand current layout
- Add a `source` tag badge to each message: `"🤖 AI 코치"` for regular advice, `"⚠️ 패턴 경고"` for proactive warnings, `"📊 OP.GG"` for matchup responses
  - Matchup responses are sent when user presses `Cmd+Shift+C` (action = `"matchup"`) — the backend sends a regular `advice` type. To distinguish, the frontend can track the last action sent and tag the next advice message accordingly.
- Style changes:
  - Proactive warning: amber left border (`border-l-2 border-amber-400`), slightly dimmed background
  - OP.GG matchup: blue left border (`border-l-2 border-blue-400`)
  - Regular advice: default white
  - All in a scrollable message list with max height, newest at bottom
- Keep the overlay compact — it overlays over the game. Max width ~380px, semi-transparent background.

**Files to change:** `frontend/src/components/Overlay.tsx`, `frontend/src/hooks/useWebSocket.ts`

> Note: Task 1 and Task 3 overlap — implement them together as one pass.

---

### Task 4 — Draft → In-game continuity

**Problem:** The draft assistant (champion select phase) detects the player's champion and opponent picks via LCU API, but this data is not passed to the in-game advice pipeline. When the game starts, `backend/main.py` re-reads champion info from the Riot Live Client API, which can be slow or inaccurate in the first few minutes.

**What to do:**
1. In `frontend/electron/main.ts`, when champ select ends and the game starts, send the draft result (my champion, position, lane opponent) to the backend via a new REST endpoint.
2. Add `POST /game/draft-context` endpoint in `backend/main.py` (or a new `backend/draft/router.py` route):
   ```python
   class DraftContext(BaseModel):
       my_champion: str
       my_position: str
       lane_opponent: str | None = None

   @app.post("/game/draft-context")
   async def set_draft_context(ctx: DraftContext):
       global _cached_lane_opponent, _lane_opponent_cache_key
       _cached_lane_opponent = ctx.lane_opponent
       # Set a sentinel cache key so role_rate inference is skipped
       _lane_opponent_cache_key = f"{ctx.my_champion}:{ctx.my_position}:from_draft"
       return {"ok": True}
   ```
3. In `frontend/electron/champSelectTracking.ts`, find where champ select finalization is detected and trigger the endpoint call after game start is confirmed.

**Files to change:** `backend/main.py`, `frontend/electron/champSelectTracking.ts`, possibly `frontend/electron/main.ts`

---

### Task 5 — Phase 6: Demo & README Polish

**Goal:** Make RiftBuddy presentable as a portfolio project. Produce a polished README and a working demo script.

**Spec (from `docs/superpowers/specs/2026-05-11-riftbuddy-2-0-design.md`):**

#### 5a — README.md

Write `README.md` at repo root with this structure:

```markdown
# RiftBuddy — Real-time AI Inference Platform for League Coaching

[Demo GIF — placeholder OK if no recording yet]

## What it does
## Architecture  (Mermaid diagram)
## Key Technical Challenges
## Evaluation Results  (table from evals/run_evals.py output)
## Quick Start
## Environment Variables
```

**Architecture diagram** should show the full pipeline:
`Riot API → GameState → EventPipeline → OP.GG MCP → ChromaDB RAG → AdvicePlanner → LLM → WebSocket → Electron`

**Evaluation results table** — run `python evals/run_evals.py` and capture output, paste into README.

#### 5b — Demo script (`TEST_MODE=1`)

`TEST_MODE` is already supported in `backend/riot/live_client.py`. Verify the demo flow works end-to-end:

1. `RIFTBUDDY_TEST_MODE=1 uvicorn backend.main:app --port 8001`
2. Open Electron overlay
3. Press `Cmd+Shift+B` → should receive general advice (mock game state)
4. Verify `proactive_warning` appears if ChromaDB has seeded death pattern data

Add a `docs/DEMO.md` with step-by-step demo instructions for anyone evaluating the project.

#### 5c — Resume bullets

Add to README under a collapsible `## Resume` section:

> Designed a real-time AI inference platform for League of Legends that transforms live game telemetry into prioritized coaching signals via a deterministic event detection pipeline (9 detectors), OP.GG MCP live data integration, champion/matchup knowledge retrieval (ChromaDB + sentence-transformers), and an advice planning layer before LLM dispatch. Includes proactive pattern-based coaching from historical performance seeds and an automated eval suite.

**Files to create/change:** `README.md`, `docs/DEMO.md`

---

## Suggested Execution Order

1. **Task 1 + 3 together** — UI pass (proactive warning distinction + overlay redesign)
2. **Task 2** — OP.GG field validation (low risk, isolated backend fix)
3. **Task 4** — Draft → in-game continuity (requires Electron + backend coordination)
4. **Task 5** — Phase 6 README + demo polish (do last, captures everything)

---

## Test Commands

```bash
# Backend tests (107 passing as of last commit)
python -m pytest backend/tests/ -q

# Frontend tests
cd frontend && npm test

# Run evals
python evals/run_evals.py

# Start backend (test mode)
RIFTBUDDY_TEST_MODE=1 LLM_PROVIDER=mock uvicorn backend.main:app --reload --port 8001

# Start frontend
cd frontend && npm run dev
```

## Known Good State

- 107 backend tests passing
- `LLM_PROVIDER=mock` bypasses all API keys for local testing
- `RIFTBUDDY_TEST_MODE=1` provides fake game state (no real LoL game needed)
- OP.GG MCP endpoint `https://mcp-api.op.gg/mcp` requires no API key
- ChromaDB persisted at `.chroma_db/` — delete to reset knowledge/seeds
