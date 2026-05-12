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
from backend.advice.planner import plan
from backend.riot.live_client import fetch_game_state, GameState
from backend.opgg.client import get_matchup_guide, get_champion_counters, infer_lane_opponent
from backend.opgg.snippets import matchup_guide_to_snippet, fed_enemy_to_snippet

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
_performance_collection = None
_game_poll_task: asyncio.Task | None = None
_cached_lane_opponent: str | None = None  # inferred once per game session
_lane_opponent_cache_key: str = ""        # "champion:position:enemies" to detect new game


def get_knowledge_collection():
    return _knowledge_collection


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


async def _refresh_lane_opponent_cache(state: GameState) -> None:
    """Infer lane opponent via OP.GG role_rate once per unique game lineup."""
    global _cached_lane_opponent, _lane_opponent_cache_key
    enemy_list = list(state.enemy_champions)
    cache_key = f"{state.champion_name}:{state.assigned_position}:{','.join(sorted(enemy_list))}"
    if cache_key == _lane_opponent_cache_key or not enemy_list:
        return
    _lane_opponent_cache_key = cache_key
    try:
        inferred = await infer_lane_opponent(enemy_list, state.assigned_position)
        _cached_lane_opponent = inferred
        logger.info("Lane opponent inferred: %s (position=%s)", inferred, state.assigned_position)
    except Exception as exc:
        logger.warning("Lane opponent inference failed: %s", exc)
        _cached_lane_opponent = None


async def _poll_game_state() -> None:
    while True:
        await asyncio.sleep(3)
        try:
            state = await fetch_game_state()
        except Exception as exc:
            logger.warning("Game state poll error: %s", exc)
            continue
        if state is None:
            _lane_opponent_cache_key = ""  # reset on game end
            continue
        asyncio.create_task(_refresh_lane_opponent_cache(state))
        payload = _game_state_to_ws_payload(state)
        for ws in list(active_websockets):
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning("WS broadcast failed, removing: %s", exc)
                active_websockets.discard(ws)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _game_poll_task, _knowledge_collection, _performance_collection
    _knowledge_collection = get_or_build_collection(
        data_dir=Path("backend/knowledge/data"),
        db_path=Path(".chroma_db"),
    )
    import chromadb as _chromadb_mod
    _perf_client = _chromadb_mod.PersistentClient(path=".chroma_db")
    _performance_collection = _perf_client.get_or_create_collection("performance_seeds")
    _game_poll_task = asyncio.create_task(_poll_game_state())
    try:
        yield
    finally:
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

            if action == "matchup":
                await send_advice(websocket, user_query="상대 챔피언 매치업과 OP.GG 통계를 알려줘.", language=language, planned=False, opgg_only=True)
            elif action == "items":
                await send_advice(websocket, user_query="지금 뭘 사야 해? 아이템 추천해줘.", language=language, planned=False)
            elif action == "macro":
                await send_advice(websocket, user_query="오브젝트 타이밍과 지금 매크로 플레이를 알려줘.", language=language, planned=False)
            else:
                await send_advice(websocket, user_query=user_query, language=language, planned=mode == "planned")
    except WebSocketDisconnect:
        pass
    finally:
        active_websockets.discard(websocket)


async def _fetch_opgg_snippets(state: GameState) -> list:
    from backend.knowledge.schemas import KnowledgeSnippet

    # lane opponent: prefer cached role_rate inference, fallback to live_client guess
    opponent = _cached_lane_opponent or (
        state.lane_opponent
        if state.lane_opponent and state.lane_opponent != "Unknown"
        else None
    )
    fed = state.fed_enemy if state.fed_enemy and state.fed_enemy != "Unknown" else None

    tasks: list = []
    task_labels: list[str] = []

    if opponent:
        tasks.append(get_matchup_guide(state.champion_name, opponent, state.assigned_position))
        task_labels.append("matchup")
    elif fed:
        # fallback: focus on the most fed enemy instead
        tasks.append(get_champion_counters(fed, state.assigned_position))
        task_labels.append("fed_enemy")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    snippets: list[KnowledgeSnippet] = []
    for label, result in zip(task_labels, results):
        if isinstance(result, Exception) or not result:
            continue
        if label == "matchup":
            s = matchup_guide_to_snippet(result, state.champion_name, opponent)
        elif label == "fed_enemy":
            s = fed_enemy_to_snippet(result, fed)
        else:
            continue
        if s:
            snippets.append(s)
    return snippets


async def send_advice(websocket: WebSocket, user_query: str | None, language: str, planned: bool = False, opgg_only: bool = False) -> None:
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
    opgg_snippets = await _fetch_opgg_snippets(game_state)

    if opgg_only:
        knowledge_snippets = opgg_snippets
    else:
        rag_snippets = retrieve(
            champion=game_state.champion_name,
            lane_opponent=game_state.lane_opponent,
            fed_enemy=game_state.fed_enemy,
            collection=_knowledge_collection,
            performance_collection=_performance_collection,
        ) if _knowledge_collection is not None else []
        knowledge_snippets = opgg_snippets + rag_snippets

    advice_request = plan(detected_events, knowledge_snippets)
    advice = await get_advice(packet, user_query=user_query, language=language, advice_request=advice_request)
    await websocket.send_json(
        {
            "type": "advice",
            "text": advice,
            "context": {
                "health_percent": packet.health_percent,
                "gold": packet.gold,
                "level": packet.level,
                "game_time_minutes": packet.game_time_minutes,
            },
        }
    )
