# AI Backend Infra Portfolio Strategy

**For:** Seoungmin Kim  
**Goal:** Reposition existing projects into a focused AI Backend / AI Platform / Infrastructure Engineering portfolio  
**Main narrative:**

> I build production-minded AI systems that connect models to real users, real workflows, and reliable backend infrastructure.

This document is not a brand-new project plan. It is a strategy for upgrading the existing projects so they clearly signal **AI Backend Infrastructure** instead of looking like disconnected AI/product prototypes.

---

## 0. Portfolio Positioning

### Current 4 Projects

| Project   | Current Strength                                           | Current Weakness                          | AI Backend Infra Upgrade Direction                              |
| --------- | ---------------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------- |
| RiftBuddy | Real-time LLM product, gaming, WebSocket, Electron overlay | Looks more like AI app/product than infra | Add LLM gateway, RAG service, evals, observability, Redis queue |

### Desired Recruiter Impression

Instead of:

> “This student built many different AI apps.”

The portfolio should communicate:

> “This engineer can build backend systems around AI models: routing, retrieval, evaluation, monitoring, reliability, workflow automation, and human-in-the-loop review.”

---

## 1. Core AI Backend Infra Skills to Show

Across the RiftBuddy project, try to show these capabilities repeatedly:

### AI System Layer

- LLM provider routing
- model fallback
- prompt versioning
- token and cost tracking
- response caching
- RAG / vector retrieval
- AI eval pipeline
- hallucination or quality checks
- safety guardrails
- human-in-the-loop workflow

### Backend Infrastructure Layer

- FastAPI service design
- WebSocket streaming
- Redis queue / background jobs
- PostgreSQL data modeling
- idempotency
- retry-safe state transitions
- RBAC / auth
- audit logs
- metrics endpoint
- Prometheus / Grafana
- structured logging
- Docker / Kubernetes deployment
- CI/CD

### Product/Platform Layer

- real user workflow
- admin dashboard
- non-technical user support
- evaluation dashboards
- demo videos
- architecture diagrams
- clear README storytelling

---

# Project 1: RiftBuddy AI Inference Platform

## Target Positioning

Current positioning:

> AI League of Legends coach app.

New positioning:

> Real-time AI inference platform for game coaching, combining live telemetry, LLM routing, retrieval, evaluation, and observability.

This should become your strongest **AI Backend Infra flagship**.

---

## Why RiftBuddy Is Important

RiftBuddy already has:

- live game telemetry
- WebSocket communication
- LLM provider integration
- Electron overlay
- real-time user interaction

That means it can naturally become a production-style AI system if you add infrastructure around the LLM calls.

---

## Upgrade 1: LLM Gateway

### Goal

Turn simple provider abstraction into a real AI gateway.

### Add Folder

```text
backend/ai_gateway/
    __init__.py
    router.py
    schemas.py
    fallback.py
    rate_limiter.py
    cost_tracker.py
    prompt_registry.py
    providers/
        anthropic.py
        gemini.py
        groq.py
        mock.py
```

### Features

- provider routing: Anthropic, Gemini, Groq, mock
- timeout handling
- fallback provider on error
- retry policy
- token usage tracking
- estimated cost tracking
- request/response metadata logging
- model latency histogram
- prompt version tracking

### Example AI Gateway Response

```json
{
  "provider": "anthropic",
  "model": "claude-sonnet",
  "prompt_version": "in_game_advice_v3",
  "latency_ms": 1840,
  "fallback_used": false,
  "input_tokens": 842,
  "output_tokens": 71,
  "estimated_cost_usd": 0.0041,
  "advice": "You have enough gold for a spike. Push one safe wave and reset before dragon."
}
```

### Resume Bullet

> Built an LLM gateway for a real-time coaching system with provider routing, fallback handling, rate limiting, token-cost tracking, and latency metrics across multiple model providers.

---

## Upgrade 2: RAG / Champion Knowledge Service

### Goal

Make advice grounded in structured champion, item, and matchup knowledge.

### Add Folder

```text
backend/rag/
    ingest.py
    retriever.py
    vector_store.py
    schemas.py
    eval.py
    data/
        champions/
        matchups/
        macro_rules/
```

### Features

- champion profile ingestion
- matchup notes ingestion
- top-k retrieval
- query normalization
- retrieval latency tracking
- retrieval eval tests

### Example Knowledge Object

```json
{
  "champion": "Rumble",
  "role": "TOP",
  "identity": "AP lane bully with strong level 6 objective fight",
  "spikes": ["Level 6", "Liandry completion", "Sorcerer Shoes"],
  "weaknesses": ["No dash", "vulnerable to ganks when pushed"],
  "rules": [
    "Track enemy jungler before overheating for trades",
    "Use Equalizer for objective choke points"
  ]
}
```

### Resume Bullet

> Added a lightweight RAG service that retrieves champion matchup and macro knowledge to ground real-time LLM coaching advice in game-specific context.

---

## Upgrade 3: Event Detector Layer

### Goal

Do not send raw game state directly to an LLM. Detect important game events first.

### Add Folder

```text
backend/timeline/
    event_detector.py
    objective_tracker.py
    session_store.py
    schemas.py
```

### Event Types

```text
LOW_HEALTH_WARNING
GOLD_SPIKE
OBJECTIVE_SPAWN_SOON
BAD_RECALL_WINDOW
DEATH_STREAK
ITEM_COMPLETION
VISION_DANGER
CS_DROP
LANE_PRESSURE_LOST
```

### Example Event

```json
{
  "event_type": "GOLD_SPIKE",
  "severity": "HIGH",
  "reason": "Player has 2750 unspent gold before dragon spawn",
  "recommended_action": "Push one wave and reset before objective setup"
}
```

### Resume Bullet

> Designed a game-event detection layer that transforms live telemetry into prioritized coaching signals before passing context to the LLM.

---

## Upgrade 4: AI Evaluation Pipeline

### Goal

Show that you understand AI quality testing, not just AI feature building.

### Add Folder

```text
evals/
    scenarios/
        low_health.json
        objective_spawn.json
        high_gold.json
        enemy_missing.json
    run_evals.py
    report.md
```

### Eval Metrics

- context usage
- advice relevance
- response length
- Korean LoL terminology correctness
- hallucination rate
- latency
- fallback behavior

### README Table Example

| Metric                       | Result |
| ---------------------------- | -----: |
| Scenario tests passed        |  42/45 |
| Avg LLM latency              |   2.1s |
| Fallback success rate        |   100% |
| Context-grounded advice      |    91% |
| Korean terminology pass rate |    96% |

### Resume Bullet

> Built an automated LLM evaluation suite to test advice relevance, latency, fallback behavior, and context-groundedness across simulated game scenarios.

---

## Upgrade 5: Observability

### Goal

Make the project look like a real production AI service.

### Add

- `/metrics` endpoint
- Prometheus metrics
- structured JSON logs
- request IDs
- Grafana dashboard screenshot

### Metrics

```text
riftbuddy_llm_requests_total{provider="anthropic"}
riftbuddy_llm_latency_seconds
riftbuddy_llm_failures_total
riftbuddy_llm_fallback_total
riftbuddy_websocket_connections
riftbuddy_advice_events_total{event_type="LOW_HEALTH"}
rfitbuddy_token_usage_total
```

### Resume Bullet

> Added Prometheus metrics and structured logging to monitor LLM latency, provider failures, token usage, WebSocket connections, and real-time advice events.

---

## Final RiftBuddy README Headline

```md
# RiftBuddy — Real-time AI Inference Platform for League Coaching

RiftBuddy turns live League of Legends telemetry into real-time coaching advice using an LLM gateway, game-event detection, champion knowledge retrieval, WebSocket streaming, and AI evaluation pipelines.
```

---

# Final Resume Bullets by Project

## RiftBuddy

> Built a real-time AI inference platform for League coaching with FastAPI, WebSockets, Electron, an LLM gateway, provider fallback, RAG-based champion knowledge retrieval, and Prometheus latency metrics.

## RiftBuddy AI Gateway

- Add `backend/ai_gateway/`
- Add provider fallback
- Add token/cost tracking
- Add latency logging
- Add README architecture diagram

Deliverable:

```text
RiftBuddy looks like an AI backend system, not just an AI app.
```

---

## RiftBuddy RAG + Evals

- Add champion/matchup knowledge base
- Add retrieval service
- Add eval scenarios
- Add eval report

Deliverable:

```text
RiftBuddy demonstrates RAG + AI evaluation.
```

---

## GOAL

The goal is not more repos. The goal is:

- clearer narrative
- stronger README files
- better architecture diagrams
- working demos
- measurable metrics
- tests and CI
- production-minded design

A recruiter should be able to look at your GitHub and think:

> This person can build AI systems around real products, with backend reliability, observability, and infra maturity.

---

# Final North Star

Your portfolio should say:

> I am not just building AI demos. I am building the backend infrastructure that makes AI products reliable, measurable, safe, and useful.
