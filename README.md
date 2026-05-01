# RiftBuddy

RiftBuddy is a League of Legends companion MVP that polls the Riot Live Client API, builds a compact game context, asks an LLM for advice, and streams advice plus TTS audio to an Electron overlay.

## Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

## Frontend

```bash
cd frontend
npm install
NODE_ENV=development npm run dev
```

## Tests

```bash
python -m pytest backend/tests -v
```
