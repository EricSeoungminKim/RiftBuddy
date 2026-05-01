import asyncio
import json
import logging
from contextlib import suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.auth.supabase_client import verify_token
from backend.config import CONFIG
from backend.context.engine import build_context_packet
from backend.llm.advisor import get_advice
from backend.riot.live_client import fetch_game_state
from backend.voice.tts import text_to_speech_bytes
from backend.voice.wake_word import run_wake_word_loop

app = FastAPI(title="RiftBuddy Backend")
logger = logging.getLogger(__name__)
active_websockets: set[WebSocket] = set()
wake_word_task: asyncio.Task | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup() -> None:
    global wake_word_task
    if CONFIG["wake_word"] == "1":
        wake_word_task = asyncio.create_task(run_wake_word_loop(broadcast_wake_ack, broadcast_voice_question))


@app.on_event("shutdown")
async def shutdown() -> None:
    if wake_word_task:
        wake_word_task.cancel()
        with suppress(asyncio.CancelledError):
            await wake_word_task


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    should_bypass_auth = CONFIG["test_mode"] == "1" or CONFIG["bypass_auth"] == "1"
    user = {"id": "dev-user"} if should_bypass_auth else await verify_token(token) if token else None
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            user_query = msg.get("query")
            language = msg.get("language") or CONFIG["response_language"]

            await send_advice(websocket, user_query=user_query, language=language)
    except WebSocketDisconnect:
        pass
    finally:
        active_websockets.discard(websocket)


async def broadcast_wake_ack(transcript: str) -> None:
    for websocket in list(active_websockets):
        await websocket.send_json({"type": "transcript", "text": transcript})
        await websocket.send_json({"type": "listening", "text": "네?"})


async def broadcast_voice_question(question: str) -> None:
    for websocket in list(active_websockets):
        await websocket.send_json({"type": "transcript", "text": question})
        await send_advice(websocket, user_query=question, language=CONFIG["response_language"])


async def send_advice(websocket: WebSocket, user_query: str | None, language: str) -> None:
    game_state = await fetch_game_state()
    if game_state is None:
        await websocket.send_json({"type": "error", "message": "Game not running"})
        return

    packet = build_context_packet(game_state)
    advice = await get_advice(packet, user_query=user_query, language=language)
    audio_bytes = None
    audio_error = None
    try:
        audio_bytes = await text_to_speech_bytes(advice)
    except Exception as exc:
        logger.warning("TTS failed; sending text advice without audio: %s", exc)
        audio_error = "Voice output unavailable. Check ElevenLabs credits, billing, or API permissions."

    await websocket.send_json(
        {
            "type": "advice",
            "text": advice,
            "audio_error": audio_error,
            "context": {
                "health_percent": packet.health_percent,
                "gold": packet.gold,
                "level": packet.level,
                "game_time_minutes": packet.game_time_minutes,
            },
        }
    )
    if audio_bytes:
        await websocket.send_bytes(audio_bytes)
