"""Proactive coach — warns the player before historically dangerous game moments.

Flow:
1. On game start, load death timestamps from past performance seeds in ChromaDB.
2. Cluster them into danger windows (e.g. 7–9 min, 14–16 min).
3. During _poll_game_state, check if current game_time is entering a window.
4. If triggered (once per window per game), call LLM and push proactive_warning to WS.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TYPE_CHECKING = False
if TYPE_CHECKING:
    import chromadb


# ---------------------------------------------------------------------------
# 1. Pattern extraction from ChromaDB seeds
# ---------------------------------------------------------------------------

_DEATH_RE = re.compile(r"Died at (\d+):(\d+)")


def _minutes(m: int, s: int) -> float:
    return m + s / 60.0


def extract_death_minutes(seed_text: str) -> list[float]:
    """Parse 'Died at MM:SS' entries from a seed text."""
    return [_minutes(int(m), int(s)) for m, s in _DEATH_RE.findall(seed_text)]


def load_death_patterns(
    collection: "chromadb.Collection",
    champion: str,
    max_seeds: int = 10,
) -> list[float]:
    """Return all death timestamps (minutes) from recent seeds for this champion."""
    try:
        results = collection.query(
            query_texts=[f"Personal history - {champion}"],
            n_results=max_seeds,
            where={"champion": champion},
        )
    except Exception:
        return []

    death_minutes: list[float] = []
    for doc in (results.get("documents") or [[]])[0]:
        death_minutes.extend(extract_death_minutes(doc))
    return death_minutes


# ---------------------------------------------------------------------------
# 2. Danger window clustering
# ---------------------------------------------------------------------------

@dataclass
class DangerWindow:
    center_minutes: float       # average death time in this cluster
    count: int                  # how many historical deaths contributed
    triggered: bool = False     # fired once per game


def cluster_danger_windows(
    death_minutes: list[float],
    cluster_radius: float = 1.5,
    min_count: int = 2,
) -> list[DangerWindow]:
    """Group nearby death timestamps into danger windows.

    Uses a simple greedy pass: sort, then merge points within cluster_radius.
    Only keeps windows with at least min_count deaths.
    """
    if not death_minutes:
        return []

    sorted_times = sorted(death_minutes)
    clusters: list[list[float]] = []
    current: list[float] = [sorted_times[0]]

    for t in sorted_times[1:]:
        if t - current[0] <= cluster_radius * 2:
            current.append(t)
        else:
            clusters.append(current)
            current = [t]
    clusters.append(current)

    windows = []
    for group in clusters:
        if len(group) >= min_count:
            windows.append(DangerWindow(
                center_minutes=sum(group) / len(group),
                count=len(group),
            ))
    return windows


# ---------------------------------------------------------------------------
# 3. Trigger check (called every poll cycle)
# ---------------------------------------------------------------------------

WARN_BEFORE_MINUTES = 1.0   # warn this many minutes before the danger window center
WARN_WINDOW_MINUTES = 0.5   # window stays "active" for this many minutes after trigger time


def check_triggers(
    game_time_seconds: float,
    windows: list[DangerWindow],
) -> list[DangerWindow]:
    """Return windows whose trigger time just arrived (not yet fired)."""
    now = game_time_seconds / 60.0
    fired: list[DangerWindow] = []
    for w in windows:
        if w.triggered:
            continue
        trigger_at = w.center_minutes - WARN_BEFORE_MINUTES
        # Fire if we're in [trigger_at, trigger_at + WARN_WINDOW_MINUTES]
        if trigger_at <= now <= trigger_at + WARN_WINDOW_MINUTES:
            w.triggered = True
            fired.append(w)
    return fired


# ---------------------------------------------------------------------------
# 4. LLM warning generation
# ---------------------------------------------------------------------------

async def generate_proactive_warning(
    window: DangerWindow,
    champion: str,
    position: str,
    language: str,
) -> str:
    """Ask the LLM to generate a natural proactive warning based on the pattern."""
    from backend.llm.advisor import get_advice
    from backend.context.engine import ContextPacket

    minute = int(window.center_minutes)
    lang_instruction = "한국어로 2문장 이내로" if language == "ko" else "in 2 sentences or less"

    prompt = (
        f"리그 오브 레전드 코치야. 플레이어는 {champion} ({position})을 플레이 중이고 "
        f"지금 게임 {minute - 1}분~{minute + 1}분 구간에 진입했어. "
        f"과거 {window.count}번의 게임 데이터를 보면 이 시간대({minute}분 전후)에 "
        f"반복적으로 사망하는 패턴이 있었어. "
        f"지금 이 순간 플레이어에게 {lang_instruction} 간결하고 구체적인 주의 경고를 해줘. "
        f"'⚠️'로 시작해."
    )

    dummy_packet = ContextPacket(
        health_percent=100.0,
        gold=0.0,
        level=1,
        game_time_minutes=window.center_minutes,
        summary=prompt,
    )
    return await get_advice(dummy_packet, user_query=prompt, language=language)


# ---------------------------------------------------------------------------
# 5. Session state container (one per game)
# ---------------------------------------------------------------------------

@dataclass
class ProactiveCoachSession:
    champion: str
    position: str
    windows: list[DangerWindow] = field(default_factory=list)
    loaded: bool = False

    def reset(self) -> None:
        self.windows = []
        self.loaded = False

    async def load(self, collection: "chromadb.Collection") -> None:
        death_minutes = load_death_patterns(collection, self.champion)
        self.windows = cluster_danger_windows(death_minutes)
        self.loaded = True

    def check(self, game_time_seconds: float) -> list[DangerWindow]:
        return check_triggers(game_time_seconds, self.windows)
