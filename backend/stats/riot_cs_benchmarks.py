"""Build CS benchmarks from Riot Match-V5 raw match data."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

QUEUE_RANKED_SOLO = 420
DEFAULT_DIVISIONS = ("I", "II", "III", "IV")
DEFAULT_TIMELINE_MINUTES = (10, 15, 20)
DEFAULT_CACHE_DIR = Path("backend/data/cs_benchmarks")

_PLATFORM_TO_REGIONAL = {
    "BR1": "AMERICAS",
    "EUN1": "EUROPE",
    "EUW1": "EUROPE",
    "JP1": "ASIA",
    "KR": "ASIA",
    "LA1": "AMERICAS",
    "LA2": "AMERICAS",
    "NA1": "AMERICAS",
    "OC1": "SEA",
    "PH2": "SEA",
    "RU": "EUROPE",
    "SG2": "SEA",
    "TH2": "SEA",
    "TR1": "EUROPE",
    "TW2": "SEA",
    "VN2": "SEA",
}

_POSITION_ALIASES = {
    "ADC": "BOTTOM",
    "BOT": "BOTTOM",
    "BOTTOM": "BOTTOM",
    "SUPPORT": "UTILITY",
    "UTILITY": "UTILITY",
    "MID": "MIDDLE",
    "MIDDLE": "MIDDLE",
    "JUNGLE": "JUNGLE",
    "TOP": "TOP",
}


@dataclass(frozen=True)
class CsBenchmark:
    champion: str
    position: str
    tier: str
    region: str
    samples: int
    avg_cspm: float
    cs_at: dict[str, float] = field(default_factory=dict)
    match_ids: tuple[str, ...] = field(default_factory=tuple)
    generated_at: int = field(default_factory=lambda: int(time.time()))

    def to_average_stats_payload(self) -> dict[str, Any]:
        average_stats: dict[str, Any] = {
            "cs_per_min": self.avg_cspm,
            "sample_size": self.samples,
            "source": "riot_match_v5",
        }
        for minute, value in self.cs_at.items():
            average_stats[f"cs_at_{minute}"] = value
        return {"data": {"summary": {"average_stats": average_stats}}}


class RiotApiClient:
    def __init__(self, api_key: str, platform_region: str = "KR", timeout: float = 8.0):
        if not api_key:
            raise ValueError("RIOT_API_KEY is required for Riot CS benchmarks")
        self.api_key = api_key
        self.platform_region = platform_region.upper()
        self.regional_region = _PLATFORM_TO_REGIONAL.get(self.platform_region, "ASIA")
        self.timeout = timeout

    async def get_platform(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._get(f"https://{self.platform_region.lower()}.api.riotgames.com{path}", params)

    async def get_regional(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._get(f"https://{self.regional_region.lower()}.api.riotgames.com{path}", params)

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        headers = {"X-Riot-Token": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()


async def fetch_cs_benchmark(
    api_key: str,
    champion: str,
    position: str,
    *,
    region: str = "KR",
    tier: str = "DIAMOND",
    target_samples: int = 25,
    matches_per_player: int = 3,
    max_pages_per_division: int = 1,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    ttl_seconds: int = 60 * 60 * 24 * 7,
) -> CsBenchmark | None:
    cache_path = _cache_path(cache_dir, region, tier, champion, position)
    cached = _read_cache(cache_path, ttl_seconds)
    if cached:
        return cached

    client = RiotApiClient(api_key=api_key, platform_region=region)
    benchmark = await collect_cs_benchmark(
        client,
        champion=champion,
        position=position,
        tier=tier,
        target_samples=target_samples,
        matches_per_player=matches_per_player,
        max_pages_per_division=max_pages_per_division,
    )
    if benchmark:
        _write_cache(cache_path, benchmark)
    return benchmark


async def collect_cs_benchmark(
    client: RiotApiClient,
    champion: str,
    position: str,
    *,
    tier: str = "DIAMOND",
    divisions: tuple[str, ...] = DEFAULT_DIVISIONS,
    target_samples: int = 25,
    matches_per_player: int = 3,
    max_pages_per_division: int = 1,
) -> CsBenchmark | None:
    target_champion = _normalize_champion(champion)
    target_position = normalize_position(position)
    samples: list[tuple[float, dict[str, int], str]] = []
    seen_match_ids: set[str] = set()

    entries = await _league_entries(client, tier, divisions, max_pages_per_division)
    for entry in entries:
        puuid = await _entry_puuid(client, entry)
        if not puuid:
            continue
        match_ids = await client.get_regional(
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
            {"queue": QUEUE_RANKED_SOLO, "type": "ranked", "count": matches_per_player},
        )
        for match_id in match_ids:
            if match_id in seen_match_ids:
                continue
            seen_match_ids.add(match_id)
            sample = await _cs_sample_from_match(client, match_id, target_champion, target_position)
            if sample:
                samples.append(sample)
            if len(samples) >= target_samples:
                return _build_benchmark(champion, target_position, tier, client.platform_region, samples)

    return _build_benchmark(champion, target_position, tier, client.platform_region, samples)


async def _league_entries(
    client: RiotApiClient,
    tier: str,
    divisions: tuple[str, ...],
    max_pages_per_division: int,
) -> list[dict]:
    entries: list[dict] = []
    for division in divisions:
        for page in range(1, max_pages_per_division + 1):
            try:
                page_entries = await client.get_platform(
                    f"/lol/league-exp/v4/entries/RANKED_SOLO_5x5/{tier}/{division}",
                    {"page": page},
                )
                entries.extend(page_entries)
            except httpx.HTTPStatusError as exc:
                logger.warning("Riot league entries fetch failed: %s", exc)
    return entries


async def _entry_puuid(client: RiotApiClient, entry: dict) -> str | None:
    if entry.get("puuid"):
        return entry["puuid"]
    summoner_id = entry.get("summonerId")
    if not summoner_id:
        return None
    try:
        summoner = await client.get_platform(f"/lol/summoner/v4/summoners/{summoner_id}")
        return summoner.get("puuid")
    except httpx.HTTPStatusError as exc:
        logger.warning("Riot summoner lookup failed: %s", exc)
        return None


async def _cs_sample_from_match(
    client: RiotApiClient,
    match_id: str,
    champion: str,
    position: str,
) -> tuple[float, dict[str, int], str] | None:
    try:
        match, timeline = await asyncio.gather(
            client.get_regional(f"/lol/match/v5/matches/{match_id}"),
            client.get_regional(f"/lol/match/v5/matches/{match_id}/timeline"),
            return_exceptions=True,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning("Riot match fetch failed: %s", exc)
        return None

    if isinstance(match, Exception):
        return None
    info = match.get("info", {})
    if info.get("queueId") != QUEUE_RANKED_SOLO:
        return None
    duration_minutes = float(info.get("gameDuration", 0)) / 60
    if duration_minutes <= 0:
        return None

    participant = next(
        (
            p for p in info.get("participants", [])
            if _normalize_champion(p.get("championName", "")) == champion
            and normalize_position(p.get("teamPosition", "")) == position
        ),
        None,
    )
    if not participant:
        return None

    cs_total = participant_cs(participant)
    cs_at = (
        timeline_cs_at(timeline, participant.get("participantId"))
        if not isinstance(timeline, Exception)
        else {}
    )
    return cs_total / duration_minutes, cs_at, match_id


def participant_cs(participant: dict) -> int:
    return int(participant.get("totalMinionsKilled", 0) or 0) + int(participant.get("neutralMinionsKilled", 0) or 0)


def timeline_cs_at(timeline: dict, participant_id: int | None, minutes: tuple[int, ...] = DEFAULT_TIMELINE_MINUTES) -> dict[str, int]:
    if participant_id is None:
        return {}
    frames = timeline.get("info", {}).get("frames", [])
    result: dict[str, int] = {}
    participant_key = str(participant_id)
    for minute in minutes:
        frame_index = min(minute, len(frames) - 1)
        if frame_index < 0:
            continue
        frame_participant = frames[frame_index].get("participantFrames", {}).get(participant_key, {})
        result[str(minute)] = int(frame_participant.get("minionsKilled", 0) or 0) + int(
            frame_participant.get("jungleMinionsKilled", 0) or 0
        )
    return result


def normalize_position(position: str) -> str:
    return _POSITION_ALIASES.get(position.strip().upper(), position.strip().upper())


def _normalize_champion(champion: str) -> str:
    return champion.lower().replace(" ", "").replace("'", "").replace(".", "")


def _build_benchmark(
    champion: str,
    position: str,
    tier: str,
    region: str,
    samples: list[tuple[float, dict[str, int], str]],
) -> CsBenchmark | None:
    if not samples:
        return None
    avg_cspm = round(sum(sample[0] for sample in samples) / len(samples), 2)
    cs_at: dict[str, float] = {}
    timeline_keys = sorted({key for _, timeline, _ in samples for key in timeline}, key=int)
    for key in timeline_keys:
        values = [timeline[key] for _, timeline, _ in samples if key in timeline]
        if values:
            cs_at[key] = round(sum(values) / len(values), 1)
    return CsBenchmark(
        champion=champion,
        position=position,
        tier=tier.upper(),
        region=region.upper(),
        samples=len(samples),
        avg_cspm=avg_cspm,
        cs_at=cs_at,
        match_ids=tuple(match_id for _, _, match_id in samples),
    )


def _cache_path(cache_dir: Path, region: str, tier: str, champion: str, position: str) -> Path:
    filename = f"{_normalize_champion(champion)}_{normalize_position(position).lower()}.json"
    return cache_dir / region.upper() / tier.upper() / filename


def _read_cache(path: Path, ttl_seconds: int) -> CsBenchmark | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if int(time.time()) - int(data.get("generated_at", 0)) > ttl_seconds:
            return None
        data["match_ids"] = tuple(data.get("match_ids", []))
        return CsBenchmark(**data)
    except Exception as exc:
        logger.warning("Failed to read CS benchmark cache %s: %s", path, exc)
        return None


def _write_cache(path: Path, benchmark: CsBenchmark) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(benchmark), indent=2, sort_keys=True))
