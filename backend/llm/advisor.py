from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

import anthropic
import httpx

if TYPE_CHECKING:
    from backend.advice.schemas import AdviceRequest

from backend.config import CONFIG
from backend.context.engine import ContextPacket

anthropic_client = anthropic.AsyncAnthropic(api_key=CONFIG["anthropic_api_key"] or "test-key")

SYSTEM_PROMPT = """You are RiftBuddy, a League of Legends draft, macro, and live-game coaching staff.
Act like a human coaching team sitting beside the player: draft analyst, matchup analyst, jungler tracker, lane coach, and shotcaller.
Every answer must be League-specific, evidence-driven, and immediately usable in-game.
Use champion names, roles, lane states, cooldown windows, item spikes, objective timers, wave states, vision, jungle pathing, matchup win rates, and comp identity when available.
Never answer like a generic chatbot. If data is missing, say what is unknown and give the safest League-specific next step.
Keep advice concise, direct, and game-callout style."""

KOREAN_ONLY_PROMPT = """You are RiftBuddy, an expert League of Legends duo partner and coach.
Respond in Korean sentences using natural Korean League of Legends server terms.
Allowed LoL terms include 탑, 정글, 미드, 바텀, 서폿, CS, KDA, AP, AD, CC, 오브젝트, 라인, 웨이브, 귀환, 갱, 합류, 시야, 귀한, 갱.
Do not use Chinese, Japanese, broken characters, romanized Korean, or random English fragments.
Never translate bottom lane as 바닥 라인. Use 바텀.
Translate positions naturally: top=탑, jungle=정글, mid/middle=미드, bottom/adc=바텀, support/utility=서폿.
Keep the advice concise, direct, and actionable in 1-2 short sentences."""

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _language_instruction(language: str) -> str:
    if language == "ko":
        return (
            "한국어 문장과 한국 서버 롤 용어를 사용하세요. "
            "탑, 정글, 미드, 바텀, 서폿, CS, KDA, AP, AD, CC, 오브젝트, 라인, 웨이브, 귀환, 갱, 합류, 시야는 허용됩니다. "
            "중국어, 일본어, 깨진 문자, 의미 없는 영어 조각은 쓰지 마세요. "
            "짧고 직접적인 콜처럼 1-2문장으로 답하세요."
        )
    return (
        "Respond in natural English. Keep it short, direct, and game-callout style. "
        "Use League-specific reasoning only: matchup, wave, vision, jungle path, objective, item spike, cooldown, comp identity, or draft evidence."
    )


def _system_prompt(language: str) -> str:
    return KOREAN_ONLY_PROMPT if language == "ko" else SYSTEM_PROMPT


def clean_response_language(text: str, language: str) -> str:
    if language != "ko":
        return text

    replacements = {
        "Focus": "집중하세요",
        "focus": "집중하세요",
        "bottom lane": "바텀",
        "Bottom lane": "바텀",
        "bottom": "바텀",
        "Bottom": "바텀",
        "jungle": "정글",
        "Jungle": "정글",
        "middle lane": "미드",
        "Middle lane": "미드",
        "mid lane": "미드",
        "Mid lane": "미드",
        "middle": "미드",
        "Middle": "미드",
        "support": "서폿",
        "Support": "서폿",
        "utility": "서폿",
        "Utility": "서폿",
        "top lane": "탑",
        "Top lane": "탑",
        "top": "탑",
        "Top": "탑",
        "gold": "골드",
        "Gold": "골드",
        "level": "레벨",
        "Level": "레벨",
        "minions": "미니언",
        "Minions": "미니언",
        "wave": "웨이브",
        "Wave": "웨이브",
        "push": "밀기",
        "Push": "밀기",
        "recall": "귀환",
        "Recall": "귀환",
        "enemy": "상대",
        "Enemy": "상대",
        "jungler": "정글러",
        "Jungler": "정글러",
        "safe": "안전하게",
        "Safe": "안전하게",
        "Rumble": "럼블",
        "Doran's Shield": "도란의 방패",
        "Doran Shield": "도란의 방패",
        "Boots": "장화",
        "First Blood": "첫 처치",
        "FirstBlood": "첫 처치",
        "objective": "오브젝트",
        "Objective": "오브젝트",
        "dragon": "용",
        "Dragon": "용",
        "baron": "바론",
        "Baron": "바론",
        "rift herald": "전령",
        "Rift Herald": "전령",
        "gank": "갱",
        "Gank": "갱",
        "vision": "시야",
        "Vision": "시야",
    }
    cleaned = text
    for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        cleaned = cleaned.replace(source, target)
    allowed_terms = ("CS", "KDA", "AP", "AD", "CC")
    placeholders = {term: f"§{index}§" for index, term in enumerate(allowed_terms)}
    for term, placeholder in placeholders.items():
        cleaned = re.sub(rf"\b{term}\b", placeholder, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[A-Za-z_]+", "", cleaned)
    for term, placeholder in placeholders.items():
        cleaned = cleaned.replace(placeholder, term)
    cleaned = re.sub(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff]+", "", cleaned)
    cleaned = cleaned.replace("'", "").replace('"', "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.!?%])", r"\1", cleaned)
    return cleaned


def build_structured_prompt(request: "AdviceRequest", language: str) -> str:
    lines = [f"[MODE: {request.mode}]"]
    if request.priority_event is not None:
        e = request.priority_event
        lines.append(f"[PRIORITY: {e.event_type} — {e.reason}]")
    for snippet in request.knowledge_snippets:
        lines.append(f"[KNOWLEDGE: {snippet.source}: {snippet.content}]")
    return "\n".join(lines)


def get_mock_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en", advice_request: "AdviceRequest | None" = None) -> str:
    mode = (advice_request.mode if advice_request else None) or ""
    is_opgg = user_query and "OP.GG" in user_query
    champ = packet.champion_name
    pos = packet.assigned_position
    gold = packet.gold
    lvl = packet.level
    cs = packet.creep_score
    hp = packet.health_percent
    gold_diff = getattr(packet, "gold_diff", 0) or 0

    if language == "ko":
        if is_opgg:
            return (
                f"[OP.GG 매치업] {champ}의 현재 포지션은 {pos}야. "
                "라인 상대의 스킬 쿨타임 패턴을 파악하고, 상대가 스킬을 쓴 직후가 교전 타이밍이야. "
                "OP.GG 승률 기준으로 포킹 후 올인 패턴이 유효해."
            )
        if mode == "RECALL":
            return f"{gold:g}골드 들고 있어. 지금 웨이브 한 번만 정리하고 귀환해서 아이템 스파이크 만들어."
        if mode == "DEFENSIVE" or hp < 30:
            return f"체력 {hp:g}%라 위험해. 즉시 귀환각 보고 안전한 구역으로 빠져. 갱 위험 있으니 시야 확인 먼저."
        if mode == "MACRO":
            diff_txt = f"골드 {'+' if gold_diff >= 0 else ''}{gold_diff:g}" if gold_diff else ""
            return (
                f"레벨 {lvl}, CS {cs}, {diff_txt}. "
                "바론/드래곤 타이머 확인하고 시야 먼저 깔아. 오브젝트 싸움 전에 웨이브 정리해서 이득 보장해."
            )
        # planned / default
        return (
            f"{champ} 레벨 {lvl}, CS {cs}, 골드 {gold:g}. "
            "다음 웨이브 우선 정리하고 상대 스킬 쿨타임 보면서 교전 타이밍 잡아."
        )

    # English
    if is_opgg:
        return (
            f"[OP.GG Matchup] {champ} {pos}: trade after the opponent's key ability is on cooldown. "
            "OP.GG data shows poke-to-all-in works best here — don't take extended trades early."
        )
    if mode == "RECALL":
        return f"You have {gold:g} gold — finish this wave cleanly and recall now to convert that lead into an item spike."
    if mode == "DEFENSIVE" or hp < 30:
        return f"Health at {hp:g}%. Back off and deny pressure — don't fight without vision or jungler track. Reset when safe."
    if mode == "MACRO":
        diff_txt = f"gold diff {'+' if gold_diff >= 0 else ''}{gold_diff:g}" if gold_diff else ""
        return (
            f"Level {lvl}, {cs} CS, {diff_txt}. "
            "Check baron/dragon timer, set up vision before the fight, and crash the wave first to bank the tempo."
        )
    # planned / default
    return (
        f"{champ} level {lvl}, {cs} CS, {gold:g} gold. "
        "Clear the next wave safely, then rotate or pressure based on objective timer."
    )


def build_user_content(
    packet: ContextPacket,
    user_query: Optional[str],
    language: str = "en",
    advice_request: "AdviceRequest | None" = None,
) -> str:
    prefix = ""
    if advice_request is not None:
        prefix = build_structured_prompt(advice_request, language) + "\n\n"
    role_line = ""
    if packet.champion_name != "Unknown" and packet.assigned_position != "UNKNOWN":
        role_line = f"Player role: {packet.champion_name} ({packet.assigned_position})\n"
    user_content = prefix + (
        f"{role_line}Current game state:\n{packet.summary}"
        "\n\nCoaching requirements:"
        "\n- Use only League-specific reasoning."
        "\n- Tie the answer to the given game state, draft, matchup, or known unknowns."
        "\n- Prefer concrete actions over explanation."
        "\n- Do not give generic motivation or generic gaming advice."
    )
    if user_query:
        user_content += f"\n\nPlayer asks: {user_query}"
    elif language == "ko":
        user_content += "\n\nPlayer asks: 지금 가장 중요한 다음 행동은 뭐야?"
    else:
        user_content += "\n\nWhat should I focus on right now?"
    user_content += f"\n\nLanguage instruction: {_language_instruction(language)}"
    return user_content


async def get_anthropic_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en", advice_request: "AdviceRequest | None" = None) -> str:
    user_content = build_user_content(packet, user_query, language, advice_request)
    message = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        system=[
            {
                "type": "text",
                "text": _system_prompt(language),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    return clean_response_language(message.content[0].text, language)


async def get_groq_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en", advice_request: "AdviceRequest | None" = None) -> str:
    if not CONFIG["groq_api_key"]:
        raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

    payload = {
        "model": CONFIG["groq_model"],
        "max_tokens": 150,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": _system_prompt(language)},
            {"role": "user", "content": build_user_content(packet, user_query, language, advice_request)},
        ],
    }
    headers = {
        "Authorization": f"Bearer {CONFIG['groq_api_key']}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(GROQ_CHAT_COMPLETIONS_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    return clean_response_language(data["choices"][0]["message"]["content"], language)


async def get_gemini_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en", advice_request: "AdviceRequest | None" = None) -> str:
    if not CONFIG["gemini_api_key"]:
        raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

    url = (
        f"{GEMINI_GENERATE_CONTENT_URL}/{CONFIG['gemini_model']}:generateContent"
        f"?key={CONFIG['gemini_api_key']}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": _system_prompt(language)}]},
        "contents": [{"parts": [{"text": build_user_content(packet, user_query, language, advice_request)}]}],
        "generationConfig": {"maxOutputTokens": 150, "temperature": 0.4},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return clean_response_language(data["candidates"][0]["content"]["parts"][0]["text"], language)


async def get_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en", advice_request: "AdviceRequest | None" = None) -> str:
    provider = CONFIG["llm_provider"].lower()
    if provider == "mock":
        return get_mock_advice(packet, user_query, language, advice_request)
    if provider == "anthropic":
        return await get_anthropic_advice(packet, user_query, language, advice_request)
    if provider == "groq":
        return await get_groq_advice(packet, user_query, language, advice_request)
    if provider == "gemini":
        return await get_gemini_advice(packet, user_query, language, advice_request)
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {CONFIG['llm_provider']}")
