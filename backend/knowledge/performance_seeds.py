"""performance_seeds.py

Summarises a completed GameSession into a natural-language seed text and
embeds it into a ChromaDB ``performance_seeds`` collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb
    from backend.game_session import GameSession


COLLECTION_NAME = "performance_seeds"


def _ts(game_time: float) -> str:
    """Convert seconds to MM:SS string."""
    m = int(game_time // 60)
    s = int(game_time % 60)
    return f"{m}:{s:02d}"


@dataclass
class GameSummary:
    champion: str
    kills: int
    deaths: int
    assists: int
    avg_cs: float
    avg_gold_diff: float
    game_duration_minutes: float
    key_moments: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1. summarize_session
# ---------------------------------------------------------------------------

def summarize_session(session: "GameSession") -> GameSummary | None:
    if session.is_empty:
        return None

    snaps = session.snapshots
    last = snaps[-1]

    kills = last.kills
    deaths = last.deaths
    assists = last.assists
    avg_cs = round(sum(s.creep_score for s in snaps) / len(snaps), 1)
    avg_gold_diff = round(sum(s.gold_diff for s in snaps) / len(snaps), 1)
    duration_minutes = round(last.game_time / 60, 1)

    # --- key moments ---
    key_moments: list[str] = []

    # Deaths: snapshots where deaths increased vs previous
    for i in range(1, len(snaps)):
        if snaps[i].deaths > snaps[i - 1].deaths:
            key_moments.append(f"Died at {_ts(snaps[i].game_time)}")

    # Best CS window: 3-consecutive-snapshot window with highest CS gain
    if len(snaps) >= 3:
        best_gain = -1
        best_start = 0
        for i in range(len(snaps) - 2):
            gain = snaps[i + 2].creep_score - snaps[i].creep_score
            if gain > best_gain:
                best_gain = gain
                best_start = i
        if best_gain > 0:
            t_start = _ts(snaps[best_start].game_time)
            t_end = _ts(snaps[best_start + 2].game_time)
            key_moments.append(f"Best CS window: {t_start} - {t_end}")

    # Gold peak: snapshot with highest gold_diff
    peak_snap = max(snaps, key=lambda s: s.gold_diff)
    if peak_snap.gold_diff > 0:
        key_moments.append(
            f"Gold peak: +{int(peak_snap.gold_diff)} at {_ts(peak_snap.game_time)}"
        )

    return GameSummary(
        champion=last.champion_name,
        kills=kills,
        deaths=deaths,
        assists=assists,
        avg_cs=avg_cs,
        avg_gold_diff=avg_gold_diff,
        game_duration_minutes=duration_minutes,
        key_moments=key_moments,
    )


# ---------------------------------------------------------------------------
# 2. generate_seed_text
# ---------------------------------------------------------------------------

def generate_seed_text(summary: GameSummary) -> str:
    gold_str = f"+{int(summary.avg_gold_diff)}" if summary.avg_gold_diff >= 0 else str(int(summary.avg_gold_diff))
    kda = f"{summary.kills}/{summary.deaths}/{summary.assists}"
    base = (
        f"Personal history - {summary.champion}: {kda} KDA, "
        f"avg {int(summary.avg_cs)} CS, avg {gold_str} gold lead ({int(summary.game_duration_minutes)}min game)."
    )

    if not summary.key_moments:
        return base

    moments_text = ". ".join(summary.key_moments)
    if moments_text:
        moments_text += "."
    return f"{base} {moments_text}"


# ---------------------------------------------------------------------------
# 3. embed_performance_seed
# ---------------------------------------------------------------------------

def embed_performance_seed(
    collection: "chromadb.Collection",
    summary: GameSummary,
    seed_text: str,
) -> str:
    now = datetime.utcnow()
    doc_id = f"perf_{summary.champion.lower()}_{now.strftime('%Y%m%d%H%M%S%f')}"
    collection.add(
        documents=[seed_text],
        ids=[doc_id],
        metadatas=[{
            "champion": summary.champion,
            "kills": summary.kills,
            "deaths": summary.deaths,
            "assists": summary.assists,
            "avg_cs": summary.avg_cs,
            "avg_gold_diff": summary.avg_gold_diff,
            "game_duration_minutes": summary.game_duration_minutes,
            "source": "performance",
            "date": now.strftime("%Y-%m-%d"),
        }],
    )
    return doc_id


# ---------------------------------------------------------------------------
# 4. save_game_seed
# ---------------------------------------------------------------------------

def save_game_seed(
    session: "GameSession",
    collection: "chromadb.Collection",
) -> str | None:
    if session.is_empty:
        return None

    summary = summarize_session(session)
    if summary is None:
        return None

    seed_text = generate_seed_text(summary)
    return embed_performance_seed(collection, summary, seed_text)
