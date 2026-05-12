# Phase 4: Advice Planner — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

---

## Overview

Wire `detected_events` + `knowledge_snippets` through a `plan()` function that produces a structured `AdviceRequest`, then inject that structure into the LLM prompt as a mode/priority header.

**Files touched:**

| File | Action |
|---|---|
| `backend/advice/planner.py` | CREATE |
| `backend/tests/test_advice_planner.py` | CREATE |
| `backend/llm/advisor.py` | MODIFY |
| `backend/main.py` | MODIFY |

---

## Task 1 — RED: Write failing tests for `planner.py`

Write `backend/tests/test_advice_planner.py` before the implementation exists. All tests must fail on first run.

### Steps

- [ ] Create `backend/tests/test_advice_planner.py` with the following test cases (import `plan` from `backend.advice.planner`):

  ```
  from backend.advice.planner import plan
  from backend.advice.schemas import AdviceRequest
  from backend.timeline.schemas import DetectedEvent, Severity
  from backend.knowledge.schemas import KnowledgeSnippet
  ```

  Test cases:

  - `test_empty_events_returns_macro`: `plan([], [])` → `mode="MACRO"`, `priority_event=None`, `response_length="medium"`
  - `test_low_health_high_severity`: event `LOW_HEALTH` + `Severity.HIGH` → `mode="DEFENSIVE"`, `response_length="short"`
  - `test_gold_spike_medium_severity`: event `GOLD_SPIKE` + `Severity.MEDIUM` → `mode="RECALL"`, `response_length="medium"`
  - `test_death_streak_high_severity`: event `DEATH_STREAK` + `Severity.HIGH` → `mode="DEFENSIVE"`, `response_length="short"`
  - `test_objective_spawn_low_severity`: event `OBJECTIVE_SPAWN` + `Severity.LOW` → `mode="MACRO"`, `response_length="medium"`
  - `test_unknown_event_type_defaults_macro`: event `"WARD_KILL"` + `Severity.MEDIUM` → `mode="MACRO"`, `response_length="medium"`
  - `test_knowledge_snippets_passed_through`: snippets list is present verbatim in returned `AdviceRequest.knowledge_snippets`
  - `test_priority_event_is_first_event`: when multiple events provided, `priority_event` is the first in the list

- [ ] Confirm tests fail (module not found is acceptable at this stage):

  ```
  pytest backend/tests/test_advice_planner.py -v
  ```

  Expected: `ImportError` or `ModuleNotFoundError` for `backend.advice.planner`.

---

## Task 2 — GREEN: Implement `backend/advice/planner.py`

- [ ] Create `backend/advice/planner.py`:

  ```python
  from backend.advice.schemas import AdviceRequest
  from backend.timeline.schemas import DetectedEvent, Severity
  from backend.knowledge.schemas import KnowledgeSnippet

  _MODE_MAP: dict[str, str] = {
      "LOW_HEALTH": "DEFENSIVE",
      "GOLD_SPIKE": "RECALL",
      "OBJECTIVE_SPAWN": "MACRO",
      "DEATH_STREAK": "DEFENSIVE",
  }

  def plan(events: list[DetectedEvent], snippets: list[KnowledgeSnippet]) -> AdviceRequest:
      top_event = events[0] if events else None
      mode = _decide_mode(top_event)
      length = "short" if top_event and top_event.severity == Severity.HIGH else "medium"
      return AdviceRequest(
          mode=mode,
          priority_event=top_event,
          knowledge_snippets=snippets,
          response_length=length,
      )

  def _decide_mode(event: DetectedEvent | None) -> str:
      if not event:
          return "MACRO"
      return _MODE_MAP.get(event.event_type, "MACRO")
  ```

- [ ] Run tests — all must pass (GREEN):

  ```
  pytest backend/tests/test_advice_planner.py -v
  ```

---

## Task 3 — Structured prompt injection in `backend/llm/advisor.py`

### Steps

- [ ] Add `build_structured_prompt(request: AdviceRequest, language: str) -> str` function. The function builds a header block like:

  ```
  [MODE: DEFENSIVE]
  [PRIORITY: LOW_HEALTH — <reason>]
  [KNOWLEDGE: <first snippet content>]
  ```

  Rules:
  - `[MODE: {request.mode}]` always present
  - `[PRIORITY: ...]` line only when `request.priority_event is not None`; format: `{event_type} — {reason}`
  - `[KNOWLEDGE: ...]` line for each snippet in `request.knowledge_snippets` (one line per snippet, `{source}: {content}`)
  - Return the full block as a single string (lines joined by `\n`)

- [ ] Modify `build_user_content` signature to accept an optional param:

  ```python
  def build_user_content(
      packet: ContextPacket,
      user_query: Optional[str],
      language: str = "en",
      advice_request: "AdviceRequest | None" = None,
  ) -> str:
  ```

  When `advice_request` is not None, prepend `build_structured_prompt(advice_request, language) + "\n\n"` before the existing content block.

- [ ] Add the `AdviceRequest` import at the top of `advisor.py` (TYPE_CHECKING guard to avoid circular imports if needed):

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from backend.advice.schemas import AdviceRequest
  ```

  If no circular import risk exists after checking, import directly instead.

- [ ] Update the three provider functions and `get_advice` to accept and forward `advice_request`:

  ```python
  async def get_anthropic_advice(
      packet: ContextPacket,
      user_query: Optional[str],
      language: str = "en",
      advice_request: "AdviceRequest | None" = None,
  ) -> str:
      user_content = build_user_content(packet, user_query, language, advice_request=advice_request)
      ...

  async def get_groq_advice(
      packet: ContextPacket,
      user_query: Optional[str],
      language: str = "en",
      advice_request: "AdviceRequest | None" = None,
  ) -> str:
      ...
      "messages": [
          {"role": "system", "content": _system_prompt(language)},
          {"role": "user", "content": build_user_content(packet, user_query, language, advice_request=advice_request)},
      ],
      ...

  async def get_gemini_advice(
      packet: ContextPacket,
      user_query: Optional[str],
      language: str = "en",
      advice_request: "AdviceRequest | None" = None,
  ) -> str:
      ...
      "contents": [{"parts": [{"text": build_user_content(packet, user_query, language, advice_request=advice_request)}]}],
      ...

  async def get_advice(
      packet: ContextPacket,
      user_query: Optional[str],
      language: str = "en",
      advice_request: "AdviceRequest | None" = None,
  ) -> str:
      # dispatch to provider, forwarding advice_request
  ```

- [ ] Verify no existing tests broke:

  ```
  pytest backend/tests/ -v
  ```

---

## Task 4 — Wire planner into `backend/main.py`

### Steps

- [ ] Add import at top of `backend/main.py`:

  ```python
  from backend.advice.planner import plan
  ```

- [ ] In `send_advice()`, replace the existing knowledge injection block:

  **Remove** (lines ~191–200):
  ```python
  if knowledge_snippets:
      knowledge_block = "\n".join(
          f"[KNOWLEDGE] {s.source}: {s.content}" for s in knowledge_snippets
      )
      packet = ContextPacket(
          ...
          summary=f"{knowledge_block}\n\n{packet.summary}",
          ...
      )
  ```

  **Replace with:**
  ```python
  advice_request = plan(detected_events, knowledge_snippets)
  ```

- [ ] Update the `get_advice` call to pass `advice_request`:

  ```python
  advice = await get_advice(packet, user_query=user_query, language=language, advice_request=advice_request)
  ```

- [ ] Run full test suite to confirm nothing regressed:

  ```
  pytest backend/tests/ -v
  ```

---

## Verification

```bash
# Planner unit tests only
pytest backend/tests/test_advice_planner.py -v

# Full suite — must all pass
pytest backend/tests/ -v
```

Expected: all planner tests green, no regressions in existing tests.

---

## Success Criteria

- `plan([], [])` returns `AdviceRequest(mode="MACRO", priority_event=None, response_length="medium")`
- `plan([LOW_HEALTH HIGH], [...])` returns `mode="DEFENSIVE"`, `response_length="short"`
- `get_advice(packet, ..., advice_request=None)` behaves identically to old signature (backward compatible)
- `build_user_content` with a non-None `advice_request` prepends mode/priority/knowledge header
- `send_advice` in `main.py` no longer contains the manual `[KNOWLEDGE]` prefix loop
- `pytest backend/tests/ -v` passes in full
