import asyncio
import json
import logging
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.draft.router import router as draft_router
from backend.lcu.router import router as lcu_router
from backend.postgame.router import router as postgame_router
from backend.postgame.router import game_session as _game_session
from backend.config import CONFIG
from pathlib import Path
from backend.context.engine import build_context_packet, enrich_summary_with_events, ContextPacket
from backend.knowledge.embedder import get_or_build_collection
from backend.knowledge.retriever import retrieve
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
from backend.context.question_planner import build_planned_question
from backend.llm.advisor import get_advice
from backend.riot.live_client import fetch_game_state, GameState
from backend.voice.stt import is_valid_transcript
from backend.voice.tts import text_to_speech_bytes
from backend.voice.wake_word import capture_voice_question_once, run_wake_word_loop

logger = logging.getLogger(__name__)
active_websockets: set[WebSocket] = set()
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
_knowledge_collection = None
wake_word_task: asyncio.Task | None = None
_game_poll_task: asyncio.Task | None = None


async def _start_wake_word_task() -> None:
    global wake_word_task
    if CONFIG["wake_word"] == "1":
        wake_word_task = asyncio.create_task(run_wake_word_loop(broadcast_wake_ack, broadcast_voice_question))


async def _stop_wake_word_task() -> None:
    if wake_word_task:
        wake_word_task.cancel()
        with suppress(asyncio.CancelledError):
            await wake_word_task


def _game_state_to_ws_payload(state: GameState) -> dict:
    return {
        "type": "game_state",
        "gameTime": state.game_time,
        "championName": state.champion_name,
        "summonerName": state.summoner_name,
        "position": state.assigned_position,
        "health": state.current_health,
        "maxHealth": state.max_health,
        "gold": state.gold,
        "level": state.level,
        "kills": state.kills,
        "deaths": state.deaths,
        "assists": state.assists,
        "cs": state.creep_score,
        "wardScore": state.ward_score,
        "items": list(state.items),
        "summonerSpells": list(state.summoner_spells),
        "recentEvents": list(state.recent_events),
        "allyGold": state.ally_gold,
        "enemyGold": state.enemy_gold,
        "goldDiff": state.gold_diff,
        "allyChampions": list(state.ally_champions),
        "enemyChampions": list(state.enemy_champions),
    }


async def _poll_game_state() -> None:
    while True:
        await asyncio.sleep(3)
        try:
            state = await fetch_game_state()
        except Exception as exc:
            logger.warning("Game state poll error: %s", exc)
            continue
        if state is None:
            continue
        payload = _game_state_to_ws_payload(state)
        for ws in list(active_websockets):
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning("WS broadcast failed, removing: %s", exc)
                active_websockets.discard(ws)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _game_poll_task, _knowledge_collection
    _knowledge_collection = get_or_build_collection(
        data_dir=Path("backend/knowledge/data"),
        db_path=Path(".chroma_db"),
    )
    await _start_wake_word_task()
    _game_poll_task = asyncio.create_task(_poll_game_state())
    try:
        yield
    finally:
        await _stop_wake_word_task()
        if _game_poll_task:
            _game_poll_task.cancel()
            with suppress(asyncio.CancelledError):
                await _game_poll_task


app = FastAPI(title="RiftBuddy Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(draft_router)
app.include_router(lcu_router)
app.include_router(postgame_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action", "advice")
            user_query = msg.get("query")
            mode = msg.get("mode")
            language = msg.get("language") or CONFIG["response_language"]

            if action == "listen":
                await websocket.send_json(
                    {
                        "type": "listening",
                        "text": "준비하세요. 곧 말하면 됩니다..." if language == "ko" else "Get ready. Speak in a moment...",
                    }
                )
                await asyncio.sleep(float(CONFIG["question_prepare_seconds"]))
                await websocket.send_json(
                    {
                        "type": "listening",
                        "text": "Buddy가 듣고 있습니다..." if language == "ko" else "Buddy is listening...",
                    }
                )
                question = await capture_voice_question_once()
                if not is_valid_transcript(question):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "질문을 제대로 듣지 못했습니다. 다시 눌러 말해주세요."
                            if language == "ko"
                            else "I could not hear the question. Press the hotkey and try again.",
                        }
                    )
                    continue
                await websocket.send_json({"type": "transcript", "text": question})
                await send_advice(websocket, user_query=question, language=language)
            else:
                await send_advice(websocket, user_query=user_query, language=language, planned=mode == "planned")
    except WebSocketDisconnect:
        pass
    finally:
        active_websockets.discard(websocket)


async def broadcast_wake_ack(transcript: str) -> None:
    for websocket in list(active_websockets):
        await websocket.send_json({"type": "transcript", "text": transcript})
        await websocket.send_json({"type": "listening", "text": "Buddy가 듣고 있습니다..."})


async def broadcast_voice_question(question: str) -> None:
    for websocket in list(active_websockets):
        await websocket.send_json({"type": "transcript", "text": question})
        await send_advice(websocket, user_query=question, language=CONFIG["response_language"])


async def send_advice(websocket: WebSocket, user_query: str | None, language: str, planned: bool = False) -> None:
    game_state = await fetch_game_state()
    if game_state is None:
        await websocket.send_json({"type": "error", "message": "Game not running"})
        if not _game_session.is_empty:
            for ws in list(active_websockets):
                try:
                    await ws.send_json({"type": "game_end"})
                except Exception:
                    pass
            _game_session.clear()
        return

    _game_session.add_snapshot(game_state)

    if planned and not user_query:
        user_query = build_planned_question(game_state, language)
        await websocket.send_json({"type": "transcript", "text": user_query})

    packet = build_context_packet(game_state)
    detected_events = _event_pipeline.run(game_state, packet)
    packet = enrich_summary_with_events(packet, detected_events)
    knowledge_snippets = retrieve(
        champion=game_state.champion_name,
        lane_opponent=game_state.lane_opponent,
        fed_enemy=game_state.fed_enemy,
        collection=_knowledge_collection,
    ) if _knowledge_collection is not None else []
    if knowledge_snippets:
        knowledge_block = "\n".join(
            f"[KNOWLEDGE] {s.source}: {s.content}" for s in knowledge_snippets
        )
        packet = ContextPacket(
            health_percent=packet.health_percent,
            gold=packet.gold,
            level=packet.level,
            game_time_minutes=packet.game_time_minutes,
            summary=f"{knowledge_block}\n\n{packet.summary}",
            champion_name=packet.champion_name,
            assigned_position=packet.assigned_position,
            creep_score=packet.creep_score,
        )
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
