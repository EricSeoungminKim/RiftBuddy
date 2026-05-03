# RiftBuddy

RiftBuddy is a League of Legends companion MVP that polls the Riot Live Client API, builds a compact game context, asks an LLM for advice, and streams advice plus TTS audio to an Electron overlay.

## Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn backend.main:app --reload --port 8001
```

Health check:

```bash
curl http://localhost:8001/health
```

LCU champion-select status check:

```bash
curl http://localhost:8001/lcu/champ-select/status
```

Expected states:

- League closed: `200 OK` with `available: false`, `inProgress: false`
- League open but not in champ select: `200 OK` with `available: true`, `inProgress: false`
- Champ select active: `200 OK` with `available: true`, `inProgress: true`, plus `allySlots` / `enemySlots`

## Frontend

```bash
cd frontend
npm install
npm run overlay
```

Useful hotkeys:

- `Command/Ctrl + Shift + D`: show/hide Draft Window
- Draft Window auto-opens when champ select starts
- `Command/Ctrl + Shift + B`: planned in-game advice
- `Command/Ctrl + Shift + Space`: custom voice question
- `Command/Ctrl + Shift + [` / `]`: switch overlay tabs

## Tests

```bash
python3 -m pytest -q
```
