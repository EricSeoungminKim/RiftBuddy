import asyncio
import json
import logging
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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
from backend.stats.riot_cs_benchmarks import fetch_cs_benchmark, normalize_position
from backend.timeline.proactive_coach import ProactiveCoachSession, generate_proactive_warning
from backend.knowledge.performance_seeds import save_game_seed

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
_draft_context: "DraftContext | None" = None
_proactive_session: ProactiveCoachSession | None = None
_proactive_session_key: str = ""          # "champion:position" to detect new game
_was_game_running = False
_last_session_snapshot_game_time: float | None = None
_game_end_sent = False
SESSION_SNAPSHOT_INTERVAL_SECONDS = 30.0


class DraftContext(BaseModel):
    my_champion: str
    my_position: str
    lane_opponent: str | None = None


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
    draft_opponent = _draft_lane_opponent_for_state(state)
    if draft_opponent:
        _lane_opponent_cache_key = cache_key
        _cached_lane_opponent = draft_opponent
        logger.info("Lane opponent from draft context: %s", draft_opponent)
        return
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


def _normalize_position(position: str) -> str:
    normalized = position.strip().upper()
    return {
        "TOP": "TOP",
        "JUNGLE": "JUNGLE",
        "MIDDLE": "MIDDLE",
        "MID": "MIDDLE",
        "BOTTOM": "BOTTOM",
        "ADC": "BOTTOM",
        "UTILITY": "UTILITY",
        "SUPPORT": "UTILITY",
        "탑": "TOP",
        "정글": "JUNGLE",
        "미드": "MIDDLE",
        "바텀": "BOTTOM",
        "서폿": "UTILITY",
    }.get(normalized, normalized)


def _draft_lane_opponent_for_state(state: GameState) -> str | None:
    if _draft_context is None or not _draft_context.lane_opponent:
        return None
    if _draft_context.my_champion.strip().lower() != state.champion_name.strip().lower():
        return None
    if _normalize_position(_draft_context.my_position) != _normalize_position(state.assigned_position):
        return None
    return _draft_context.lane_opponent


async def _ensure_proactive_session(state: GameState) -> None:
    """Load danger windows from past seeds once per champion+position combo."""
    global _proactive_session, _proactive_session_key
    key = f"{state.champion_name}:{state.assigned_position}"
    if key == _proactive_session_key:
        return
    _proactive_session_key = key
    session = ProactiveCoachSession(
        champion=state.champion_name,
        position=state.assigned_position,
    )
    if _performance_collection is not None:
        try:
            await session.load(_performance_collection)
            logger.info(
                "Proactive coach loaded %d danger windows for %s",
                len(session.windows),
                state.champion_name,
            )
        except Exception as exc:
            logger.warning("Proactive coach load failed: %s", exc)
    _proactive_session = session


async def _run_proactive_checks(state: GameState) -> None:
    """Check if any danger window triggers and push warnings to all WebSocket clients."""
    if _proactive_session is None or not _proactive_session.loaded:
        return
    fired = _proactive_session.check(state.game_time)
    language = CONFIG.get("response_language", "ko")
    for window in fired:
        try:
            warning_text = await generate_proactive_warning(
                window,
                champion=state.champion_name,
                position=state.assigned_position,
                language=language,
            )
            payload = {"type": "proactive_warning", "text": warning_text}
            for ws in list(active_websockets):
                try:
                    await ws.send_json(payload)
                except Exception:
                    active_websockets.discard(ws)
        except Exception as exc:
            logger.warning("Proactive warning generation failed: %s", exc)


def _record_session_snapshot(state: GameState, *, force: bool = False) -> bool:
    global _last_session_snapshot_game_time
    if force or _last_session_snapshot_game_time is None:
        _game_session.add_snapshot(state)
        _last_session_snapshot_game_time = state.game_time
        return True
    if state.game_time < _last_session_snapshot_game_time:
        _game_session.clear()
        _game_session.add_snapshot(state)
        _last_session_snapshot_game_time = state.game_time
        return True
    if state.game_time - _last_session_snapshot_game_time >= SESSION_SNAPSHOT_INTERVAL_SECONDS:
        _game_session.add_snapshot(state)
        _last_session_snapshot_game_time = state.game_time
        return True
    return False


async def _broadcast_game_end() -> None:
    global _game_end_sent
    if _game_end_sent:
        return
    _game_end_sent = True
    if _performance_collection is not None and not _game_session.is_empty and not _game_session.seed_doc_id:
        try:
            _game_session.seed_doc_id = save_game_seed(_game_session, _performance_collection)
            logger.info("Auto-saved performance seed: %s", _game_session.seed_doc_id)
        except Exception as exc:
            logger.warning("Auto-save performance seed failed: %s", exc)
    for ws in list(active_websockets):
        try:
            await ws.send_json({"type": "game_end"})
        except Exception:
            active_websockets.discard(ws)


def _reset_live_game_state() -> None:
    global _cached_lane_opponent, _lane_opponent_cache_key, _draft_context, _proactive_session_key, _last_session_snapshot_game_time
    _cached_lane_opponent = None
    _lane_opponent_cache_key = ""
    _draft_context = None
    _proactive_session_key = ""
    _last_session_snapshot_game_time = None


async def _poll_game_state() -> None:
    global _was_game_running, _game_end_sent
    while True:
        await asyncio.sleep(3)
        try:
            state = await fetch_game_state()
        except Exception as exc:
            logger.warning("Game state poll error: %s", exc)
            continue
        if state is None:
            if _was_game_running and not _game_session.is_empty:
                await _broadcast_game_end()
            _was_game_running = False
            _reset_live_game_state()
            continue
        if not _was_game_running:
            previous_game_time = None
            if not _game_session.is_empty:
                previous_game_time = _game_session.snapshots[-1].game_time
            if _game_end_sent and previous_game_time is not None and state.game_time < previous_game_time:
                _game_session.clear()
            _game_end_sent = False
        _was_game_running = True
        _record_session_snapshot(state)
        asyncio.create_task(_refresh_lane_opponent_cache(state))
        asyncio.create_task(_ensure_proactive_session(state))
        asyncio.create_task(_run_proactive_checks(state))
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


@app.get("/game/state")
async def get_game_state():
    state = await fetch_game_state()
    if state is None:
        return JSONResponse(status_code=503, content={"status": "no_game"})
    return _game_state_to_ws_payload(state)


@app.post("/game/draft-context")
async def set_draft_context(ctx: DraftContext):
    global _cached_lane_opponent, _lane_opponent_cache_key, _draft_context
    normalized_ctx = DraftContext(
        my_champion=ctx.my_champion.strip(),
        my_position=_normalize_position(ctx.my_position),
        lane_opponent=ctx.lane_opponent.strip() if ctx.lane_opponent else None,
    )
    _draft_context = normalized_ctx
    _cached_lane_opponent = normalized_ctx.lane_opponent
    _lane_opponent_cache_key = f"{normalized_ctx.my_champion}:{normalized_ctx.my_position}:from_draft"
    logger.info(
        "Draft context cached: champion=%s position=%s opponent=%s",
        normalized_ctx.my_champion,
        normalized_ctx.my_position,
        normalized_ctx.lane_opponent,
    )
    return {"ok": True}


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


async def _fetch_riot_cs_snippet(state: GameState):
    from backend.knowledge.schemas import KnowledgeSnippet

    riot_key = CONFIG.get("riot_api_key", "")
    if not riot_key or state.game_time <= 0 or state.creep_score < 0:
        return None
    try:
        tier = CONFIG.get("riot_benchmark_tier", "DIAMOND")
        benchmark = await fetch_cs_benchmark(
            riot_key,
            state.champion_name,
            state.assigned_position,
            region=CONFIG.get("riot_region", "KR"),
            tier=tier,
            target_samples=int(CONFIG.get("riot_benchmark_samples", "25")),
            matches_per_player=int(CONFIG.get("riot_benchmark_matches_per_player", "3")),
            ttl_seconds=int(CONFIG.get("riot_benchmark_ttl_seconds", "604800")),
        )
    except Exception as exc:
        logger.warning("Riot CS benchmark fetch failed: %s", exc)
        return None
    if not benchmark or benchmark.avg_cspm <= 0:
        return None

    game_minutes = state.game_time / 60
    current_cspm = state.creep_score / game_minutes
    diff_pct = round((current_cspm / benchmark.avg_cspm - 1.0) * 100)
    sign = "+" if diff_pct >= 0 else ""
    curve_text = _cs_curve_text(benchmark.cs_at, game_minutes)
    content = (
        f"Riot Match-V5 CS benchmark: {state.champion_name} {normalize_position(state.assigned_position)} "
        f"current {state.creep_score} CS at {game_minutes:.1f}m ({current_cspm:.1f} CS/min) vs "
        f"{tier} average {benchmark.avg_cspm:.1f} CS/min ({sign}{diff_pct}%, n={benchmark.samples})."
    )
    if curve_text:
        content += f" Timeline averages: {curve_text}."
    return KnowledgeSnippet(
        source=f"riot_cs_benchmark:{state.champion_name}:{normalize_position(state.assigned_position)}:{tier}",
        content=content,
        relevance="high",
    )


def _cs_curve_text(cs_at: dict[str, float], game_minutes: float) -> str:
    visible_points = [
        f"{minute}m {cs:g} CS"
        for minute, cs in sorted(cs_at.items(), key=lambda item: int(item[0]))
        if int(minute) <= game_minutes + 1
    ]
    return ", ".join(visible_points)


async def send_advice(websocket: WebSocket, user_query: str | None, language: str, planned: bool = False, opgg_only: bool = False) -> None:
    game_state = await fetch_game_state()
    if game_state is None:
        await websocket.send_json({"type": "error", "message": "Game not running"})
        if not _game_session.is_empty:
            await _broadcast_game_end()
        return

    _record_session_snapshot(game_state, force=True)

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
        riot_cs_snippet = await _fetch_riot_cs_snippet(game_state)
        rag_snippets = retrieve(
            champion=game_state.champion_name,
            lane_opponent=game_state.lane_opponent,
            fed_enemy=game_state.fed_enemy,
            collection=_knowledge_collection,
            performance_collection=_performance_collection,
        ) if _knowledge_collection is not None else []
        knowledge_snippets = opgg_snippets + ([riot_cs_snippet] if riot_cs_snippet else []) + rag_snippets

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
