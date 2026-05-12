# RiftBuddy Phase 1+2 — Scaffold + Event Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add typed schemas, folder structure, CI, and a working event detection pipeline (3 core detectors + 6 stubs) that enriches the LLM prompt with prioritized game signals.

**Architecture:** New modules `timeline/`, `knowledge/`, `advice/` are added alongside existing `context/`, `llm/`, `riot/`. The `EventDetectorPipeline` runs after `build_context_packet()` in `main.py:send_advice()` and enriches the `ContextPacket.summary` before passing to the existing `get_advice()`. No existing files are removed or rewritten — only `main.py` and `context/engine.py` get minor additions.

**Tech Stack:** Python 3.13, FastAPI, pytest, pytest-asyncio, dataclasses, GitHub Actions

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/timeline/schemas.py` | Create | `Severity` enum, `DetectedEvent` dataclass |
| `backend/timeline/event_detector.py` | Create | `BaseDetector`, `EventDetectorPipeline` |
| `backend/timeline/detectors/__init__.py` | Create | Package init |
| `backend/timeline/detectors/low_health.py` | Create | `LowHealthDetector` — fires when `health_percent < 30` |
| `backend/timeline/detectors/gold_spike.py` | Create | `GoldSpikeDetector` — fires when `gold >= 1300` |
| `backend/timeline/detectors/objective_timer.py` | Create | `ObjectiveTimerDetector` — fires 60s before objective spawns |
| `backend/timeline/detectors/death_streak.py` | Create | `DeathStreakDetector` stub |
| `backend/timeline/detectors/recall_window.py` | Create | `RecallWindowDetector` stub |
| `backend/timeline/detectors/item_completion.py` | Create | `ItemCompletionDetector` stub |
| `backend/timeline/detectors/cs_drop.py` | Create | `CSDropDetector` stub |
| `backend/timeline/detectors/vision_warning.py` | Create | `VisionWarningDetector` stub |
| `backend/timeline/detectors/enemy_jungle_unknown.py` | Create | `EnemyJungleUnknownDetector` stub |
| `backend/timeline/__init__.py` | Create | Package init |
| `backend/knowledge/__init__.py` | Create | Package init (empty — populated in Plan 2) |
| `backend/knowledge/schemas.py` | Create | `KnowledgeSnippet` dataclass |
| `backend/advice/__init__.py` | Create | Package init (empty — populated in Plan 2) |
| `backend/advice/schemas.py` | Create | `AdviceRequest` dataclass |
| `backend/context/engine.py` | Modify | Add `enrich_summary_with_events()` helper |
| `backend/main.py` | Modify | Wire pipeline into `send_advice()` |
| `backend/tests/test_detectors.py` | Create | Unit tests for all 3 core detectors + pipeline |
| `.github/workflows/ci.yml` | Create | Run pytest on every push |

---

## Task 1: Typed Schemas — `timeline/schemas.py`

**Files:**
- Create: `backend/timeline/__init__.py`
- Create: `backend/timeline/schemas.py`
- Test: `backend/tests/test_detectors.py`

- [ ] **Step 1: Create package init**

```python
# backend/timeline/__init__.py
```

- [ ] **Step 2: Write failing test for schemas**

Create `backend/tests/test_detectors.py`:

```python
from backend.timeline.schemas import DetectedEvent, Severity


def test_detected_event_has_required_fields():
    event = DetectedEvent(
        event_type="LOW_HEALTH",
        severity=Severity.HIGH,
        reason="Health is 20%",
        recommended_action="Recall immediately",
    )
    assert event.event_type == "LOW_HEALTH"
    assert event.severity == Severity.HIGH
    assert event.severity.value == 3


def test_severity_ordering():
    assert Severity.HIGH.value > Severity.MEDIUM.value > Severity.LOW.value
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python -m pytest backend/tests/test_detectors.py -v
```
Expected: `ModuleNotFoundError: No module named 'backend.timeline'`

- [ ] **Step 4: Implement `timeline/schemas.py`**

```python
# backend/timeline/schemas.py
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class DetectedEvent:
    event_type: str
    severity: Severity
    reason: str
    recommended_action: str
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_detectors.py::test_detected_event_has_required_fields backend/tests/test_detectors.py::test_severity_ordering -v
```
Expected: 2 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/timeline/__init__.py backend/timeline/schemas.py backend/tests/test_detectors.py
git commit -m "feat(timeline): add DetectedEvent schema and Severity enum"
```

---

## Task 2: Typed Schemas — `knowledge/schemas.py` and `advice/schemas.py`

**Files:**
- Create: `backend/knowledge/__init__.py`
- Create: `backend/knowledge/schemas.py`
- Create: `backend/advice/__init__.py`
- Create: `backend/advice/schemas.py`
- Test: `backend/tests/test_detectors.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_detectors.py`:

```python
from backend.knowledge.schemas import KnowledgeSnippet
from backend.advice.schemas import AdviceRequest
from backend.timeline.schemas import DetectedEvent, Severity


def test_knowledge_snippet_fields():
    snippet = KnowledgeSnippet(
        source="champion:rumble",
        content="Rumble has no dash — vulnerable when pushed",
        relevance="high",
    )
    assert snippet.source == "champion:rumble"
    assert snippet.relevance == "high"


def test_advice_request_fields():
    event = DetectedEvent("LOW_HEALTH", Severity.HIGH, "HP 20%", "Recall")
    snippet = KnowledgeSnippet("champion:rumble", "No dash", "high")
    req = AdviceRequest(
        mode="DEFENSIVE",
        priority_event=event,
        knowledge_snippets=[snippet],
        response_length="short",
    )
    assert req.mode == "DEFENSIVE"
    assert req.priority_event.event_type == "LOW_HEALTH"
    assert len(req.knowledge_snippets) == 1


def test_advice_request_no_event():
    req = AdviceRequest(
        mode="MACRO",
        priority_event=None,
        knowledge_snippets=[],
        response_length="medium",
    )
    assert req.priority_event is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_detectors.py -v
```
Expected: `ModuleNotFoundError: No module named 'backend.knowledge'`

- [ ] **Step 3: Create knowledge package**

```python
# backend/knowledge/__init__.py
```

```python
# backend/knowledge/schemas.py
from dataclasses import dataclass


@dataclass
class KnowledgeSnippet:
    source: str    # e.g. "champion:rumble", "matchup:rumble_vs_tryndamere", "user_plan"
    content: str   # text injected into LLM context
    relevance: str # "high" or "medium"
```

- [ ] **Step 4: Create advice package**

```python
# backend/advice/__init__.py
```

```python
# backend/advice/schemas.py
from __future__ import annotations
from dataclasses import dataclass, field
from backend.timeline.schemas import DetectedEvent
from backend.knowledge.schemas import KnowledgeSnippet


@dataclass
class AdviceRequest:
    mode: str                                    # "DEFENSIVE", "AGGRESSIVE", "MACRO", "RECALL"
    priority_event: DetectedEvent | None
    knowledge_snippets: list[KnowledgeSnippet]   = field(default_factory=list)
    response_length: str                         = "medium"  # "short" or "medium"
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_detectors.py -v
```
Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/knowledge/__init__.py backend/knowledge/schemas.py backend/advice/__init__.py backend/advice/schemas.py backend/tests/test_detectors.py
git commit -m "feat(schemas): add KnowledgeSnippet and AdviceRequest schemas"
```

---

## Task 3: `BaseDetector` and `EventDetectorPipeline`

**Files:**
- Create: `backend/timeline/event_detector.py`
- Create: `backend/timeline/detectors/__init__.py`
- Test: `backend/tests/test_detectors.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_detectors.py`:

```python
from backend.timeline.event_detector import BaseDetector, EventDetectorPipeline
from backend.riot.live_client import GameState
from backend.context.engine import build_context_packet


def _make_state(**kwargs) -> GameState:
    defaults = dict(current_health=1000, max_health=2000, gold=500, level=5, game_time=300.0)
    defaults.update(kwargs)
    return GameState(**defaults)


def test_base_detector_raises():
    detector = BaseDetector()
    state = _make_state()
    packet = build_context_packet(state)
    try:
        detector.detect(state, packet)
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass


def test_pipeline_returns_empty_with_no_detectors():
    pipeline = EventDetectorPipeline(detectors=[])
    state = _make_state()
    packet = build_context_packet(state)
    assert pipeline.run(state, packet) == []


def test_pipeline_sorts_by_severity_descending():
    from backend.timeline.schemas import DetectedEvent, Severity

    class AlwaysLow(BaseDetector):
        def detect(self, state, packet):
            return [DetectedEvent("LOW_SIGNAL", Severity.LOW, "low", "do nothing")]

    class AlwaysHigh(BaseDetector):
        def detect(self, state, packet):
            return [DetectedEvent("HIGH_SIGNAL", Severity.HIGH, "high", "act now")]

    pipeline = EventDetectorPipeline(detectors=[AlwaysLow(), AlwaysHigh()])
    state = _make_state()
    packet = build_context_packet(state)
    events = pipeline.run(state, packet)
    assert events[0].severity == Severity.HIGH
    assert events[1].severity == Severity.LOW
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_detectors.py::test_base_detector_raises -v
```
Expected: `ModuleNotFoundError: No module named 'backend.timeline.event_detector'`

- [ ] **Step 3: Implement `event_detector.py`**

```python
# backend/timeline/event_detector.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.schemas import DetectedEvent


class BaseDetector:
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        raise NotImplementedError


class EventDetectorPipeline:
    def __init__(self, detectors: list[BaseDetector]):
        self.detectors = detectors

    def run(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        events: list[DetectedEvent] = []
        for detector in self.detectors:
            events.extend(detector.detect(state, packet))
        return sorted(events, key=lambda e: e.severity.value, reverse=True)
```

- [ ] **Step 4: Create detectors package init**

```python
# backend/timeline/detectors/__init__.py
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_detectors.py::test_base_detector_raises backend/tests/test_detectors.py::test_pipeline_returns_empty_with_no_detectors backend/tests/test_detectors.py::test_pipeline_sorts_by_severity_descending -v
```
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/timeline/event_detector.py backend/timeline/detectors/__init__.py backend/tests/test_detectors.py
git commit -m "feat(timeline): add BaseDetector and EventDetectorPipeline"
```

---

## Task 4: `LowHealthDetector`

**Files:**
- Create: `backend/timeline/detectors/low_health.py`
- Test: `backend/tests/test_detectors.py`

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_detectors.py`:

```python
from backend.timeline.detectors.low_health import LowHealthDetector


def test_low_health_detector_fires_below_30_percent():
    detector = LowHealthDetector()
    state = _make_state(current_health=500, max_health=2000)  # 25%
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
    assert events[0].event_type == "LOW_HEALTH"
    assert events[0].severity == Severity.HIGH


def test_low_health_detector_silent_above_30_percent():
    detector = LowHealthDetector()
    state = _make_state(current_health=700, max_health=2000)  # 35%
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert events == []


def test_low_health_detector_fires_at_exactly_29_percent():
    detector = LowHealthDetector()
    state = _make_state(current_health=580, max_health=2000)  # 29%
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_detectors.py::test_low_health_detector_fires_below_30_percent -v
```
Expected: `ModuleNotFoundError: No module named 'backend.timeline.detectors.low_health'`

- [ ] **Step 3: Implement `low_health.py`**

```python
# backend/timeline/detectors/low_health.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity

_THRESHOLD = 30.0


class LowHealthDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        if packet.health_percent >= _THRESHOLD:
            return []
        return [
            DetectedEvent(
                event_type="LOW_HEALTH",
                severity=Severity.HIGH,
                reason=f"Health is {packet.health_percent:.0f}% — below safe threshold",
                recommended_action="귀환 또는 교전 회피 — 즉시 안전한 위치로 이동",
            )
        ]
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_detectors.py::test_low_health_detector_fires_below_30_percent backend/tests/test_detectors.py::test_low_health_detector_silent_above_30_percent backend/tests/test_detectors.py::test_low_health_detector_fires_at_exactly_29_percent -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/timeline/detectors/low_health.py backend/tests/test_detectors.py
git commit -m "feat(timeline): implement LowHealthDetector"
```

---

## Task 5: `GoldSpikeDetector`

**Files:**
- Create: `backend/timeline/detectors/gold_spike.py`
- Test: `backend/tests/test_detectors.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_detectors.py`:

```python
from backend.timeline.detectors.gold_spike import GoldSpikeDetector


def test_gold_spike_high_severity_above_2500():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=2600)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
    assert events[0].event_type == "GOLD_SPIKE"
    assert events[0].severity == Severity.HIGH


def test_gold_spike_medium_severity_between_1300_and_2500():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=1800)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
    assert events[0].event_type == "GOLD_SPIKE"
    assert events[0].severity == Severity.MEDIUM


def test_gold_spike_silent_below_1300():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=1200)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert events == []


def test_gold_spike_fires_at_exactly_1300():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=1300)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_detectors.py::test_gold_spike_high_severity_above_2500 -v
```
Expected: `ModuleNotFoundError: No module named 'backend.timeline.detectors.gold_spike'`

- [ ] **Step 3: Implement `gold_spike.py`**

```python
# backend/timeline/detectors/gold_spike.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity

_HIGH_THRESHOLD = 2500.0
_MEDIUM_THRESHOLD = 1300.0


class GoldSpikeDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        if packet.gold >= _HIGH_THRESHOLD:
            return [
                DetectedEvent(
                    event_type="GOLD_SPIKE",
                    severity=Severity.HIGH,
                    reason=f"{packet.gold:.0f} 골드 보유 — 아이템 컴플릿 가능",
                    recommended_action="다음 웨이브 안전하게 정리 후 귀환해서 아이템 구매",
                )
            ]
        if packet.gold >= _MEDIUM_THRESHOLD:
            return [
                DetectedEvent(
                    event_type="GOLD_SPIKE",
                    severity=Severity.MEDIUM,
                    reason=f"{packet.gold:.0f} 골드 보유 — 부분 아이템 구매 가능",
                    recommended_action="귀환 타이밍 고려 — 웨이브 상태와 오브젝트 확인 후 판단",
                )
            ]
        return []
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_detectors.py::test_gold_spike_high_severity_above_2500 backend/tests/test_detectors.py::test_gold_spike_medium_severity_between_1300_and_2500 backend/tests/test_detectors.py::test_gold_spike_silent_below_1300 backend/tests/test_detectors.py::test_gold_spike_fires_at_exactly_1300 -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/timeline/detectors/gold_spike.py backend/tests/test_detectors.py
git commit -m "feat(timeline): implement GoldSpikeDetector"
```

---

## Task 6: `ObjectiveTimerDetector`

**Files:**
- Create: `backend/timeline/detectors/objective_timer.py`
- Test: `backend/tests/test_detectors.py`

Objective spawn timers (Patch 25.09):
- Dragon: first spawn 5:00 (300s), respawn 5 min after kill
- Voidgrubs: first spawn 8:00 (480s), no respawn, despawns at 14:45 (885s)
- Rift Herald: first spawn 15:00 (900s), no respawn, despawns at 19:45 (1185s)
- Baron: first spawn 20:00 (1200s), respawn 6 min after kill

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_detectors.py`:

```python
from backend.timeline.detectors.objective_timer import ObjectiveTimerDetector


def test_objective_fires_60s_before_first_dragon():
    # game_time = 4:10 (250s) — 50s before Dragon first spawn at 5:00 (300s)
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=250.0)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types
    matching = [e for e in events if e.event_type == "OBJECTIVE_SPAWN"]
    assert any("Dragon" in e.reason for e in matching)


def test_objective_silent_before_60s_window():
    # game_time = 3:00 (180s) — 2 min before Dragon
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=180.0)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert events == []


def test_objective_fires_60s_before_first_baron():
    # game_time = 19:10 (1150s) — 50s before Baron first spawn at 20:00 (1200s)
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=1150.0)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types
    matching = [e for e in events if e.event_type == "OBJECTIVE_SPAWN"]
    assert any("Baron" in e.reason for e in matching)


def test_objective_dragon_respawn_after_kill():
    # DragonKill at 5.0m (300s) → respawn at 10:00 (600s)
    # game_time = 9:10 (550s) — 50s before respawn
    detector = ObjectiveTimerDetector()
    state = _make_state(
        game_time=550.0,
        recent_events=("DragonKill at 5.0m",),
    )
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types


def test_objective_voidgrubs_despawn_warning():
    # game_time = 14:10 (850s) — Voidgrubs despawn at 14:45 (885s), within 60s
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=850.0, recent_events=())
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types
    matching = [e for e in events if e.event_type == "OBJECTIVE_SPAWN"]
    assert any("Voidgrub" in e.reason for e in matching)


def test_objective_no_alert_after_voidgrubs_killed():
    # Voidgrubs already killed — no alert
    detector = ObjectiveTimerDetector()
    state = _make_state(
        game_time=850.0,
        recent_events=("VoidgrubKill at 9.0m",),
    )
    packet = build_context_packet(state)
    events = [e for e in detector.detect(state, packet) if "Voidgrub" in e.reason]
    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_detectors.py::test_objective_fires_60s_before_first_dragon -v
```
Expected: `ModuleNotFoundError: No module named 'backend.timeline.detectors.objective_timer'`

- [ ] **Step 3: Implement `objective_timer.py`**

```python
# backend/timeline/detectors/objective_timer.py
import re
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity

_ALERT_WINDOW = 60.0  # seconds before spawn to fire alert

# First spawn times in seconds
_FIRST_SPAWNS = {
    "Dragon": 300.0,
    "Voidgrubs": 480.0,
    "Rift Herald": 900.0,
    "Baron": 1200.0,
}

# Respawn delays in seconds (None = no respawn)
_RESPAWN_DELAYS = {
    "Dragon": 300.0,
    "Baron": 360.0,
}

# Despawn times for one-time objectives
_DESPAWNS = {
    "Voidgrubs": 885.0,   # 14:45
    "Rift Herald": 1185.0, # 19:45
}

# Event name patterns in recent_events strings
_KILL_PATTERNS = {
    "Dragon": r"DragonKill at ([\d.]+)m",
    "Voidgrubs": r"VoidgrubKill at ([\d.]+)m",
    "Rift Herald": r"HeraldKill at ([\d.]+)m",
    "Baron": r"BaronKill at ([\d.]+)m",
}


def _parse_last_kill_minutes(events: tuple[str, ...], pattern: str) -> float | None:
    last = None
    for event in events:
        match = re.search(pattern, event)
        if match:
            last = float(match.group(1))
    return last


class ObjectiveTimerDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        t = state.game_time
        events: list[DetectedEvent] = []

        for obj, first_spawn in _FIRST_SPAWNS.items():
            kill_pattern = _KILL_PATTERNS[obj]
            last_kill_min = _parse_last_kill_minutes(state.recent_events, kill_pattern)
            already_killed = last_kill_min is not None

            # One-time objectives (Voidgrubs, Rift Herald)
            if obj in _DESPAWNS:
                if already_killed:
                    continue
                despawn = _DESPAWNS[obj]
                # Despawn warning: within 60s of despawn and not yet killed
                if despawn - _ALERT_WINDOW <= t < despawn:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} despawning soon at {despawn/60:.1f}m — not yet secured",
                        recommended_action=f"{obj} 처치 시도 또는 포기 결정",
                    ))
                    continue
                # First spawn alert
                if first_spawn - _ALERT_WINDOW <= t < first_spawn:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} spawning at {first_spawn/60:.1f}m",
                        recommended_action=f"{obj} 스폰 60초 전 — 합류 여부 판단",
                    ))
                continue

            # Repeating objectives (Dragon, Baron)
            if not already_killed:
                # First spawn alert
                if first_spawn - _ALERT_WINDOW <= t < first_spawn:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} first spawn at {first_spawn/60:.1f}m",
                        recommended_action=f"{obj} 스폰 60초 전 — 귀환 여부 판단 후 합류",
                    ))
            else:
                respawn_delay = _RESPAWN_DELAYS[obj]
                respawn_time = last_kill_min * 60 + respawn_delay
                if respawn_time - _ALERT_WINDOW <= t < respawn_time:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} respawning at {respawn_time/60:.1f}m",
                        recommended_action=f"{obj} 리스폰 60초 전 — 귀환 여부 판단 후 합류",
                    ))

        return events
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_detectors.py::test_objective_fires_60s_before_first_dragon backend/tests/test_detectors.py::test_objective_silent_before_60s_window backend/tests/test_detectors.py::test_objective_fires_60s_before_first_baron backend/tests/test_detectors.py::test_objective_dragon_respawn_after_kill backend/tests/test_detectors.py::test_objective_voidgrubs_despawn_warning backend/tests/test_detectors.py::test_objective_no_alert_after_voidgrubs_killed -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/timeline/detectors/objective_timer.py backend/tests/test_detectors.py
git commit -m "feat(timeline): implement ObjectiveTimerDetector with Patch 25.09 timers"
```

---

## Task 7: Six Stub Detectors

**Files:**
- Create: `backend/timeline/detectors/death_streak.py`
- Create: `backend/timeline/detectors/recall_window.py`
- Create: `backend/timeline/detectors/item_completion.py`
- Create: `backend/timeline/detectors/cs_drop.py`
- Create: `backend/timeline/detectors/vision_warning.py`
- Create: `backend/timeline/detectors/enemy_jungle_unknown.py`

- [ ] **Step 1: Create all 6 stub files**

```python
# backend/timeline/detectors/death_streak.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class DeathStreakDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: fire when state.deaths >= 3
```

```python
# backend/timeline/detectors/recall_window.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class RecallWindowDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect safe recall windows based on wave state
```

```python
# backend/timeline/detectors/item_completion.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class ItemCompletionDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect when player can complete a core item
```

```python
# backend/timeline/detectors/cs_drop.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class CSDropDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect CS below expected floor for game time
```

```python
# backend/timeline/detectors/vision_warning.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class VisionWarningDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect low ward score relative to game time
```

```python
# backend/timeline/detectors/enemy_jungle_unknown.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class EnemyJungleUnknownDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect when enemy jungler position is unknown and player is pushed
```

- [ ] **Step 2: Verify all stubs import cleanly**

```bash
python -c "
from backend.timeline.detectors.death_streak import DeathStreakDetector
from backend.timeline.detectors.recall_window import RecallWindowDetector
from backend.timeline.detectors.item_completion import ItemCompletionDetector
from backend.timeline.detectors.cs_drop import CSDropDetector
from backend.timeline.detectors.vision_warning import VisionWarningDetector
from backend.timeline.detectors.enemy_jungle_unknown import EnemyJungleUnknownDetector
print('all stubs import ok')
"
```
Expected: `all stubs import ok`

- [ ] **Step 3: Commit**

```bash
git add backend/timeline/detectors/death_streak.py backend/timeline/detectors/recall_window.py backend/timeline/detectors/item_completion.py backend/timeline/detectors/cs_drop.py backend/timeline/detectors/vision_warning.py backend/timeline/detectors/enemy_jungle_unknown.py
git commit -m "feat(timeline): add 6 stub detectors for future implementation"
```

---

## Task 8: Wire Pipeline into `main.py`

**Files:**
- Modify: `backend/context/engine.py` — add `enrich_summary_with_events()`
- Modify: `backend/main.py` — call pipeline in `send_advice()`
- Test: `backend/tests/test_detectors.py`

- [ ] **Step 1: Write failing test for `enrich_summary_with_events`**

Append to `backend/tests/test_detectors.py`:

```python
from backend.context.engine import enrich_summary_with_events
from backend.timeline.schemas import DetectedEvent, Severity


def test_enrich_summary_adds_events():
    from backend.context.engine import build_context_packet
    state = _make_state(current_health=500, max_health=2000, gold=2600)
    packet = build_context_packet(state)
    events = [
        DetectedEvent("LOW_HEALTH", Severity.HIGH, "HP 25%", "귀환"),
        DetectedEvent("GOLD_SPIKE", Severity.HIGH, "2600골드", "아이템 구매"),
    ]
    enriched = enrich_summary_with_events(packet, events)
    assert "[DETECTED EVENTS]" in enriched.summary
    assert "LOW_HEALTH" in enriched.summary
    assert "GOLD_SPIKE" in enriched.summary


def test_enrich_summary_unchanged_with_no_events():
    state = _make_state()
    packet = build_context_packet(state)
    enriched = enrich_summary_with_events(packet, [])
    assert enriched.summary == packet.summary
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_detectors.py::test_enrich_summary_adds_events -v
```
Expected: `ImportError: cannot import name 'enrich_summary_with_events'`

- [ ] **Step 3: Add `enrich_summary_with_events` to `context/engine.py`**

Add this function at the end of `backend/context/engine.py`:

```python
from backend.timeline.schemas import DetectedEvent


def enrich_summary_with_events(packet: ContextPacket, events: list[DetectedEvent]) -> ContextPacket:
    if not events:
        return packet
    lines = ["[DETECTED EVENTS]"]
    for event in events:
        lines.append(f"- {event.event_type} ({event.severity.name}): {event.reason} → {event.recommended_action}")
    event_block = "\n".join(lines)
    return ContextPacket(
        health_percent=packet.health_percent,
        gold=packet.gold,
        level=packet.level,
        game_time_minutes=packet.game_time_minutes,
        summary=f"{event_block}\n\n{packet.summary}",
        champion_name=packet.champion_name,
        assigned_position=packet.assigned_position,
        creep_score=packet.creep_score,
    )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_detectors.py::test_enrich_summary_adds_events backend/tests/test_detectors.py::test_enrich_summary_unchanged_with_no_events -v
```
Expected: 2 PASSED

- [ ] **Step 5: Wire pipeline into `main.py`**

At the top of `backend/main.py`, add these imports after the existing imports:

```python
from backend.timeline.event_detector import EventDetectorPipeline
from backend.timeline.detectors.low_health import LowHealthDetector
from backend.timeline.detectors.gold_spike import GoldSpikeDetector
from backend.timeline.detectors.objective_timer import ObjectiveTimerDetector
from backend.timeline.detectors.death_streak import DeathStreakDetector
from backend.timeline.detectors.recall_window import RecallWindowDetector
from backend.timeline.detectors.item_completion import ItemCompletionDetector
from backend.timeline.detectors.cs_drop import CSDropDetector
from backend.timeline.detectors.vision_warning import VisionWarningDetector
from backend.timeline.detectors.enemy_jungle_unknown import EnemyJungleUnknownDetector
from backend.context.engine import enrich_summary_with_events
```

Add the pipeline instance after `active_websockets` definition (module level):

```python
_event_pipeline = EventDetectorPipeline(detectors=[
    LowHealthDetector(),
    GoldSpikeDetector(),
    ObjectiveTimerDetector(),
    DeathStreakDetector(),
    RecallWindowDetector(),
    ItemCompletionDetector(),
    CSDropDetector(),
    VisionWarningDetector(),
    EnemyJungleUnknownDetector(),
])
```

In `send_advice()`, replace:

```python
    packet = build_context_packet(game_state)
    advice = await get_advice(packet, user_query=user_query, language=language)
```

With:

```python
    packet = build_context_packet(game_state)
    detected_events = _event_pipeline.run(game_state, packet)
    packet = enrich_summary_with_events(packet, detected_events)
    advice = await get_advice(packet, user_query=user_query, language=language)
```

- [ ] **Step 6: Run full test suite to verify nothing broke**

```bash
python -m pytest backend/tests/ -v
```
Expected: all existing tests PASS + new detector tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/context/engine.py backend/main.py backend/tests/test_detectors.py
git commit -m "feat(main): wire EventDetectorPipeline into send_advice"
```

---

## Task 9: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        env:
          RIFTBUDDY_REQUIRE_ENV: "0"
          LLM_PROVIDER: mock
          RIFTBUDDY_TEST_MODE: "1"
        run: python -m pytest backend/tests/ -v
```

- [ ] **Step 2: Verify requirements.txt has pytest**

```bash
grep -i pytest requirements.txt
```
Expected: line containing `pytest`

If missing, add:
```bash
echo "pytest\npytest-asyncio" >> requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for pytest"
```

---

## Task 10: Full Verification

- [ ] **Step 1: Run complete test suite**

```bash
python -m pytest backend/tests/ -v
```
Expected: all tests PASS, no failures

- [ ] **Step 2: Verify pipeline works end-to-end with fake game state**

```bash
RIFTBUDDY_TEST_MODE=1 LLM_PROVIDER=mock python -c "
import asyncio
from backend.riot.live_client import fetch_game_state
from backend.context.engine import build_context_packet, enrich_summary_with_events
from backend.main import _event_pipeline

async def main():
    state = await fetch_game_state()
    packet = build_context_packet(state)
    events = _event_pipeline.run(state, packet)
    enriched = enrich_summary_with_events(packet, events)
    print('Events detected:', [e.event_type for e in events])
    print('Summary preview:', enriched.summary[:300])

asyncio.run(main())
"
```
Expected: prints detected events (GOLD_SPIKE likely since fake state has 2750 gold) and enriched summary with `[DETECTED EVENTS]` block.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(phase1-2): complete event detection pipeline — Phase 1+2 done"
```
