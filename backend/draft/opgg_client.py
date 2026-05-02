import json as _json
import time
from typing import Any

import httpx

OPGG_MCP_URL = "https://mcp-api.op.gg/mcp"

# Official Korean display name → Riot champion ID (from DDragon ko_KR 14.9.1)
KO_TO_EN: dict[str, str] = {
    "아트록스": "Aatrox", "아리": "Ahri", "아칼리": "Akali", "아크샨": "Akshan",
    "알리스타": "Alistar", "아무무": "Amumu", "애니비아": "Anivia", "애니": "Annie",
    "아펠리오스": "Aphelios", "애쉬": "Ashe", "아우렐리온 솔": "AurelionSol",
    "아지르": "Azir", "바드": "Bard", "벨베스": "Belveth", "블리츠크랭크": "Blitzcrank",
    "브랜드": "Brand", "브라움": "Braum", "브라이어": "Briar", "케이틀린": "Caitlyn",
    "카밀": "Camille", "카시오페아": "Cassiopeia", "초가스": "Chogath", "코르키": "Corki",
    "다리우스": "Darius", "다이애나": "Diana", "드레이븐": "Draven",
    "문도 박사": "DrMundo", "에코": "Ekko", "엘리스": "Elise", "이블린": "Evelynn",
    "이즈리얼": "Ezreal", "피들스틱": "Fiddlesticks", "피오라": "Fiora", "피즈": "Fizz",
    "갈리오": "Galio", "갱플랭크": "Gangplank", "가렌": "Garen", "나르": "Gnar",
    "그라가스": "Gragas", "그레이브즈": "Graves", "그웬": "Gwen", "헤카림": "Hecarim",
    "하이머딩거": "Heimerdinger", "흐웨이": "Hwei", "일라오이": "Illaoi",
    "이렐리아": "Irelia", "아이번": "Ivern", "잔나": "Janna", "자르반 4세": "JarvanIV",
    "잭스": "Jax", "제이스": "Jayce", "진": "Jhin", "징크스": "Jinx",
    "카이사": "Kaisa", "칼리스타": "Kalista", "카르마": "Karma", "카서스": "Karthus",
    "카사딘": "Kassadin", "카타리나": "Katarina", "케일": "Kayle", "케인": "Kayn",
    "케넨": "Kennen", "카직스": "Khazix", "킨드레드": "Kindred", "클레드": "Kled",
    "코그모": "KogMaw", "크산테": "KSante", "르블랑": "Leblanc", "리 신": "LeeSin",
    "레오나": "Leona", "릴리아": "Lillia", "리산드라": "Lissandra", "루시안": "Lucian",
    "룰루": "Lulu", "럭스": "Lux", "말파이트": "Malphite", "말자하": "Malzahar",
    "마오카이": "Maokai", "마스터 이": "MasterYi", "밀리오": "Milio",
    "미스 포츈": "MissFortune", "오공": "MonkeyKing", "모데카이저": "Mordekaiser",
    "모르가나": "Morgana", "나피리": "Naafiri", "나미": "Nami", "나서스": "Nasus",
    "노틸러스": "Nautilus", "니코": "Neeko", "니달리": "Nidalee", "닐라": "Nilah",
    "녹턴": "Nocturne", "누누와 윌럼프": "Nunu", "올라프": "Olaf",
    "오리아나": "Orianna", "오른": "Ornn", "판테온": "Pantheon", "뽀삐": "Poppy",
    "파이크": "Pyke", "키아나": "Qiyana", "퀸": "Quinn", "라칸": "Rakan",
    "람머스": "Rammus", "렉사이": "RekSai", "렐": "Rell",
    "레나타 글라스크": "Renata", "레넥톤": "Renekton", "렝가": "Rengar",
    "리븐": "Riven", "럼블": "Rumble", "라이즈": "Ryze", "사미라": "Samira",
    "세주아니": "Sejuani", "세나": "Senna", "세라핀": "Seraphine", "세트": "Sett",
    "샤코": "Shaco", "쉔": "Shen", "쉬바나": "Shyvana", "신지드": "Singed",
    "사이온": "Sion", "시비르": "Sivir", "스카너": "Skarner", "스몰더": "Smolder",
    "소나": "Sona", "소라카": "Soraka", "스웨인": "Swain", "사일러스": "Sylas",
    "신드라": "Syndra", "탐 켄치": "TahmKench", "탈리야": "Taliyah", "탈론": "Talon",
    "타릭": "Taric", "티모": "Teemo", "쓰레쉬": "Thresh", "트리스타나": "Tristana",
    "트런들": "Trundle", "트린다미어": "Tryndamere",
    "트위스티드 페이트": "TwistedFate", "트위치": "Twitch", "우디르": "Udyr",
    "우르곳": "Urgot", "바루스": "Varus", "베인": "Vayne", "베이가": "Veigar",
    "벨코즈": "Velkoz", "벡스": "Vex", "바이": "Vi", "비에고": "Viego",
    "빅토르": "Viktor", "블라디미르": "Vladimir", "볼리베어": "Volibear",
    "워윅": "Warwick", "자야": "Xayah", "제라스": "Xerath", "신 짜오": "XinZhao",
    "야스오": "Yasuo", "요네": "Yone", "요릭": "Yorick", "유미": "Yuumi",
    "자크": "Zac", "제드": "Zed", "제리": "Zeri", "직스": "Ziggs",
    "질리언": "Zilean", "조이": "Zoe", "자이라": "Zyra",
}
CACHE_TTL_SECONDS = 600

_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    if key not in _cache:
        return None
    ts, value = _cache[key]
    if time.monotonic() - ts > CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


async def _call_opgg_mcp(tool: str, arguments: dict) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(OPGG_MCP_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    result = data.get("result", data)
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, list) and content:
            raw = content[0].get("text", "{}")
            return _json.loads(raw) if isinstance(raw, str) else raw
    return result


_POSITION_MAP = {
    "bottom": "adc",
    "바텀": "adc",
    "top": "top",
    "탑": "top",
    "jungle": "jungle",
    "정글": "jungle",
    "mid": "mid",
    "미드": "mid",
    "support": "support",
    "서폿": "support",
    "adc": "adc",
}

_ANALYSIS_FIELDS = [
    "data.summary.average_stats.{ban_rate,pick_rate,win_rate,tier}",
    "data.summary.average_stats.tier_data.{rank,tier}",
    "data.runes.{primary_page_name,primary_rune_names[],secondary_page_name,secondary_rune_names[],stat_mod_names[]}",
    "data.core_items.{ids_names[],win}",
    "data.skills.{order[],pick_rate,win}",
    "data.strong_counters[].{champion_name,win_rate}",
    "data.weak_counters[].{champion_name,win_rate}",
    "data.{damage_type}",
]


def _normalize_champion(name: str) -> str:
    # Korean name → English ID first
    en = KO_TO_EN.get(name.strip()) or KO_TO_EN.get(name.strip().lower())
    if en:
        return en.upper()
    return name.strip().upper().replace(" ", "_").replace("'", "")


def _normalize_position(role: str) -> str:
    return _POSITION_MAP.get(role.lower(), role.lower())


async def get_champion_analysis(champion: str, role: str) -> dict:
    pos = _normalize_position(role)
    champ = _normalize_champion(champion)
    key = f"champion_analysis:{champ}:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_get_champion_analysis", {
        "champion": champ,
        "position": pos,
        "game_mode": "ranked",
        "desired_output_fields": _ANALYSIS_FIELDS,
    })
    _cache_set(key, result)
    return result


async def get_matchup(my_champion: str, enemy_champion: str, role: str) -> dict:
    pos = _normalize_position(role)
    my_champ = _normalize_champion(my_champion)
    enemy_champ = _normalize_champion(enemy_champion)
    key = f"matchup:{my_champ}:{enemy_champ}:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_get_lane_matchup_guide", {
        "my_champion": my_champ,
        "opponent_champion": enemy_champ,
        "position": pos,
    })
    _cache_set(key, result)
    return result


async def get_runes(champion: str, role: str) -> dict:
    pos = _normalize_position(role)
    champ = _normalize_champion(champion)
    key = f"runes:{champ}:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    data = await get_champion_analysis(champion, role)
    runes = data.get("data", {}).get("runes", data.get("runes", {}))
    _cache_set(key, runes)
    return runes


async def get_meta_champions(role: str) -> list:
    pos = _normalize_position(role)
    key = f"meta:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_list_lane_meta_champions", {"position": pos})
    champions = result if isinstance(result, list) else result.get("champions", [])
    _cache_set(key, champions)
    return champions
