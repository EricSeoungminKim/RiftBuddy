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
    lane_opponent: str | None = None
    ally_champions: tuple[str, ...] = field(default_factory=tuple)
    enemy_champions: tuple[str, ...] = field(default_factory=tuple)
    key_moments: list[str] = field(default_factory=list)
    # OP.GG enriched fields
    op_score: float | None = None
    op_score_rank: str | None = None       # "MVP", "ACE", or None
    damage_dealt: int | None = None
    items: list[str] = field(default_factory=list)
    avg_tier: str | None = None            # e.g. "GOLD", "PLATINUM"
    cs_vs_avg_pct: float | None = None     # e.g. 1.15 = 15% above avg


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

    # Team composition — taken from the last snapshot (stable throughout game)
    first = snaps[0]
    ally_champions = first.ally_champions
    enemy_champions = first.enemy_champions
    lane_opponent = first.lane_opponent

    return GameSummary(
        champion=last.champion_name,
        kills=kills,
        deaths=deaths,
        assists=assists,
        avg_cs=avg_cs,
        avg_gold_diff=avg_gold_diff,
        game_duration_minutes=duration_minutes,
        lane_opponent=lane_opponent,
        ally_champions=ally_champions,
        enemy_champions=enemy_champions,
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

    # Lane matchup result
    if summary.lane_opponent:
        lane_result = "won lane" if summary.avg_gold_diff >= 0 else "lost lane"
        base += f" vs {summary.lane_opponent} ({lane_result})."

    # Team compositions
    if summary.ally_champions:
        base += f" Ally comp: {', '.join(summary.ally_champions)}."
    if summary.enemy_champions:
        base += f" Enemy comp: {', '.join(summary.enemy_champions)}."

    # A: OP.GG performance comparison vs average
    if summary.op_score is not None:
        grade_parts = [f"OP.GG score: {summary.op_score:.1f}"]
        if summary.op_score_rank:
            grade_parts.append(summary.op_score_rank)
        base += f" {' | '.join(grade_parts)}."
    if summary.cs_vs_avg_pct is not None:
        cs_diff = int((summary.cs_vs_avg_pct - 1.0) * 100)
        sign = "+" if cs_diff >= 0 else ""
        base += f" CS vs Diamond avg: {sign}{cs_diff}%."
    if summary.damage_dealt is not None:
        base += f" Total damage: {summary.damage_dealt:,}."
    if summary.items:
        base += f" Final build: {', '.join(summary.items)}."

    # C: score trend / grade
    if summary.avg_tier:
        base += f" Match avg tier: {summary.avg_tier}."

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
    now = datetime.now().astimezone()
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
            "lane_opponent": summary.lane_opponent or "",
            "ally_comp": ", ".join(summary.ally_champions),
            "enemy_comp": ", ".join(summary.enemy_champions),
            "op_score": summary.op_score or 0.0,
            "op_score_rank": summary.op_score_rank or "",
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
    opgg_match: dict | None = None,
    opgg_avg_stats: dict | None = None,
) -> str | None:
    if session.is_empty:
        return None

    summary = summarize_session(session)
    if summary is None:
        return None

    # Enrich from OP.GG last match
    if opgg_match:
        participants = opgg_match.get("participants", [])
        # Find the player's own participant entry (match by summoner name)
        own = next(
            (p for p in participants if p.get("team_key") == "ORDER" or True),
            None,
        )
        # Better: find by champion name matching the summary
        own = next(
            (p for p in participants if p.get("champion_name", "").upper() == summary.champion.upper()),
            participants[0] if participants else None,
        )
        if own:
            stats = own.get("stats", {})
            summary.op_score = stats.get("op_score")
            rank = stats.get("op_score_rank")
            summary.op_score_rank = rank if rank in ("MVP", "ACE") else None
            summary.damage_dealt = stats.get("total_damage_dealt_to_champions")
            summary.items = own.get("items_names", [])
        tier_info = opgg_match.get("average_tier_info", {})
        summary.avg_tier = tier_info.get("tier")

    # Enrich CS comparison from OP.GG champion analysis
    if opgg_avg_stats:
        avg_data = (
            opgg_avg_stats.get("data", {})
            .get("summary", {})
            .get("average_stats", {})
        )
        avg_cs_per_min = avg_data.get("cs_per_min")
        if avg_cs_per_min and summary.game_duration_minutes > 0:
            my_cs_per_min = summary.avg_cs / summary.game_duration_minutes
            summary.cs_vs_avg_pct = my_cs_per_min / avg_cs_per_min

    seed_text = generate_seed_text(summary)
    return embed_performance_seed(collection, summary, seed_text)
