# RiftBuddy 2.0 — Design Spec

**Date:** 2026-05-11  
**Author:** Seoungmin Kim  
**Goal:** Upgrade RiftBuddy from an AI app into a production-grade AI Inference Platform for portfolio positioning as AI Backend Infrastructure Engineer.

---

## Decisions Summary

| Item             | Decision                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------ |
| Phase order      | Phase 1 → 2 → 3 → 4 → 5 → 6                                                                |
| Existing code    | Keep `context/`, `llm/`, `riot/`, `voice/` as-is. No duplication — import and reuse.       |
| New modules      | Add `timeline/`, `knowledge/`, `advice/` alongside existing modules                        |
| Phase 1 approach | Proper folder structure + typed schemas first, then build features into clean skeleton     |
| Phase 2 scope    | `BaseDetector` + `EventDetectorPipeline` skeleton + 3 core detectors implemented + 6 stubs |
| Knowledge layer  | Manual JSON/YAML for ~20 champions + user_plans/ for personalized playbooks                |
| Eval conditions  | Percentage-based (health_percent) not absolute values                                      |

---

## Target Architecture

```
Riot Live Client API
        ↓
   GameState (riot/live_client.py)         ← existing
        ↓
  ContextPacket (context/engine.py)        ← existing
        ↓
EventDetectorPipeline (timeline/)          ← NEW
        ↓
 KnowledgeRetriever (knowledge/)           ← NEW
        ↓
   AdvicePlanner (advice/)                 ← NEW
        ↓
  LLM Gateway (llm/advisor.py)            ← existing, minor enrichment only
        ↓
  TTS + Electron Overlay                   ← existing
```

---

## Phase 1 — Professional Refactor

### New Folder Structure

```
backend/
  context/         ← unchanged
  llm/             ← unchanged
  riot/            ← unchanged
  voice/           ← unchanged
  draft/           ← unchanged
  postgame/        ← unchanged
  lcu/             ← unchanged

  timeline/        ← NEW
    __init__.py
    schemas.py
    event_detector.py
    detectors/
      __init__.py
      low_health.py
      gold_spike.py
      objective_timer.py
      death_streak.py
      recall_window.py
      item_completion.py
      cs_drop.py
      vision_warning.py
      enemy_jungle_unknown.py

  knowledge/       ← NEW
    __init__.py
    schemas.py
    retriever.py
    data/
      champions/
      matchups/
      macro_rules/
      user_plans/

  advice/          ← NEW
    __init__.py
    schemas.py
    planner.py

evals/             ← NEW (project root level)
  scenarios/
  run_evals.py
  report.md
```

### Typed Schemas

**`timeline/schemas.py`:**

```python
from enum import Enum
from dataclasses import dataclass

class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

@dataclass
class DetectedEvent:
    event_type: str      # "LOW_HEALTH", "GOLD_SPIKE", "OBJECTIVE_SPAWN", etc.
    severity: Severity
    reason: str
    recommended_action: str
```

**`knowledge/schemas.py`:**

```python
@dataclass
class KnowledgeSnippet:
    source: str       # "champion:rumble", "matchup:rumble_vs_tryndamere", "user_plan"
    content: str      # text injected into LLM context
    relevance: str    # "high" / "medium"
```

**`advice/schemas.py`:**

```python
@dataclass
class AdviceRequest:
    mode: str                              # "DEFENSIVE", "AGGRESSIVE", "MACRO", "RECALL"
    priority_event: DetectedEvent | None
    knowledge_snippets: list[KnowledgeSnippet]
    response_length: str                   # "short" / "medium"
```

### CI / GitHub Actions

- Add `.github/workflows/ci.yml`
- Run `pytest backend/tests/` on every push
- Run `python evals/run_evals.py` on every push
- Add test badge to README

---

## Phase 2 — Event Intelligence Layer

### BaseDetector Interface (`timeline/event_detector.py`)

```python
class BaseDetector:
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        raise NotImplementedError

class EventDetectorPipeline:
    def __init__(self, detectors: list[BaseDetector]):
        self.detectors = detectors

    def run(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        events = []
        for detector in self.detectors:
            events.extend(detector.detect(state, packet))
        return sorted(events, key=lambda e: e.severity.value, reverse=True)
```

Uses existing `GameState` (from `riot/`) and `ContextPacket` (from `context/`) — no recomputation.

### Core 3 Detectors (fully implemented)

| Detector                 | Trigger                                            | Severity      |
| ------------------------ | -------------------------------------------------- | ------------- |
| `LowHealthDetector`      | `packet.health_percent < 30`                       | HIGH          |
| `GoldSpikeDetector`      | `packet.gold >= 1300` (MEDIUM), `>= 2500` (HIGH)   | HIGH / MEDIUM |
| `ObjectiveTimerDetector` | Objective spawning within 60 seconds               | MEDIUM        |

### ObjectiveTimerDetector Logic

**Objective spawn timers (Patch 25.09):**

| Objective   | First Spawn | Respawn             | Despawn |
| ----------- | ----------- | ------------------- | ------- |
| Dragon      | 5:00        | 5 min after kill    | —       |
| Voidgrubs   | 8:00        | None (1 group only) | 14:45   |
| Rift Herald | 15:00       | None                | 19:45   |
| Baron       | 20:00       | 6 min after kill    | —       |

**Logic:**

1. First spawn: fire when `game_time` is within 60 seconds of first spawn time
2. After first spawn: parse `recent_events` for `DragonKill` / `BaronKill` events → extract kill time → compute respawn time → fire 60 seconds before
3. Voidgrubs / Rift Herald: if already killed in `recent_events`, no further alerts
4. Voidgrubs special: if not yet killed and `game_time > 14:00` → fire "Voidgrubs despawning soon" alert

Uses `state.recent_events` already in `GameState` — no additional API calls.

### Remaining 6 Detectors (stubs)

```python
class DeathStreakDetector(BaseDetector):
    def detect(self, state, packet) -> list[DetectedEvent]:
        return []  # TODO

class RecallWindowDetector(BaseDetector):
    def detect(self, state, packet) -> list[DetectedEvent]:
        return []  # TODO

class ItemCompletionDetector(BaseDetector):
    def detect(self, state, packet) -> list[DetectedEvent]:
        return []  # TODO

class CSDropDetector(BaseDetector):
    def detect(self, state, packet) -> list[DetectedEvent]:
        return []  # TODO

class VisionWarningDetector(BaseDetector):
    def detect(self, state, packet) -> list[DetectedEvent]:
        return []  # TODO

class EnemyJungleUnknownDetector(BaseDetector):
    def detect(self, state, packet) -> list[DetectedEvent]:
        return []  # TODO
```

### Connection to LLM

Events are injected into `ContextPacket.summary` before passing to `llm/advisor.py`. `advisor.py` is not modified — only its input is enriched.

---

## Phase 3 — Champion Knowledge / RAG Layer

### Data Structure

```
backend/knowledge/data/
  champions/
    rumble.json
    ahri.json
    lee_sin.json
    ... (~20 champions, manually authored)
  matchups/
    rumble_vs_tryndamere.json
  macro_rules/
    top_lane.yaml
    objective_setup.yaml
  user_plans/
    my_rumble_plan.yaml    # user-defined personal playbook
    my_jungle_routes.yaml
```

### Champion Profile Format

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

### User Plan Format

```yaml
# my_rumble_plan.yaml
champion: Rumble
notes:
  - 탑 럼블은 항상 레벨 3 전에 무리한 교환 금지
  - 과열 상태에서 정글러 위치 모를 때 절대 딜교 하지 말 것
  - 이퀄라이저는 드래곤/바론 협곡 입구에서 사용
```

### `retriever.py` Logic

```python
def get_snippets(champion: str, position: str, enemy_champions: tuple) -> list[KnowledgeSnippet]:
    # 1. Load champion profile JSON
    # 2. Load matching matchup files
    # 3. Load position-specific macro rules YAML
    # 4. Load user_plans if champion matches
    # Return top 3 most relevant snippets
```

Input comes from existing `GameState.champion_name`, `GameState.assigned_position`, `GameState.enemy_champions` — no new data needed.

### Connection to LLM

`llm/advisor.py`의 `build_user_content()`에 `knowledge_snippets` 파라미터 추가. 기존 로직 보존, context 앞에 knowledge block만 삽입.

---

## Phase 4 — Advice Planner

### `planner.py` Logic

```python
def plan(events: list[DetectedEvent], snippets: list[KnowledgeSnippet]) -> AdviceRequest:
    top_event = events[0] if events else None
    mode = _decide_mode(top_event)
    length = "short" if top_event and top_event.severity == Severity.HIGH else "medium"
    return AdviceRequest(
        mode=mode,
        priority_event=top_event,
        knowledge_snippets=snippets,
        response_length=length
    )

def _decide_mode(event: DetectedEvent | None) -> str:
    if not event:
        return "MACRO"
    return {
        "LOW_HEALTH": "DEFENSIVE",
        "GOLD_SPIKE": "RECALL",
        "OBJECTIVE_SPAWN": "MACRO",
        "DEATH_STREAK": "DEFENSIVE",
    }.get(event.event_type, "MACRO")
```

### LLM Prompt Structure (after enrichment)

```
[MODE: DEFENSIVE]
[PRIORITY: LOW_HEALTH — 체력 23%, 즉시 귀환 고려]
[KNOWLEDGE: 럼블은 대시가 없어 낮은 체력에서 매우 취약]
[USER PLAN: 교전 전 항상 정글러 위치 확인]

Current game state: ...
Player asks: ...
```

`llm/advisor.py` provider dispatch logic unchanged.

---

## Phase 5 — Evaluation System

### Scenario Schema

```json
{
  "name": "string — 시나리오 이름",
  "description": "string — 이 시나리오가 테스트하는 것",

  "conditions": {
    "health_percent": "number (0-100)",
    "gold": "number",
    "game_time_minutes": "number",
    "level": "number",
    "creep_score": "number",
    "deaths": "number",
    "recent_events": ["string — e.g. 'DragonKill at 8.2m'"],
    "assigned_position": "TOP | JUNGLE | MIDDLE | BOTTOM | UTILITY"
  },

  "expected": {
    "detected_events": [
      "LOW_HEALTH",
      "GOLD_SPIKE",
      "OBJECTIVE_SPAWN",
      "DEATH_STREAK"
    ],
    "advice_mode": "DEFENSIVE | AGGRESSIVE | MACRO | RECALL",
    "advice_contains": ["string"],
    "advice_contains_not": ["string"],
    "max_response_tokens": 150,
    "max_latency_ms": 100
  }
}
```

### Scenario Files

**`evals/scenarios/low_health.json`:**

```json
{
  "name": "low_health_danger",
  "description": "체력 25% 이하 — 무조건 DEFENSIVE 모드, 귀환 추천",
  "conditions": { "health_percent": 25 },
  "expected": {
    "detected_events": ["LOW_HEALTH"],
    "advice_mode": "DEFENSIVE",
    "advice_contains": ["귀환"],
    "advice_contains_not": ["교전", "돌격"],
    "max_response_tokens": 150,
    "max_latency_ms": 100
  }
}
```

**`evals/scenarios/gold_spike.json`:**

```json
{
  "name": "gold_spike_recall",
  "description": "골드 2500+ — 다음 웨이브 정리 후 귀환 추천",
  "conditions": { "health_percent": 75, "gold": 2800 },
  "expected": {
    "detected_events": ["GOLD_SPIKE"],
    "advice_mode": "RECALL",
    "advice_contains": ["귀환", "아이템"],
    "max_response_tokens": 150,
    "max_latency_ms": 100
  }
}
```

**`evals/scenarios/objective_spawn.json`:**

```json
{
  "name": "dragon_spawn_soon",
  "description": "Dragon 스폰 60초 전 — 합류 or 귀환 판단 요청",
  "conditions": {
    "health_percent": 80,
    "gold": 1200,
    "game_time_minutes": 4.0,
    "recent_events": []
  },
  "expected": {
    "detected_events": ["OBJECTIVE_SPAWN"],
    "advice_mode": "MACRO",
    "advice_contains": ["용", "합류"],
    "max_response_tokens": 150,
    "max_latency_ms": 100
  }
}
```

**`evals/scenarios/death_streak.json`:**

```json
{
  "name": "death_streak_tilt",
  "description": "3데스 이상 — 안전 플레이 추천",
  "conditions": { "health_percent": 60, "deaths": 3, "gold": 900 },
  "expected": {
    "detected_events": ["DEATH_STREAK"],
    "advice_mode": "DEFENSIVE",
    "advice_contains": ["안전"],
    "advice_contains_not": ["교전", "싸움"],
    "max_response_tokens": 150,
    "max_latency_ms": 100
  }
}
```

### `run_evals.py`

- Uses mock provider — no LLM cost
- Runs full pipeline: `timeline → knowledge → planner → llm`
- Validates all `expected` fields
- Outputs `report.md` with pass/fail table
- Integrated into GitHub Actions CI

### README Eval Results Table

```
| Metric                    | Result |
|---------------------------|--------|
| Scenario tests passed     | 4/4    |
| Avg mock latency          | <50ms  |
| Event detection accuracy  | 100%   |
| Korean terminology pass   | 100%   |
| Advice mode accuracy      | 4/4    |
```

---

## Phase 6 — Demo & README Polish

### README Structure

```markdown
# RiftBuddy — Real-time AI Inference Platform for League Coaching

[Demo GIF]

## What it does

## Architecture

[Mermaid diagram]

## Key Technical Challenges

## Evaluation Results

[table]

## Quick Start
```

### Demo Script

1. Start backend
2. Open Electron overlay
3. Set `TEST_MODE=1` (fake game state — no real game needed)
4. Trigger LOW_HEALTH → show DEFENSIVE advice
5. Trigger GOLD_SPIKE → show RECALL advice
6. Trigger Dragon 60s before spawn → show MACRO advice

`TEST_MODE` already exists in `live_client.py` — no new mock infrastructure needed.

---

## Resume Bullets

**Standard:**

> Built a real-time AI League coaching overlay with FastAPI, WebSockets, Electron, Riot Live Client API, and multi-provider LLM integration; added event detection pipeline, champion knowledge retrieval, advice planning layer, and automated eval suite.

**Strong:**

> Designed a real-time AI inference platform for League of Legends that transforms live game telemetry into prioritized coaching signals via a deterministic event detection pipeline, champion/matchup knowledge retrieval, and an advice planning layer before LLM dispatch.
