# RiftBuddy Demo Guide

This demo runs without a live League of Legends game and without paid LLM calls.

## 1. Start the backend

From the repository root:

```bash
source .venv/bin/activate
RIFTBUDDY_TEST_MODE=1 LLM_PROVIDER=mock python -m uvicorn backend.main:app --reload --port 8001
```

Verify:

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{ "status": "ok" }
```

## 2. Start the Electron overlay

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The overlay connects to `ws://127.0.0.1:8001/ws`.

## 3. Demo flow

Use these hotkeys while the overlay is open:

| Step | Hotkey                      | What to show                                                      |
| ---- | --------------------------- | ----------------------------------------------------------------- |
| 1    | `Command/Ctrl + Shift + B`  | General planned advice from mock game state                       |
| 2    | `Command/Ctrl + Shift + C`  | OP.GG matchup response, tagged as OP.GG in chat                   |
| 3    | `Command/Ctrl + Shift + 1`  | Item recommendation                                               |
| 4    | `Command/Ctrl + Shift + 2`  | Macro/objective advice                                            |
| 5    | Wait during seeded sessions | Proactive warning appears as an in-chat alert, not a separate tab |

## 4. What reviewers should notice

- The AI coach chat distinguishes regular advice, OP.GG answers, and proactive warnings in one compact overlay.
- Advice is generated from a structured pipeline, not a single generic prompt.
- Demo mode uses `RIFTBUDDY_TEST_MODE=1` for fake game telemetry and `LLM_PROVIDER=mock` for deterministic responses.
- In real API mode, post-game seed enrichment can build Riot Match-V5 CS benchmarks with `RIOT_API_KEY`, `RIOT_BENCHMARK_TIER`, and `RIOT_BENCHMARK_SAMPLES`.
- The eval suite can be run locally:

```bash
python evals/run_evals.py
```

Current expected summary:

```text
Summary: 6/6 passed — avg latency 0ms
```

## 5. Recording checklist

- Start recording after both backend and frontend are running.
- Trigger the four hotkeys in order: `B`, `C`, `1`, `2`.
- Keep the overlay visible long enough to show message source badges and timestamps.
- End with the eval command output or README architecture diagram.
