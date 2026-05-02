import re
from typing import Optional

import anthropic
import httpx

from backend.config import CONFIG
from backend.context.engine import ContextPacket

anthropic_client = anthropic.AsyncAnthropic(api_key=CONFIG["anthropic_api_key"] or "test-key")

SYSTEM_PROMPT = """You are RiftBuddy, an expert League of Legends duo partner and coach.
You give concise, actionable macro advice in 1-2 sentences.
Be encouraging and direct. Never give generic advice; always tie it to the current game state."""

KOREAN_ONLY_PROMPT = """You are RiftBuddy, an expert League of Legends duo partner and coach.
Respond in Korean sentences using natural Korean League of Legends server terms.
Allowed LoL terms include 탑, 정글, 미드, 바텀, 서폿, CS, KDA, AP, AD, CC, 오브젝트, 라인, 웨이브, 귀환, 갱, 합류, 시야.
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
    return "Respond in natural English. Keep it short, direct, and game-callout style."


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


def get_mock_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en") -> str:
    if language == "ko":
        if packet.health_percent < 30:
            return f"체력이 {packet.health_percent:g}%라 위험해. 싸움 피하고 안전하게 귀환각을 먼저 봐."
        if packet.gold >= 2500:
            return f"{packet.gold:g}골드가 있으니 다음 웨이브만 안전하게 정리하고 귀환해서 아이템으로 바꿔."
        return f"현재 {packet.champion_name} 레벨 {packet.level}, CS {packet.creep_score}야. 시야 잡고 무리한 교전은 피하면서 다음 스파이크를 봐."

    if packet.health_percent < 30:
        return (
            "You are low health, so back off and look for a reset before forcing the next play. "
            f"You have {packet.gold:g} gold at level {packet.level}, which is enough to turn into tempo."
        )
    if user_query and "push" in user_query.lower():
        return (
            "You are healthy enough to pressure the wave. Push only if you know the enemy jungler's position; "
            "otherwise hold the wave closer to safety."
        )
    if packet.gold >= 2500:
        return (
            f"You are sitting on {packet.gold:g} gold, so plan a clean recall after the next safe wave. "
            "Spend that lead before the next objective fight."
        )
    return (
        f"You are {packet.health_percent:g}% HP at level {packet.level}. "
        "Play for vision, farm safely, and avoid coin-flip fights until your next item spike."
    )


def build_user_content(packet: ContextPacket, user_query: Optional[str], language: str = "en") -> str:
    role_line = ""
    if packet.champion_name != "Unknown" and packet.assigned_position != "UNKNOWN":
        role_line = f"Player role: {packet.champion_name} ({packet.assigned_position})\n"
    user_content = f"{role_line}Current game state:\n{packet.summary}"
    if user_query:
        user_content += f"\n\nPlayer asks: {user_query}"
    elif language == "ko":
        user_content += "\n\nPlayer asks: 지금 가장 중요한 다음 행동은 뭐야?"
    else:
        user_content += "\n\nWhat should I focus on right now?"
    user_content += f"\n\nLanguage instruction: {_language_instruction(language)}"
    return user_content


async def get_anthropic_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en") -> str:
    user_content = build_user_content(packet, user_query, language)
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


async def get_groq_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en") -> str:
    if not CONFIG["groq_api_key"]:
        raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

    payload = {
        "model": CONFIG["groq_model"],
        "max_tokens": 150,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": _system_prompt(language)},
            {"role": "user", "content": build_user_content(packet, user_query, language)},
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


async def get_gemini_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en") -> str:
    if not CONFIG["gemini_api_key"]:
        raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

    url = (
        f"{GEMINI_GENERATE_CONTENT_URL}/{CONFIG['gemini_model']}:generateContent"
        f"?key={CONFIG['gemini_api_key']}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": _system_prompt(language)}]},
        "contents": [{"parts": [{"text": build_user_content(packet, user_query, language)}]}],
        "generationConfig": {"maxOutputTokens": 150, "temperature": 0.4},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return clean_response_language(data["candidates"][0]["content"]["parts"][0]["text"], language)


async def get_advice(packet: ContextPacket, user_query: Optional[str], language: str = "en") -> str:
    provider = CONFIG["llm_provider"].lower()
    if provider == "mock":
        return get_mock_advice(packet, user_query, language)
    if provider == "anthropic":
        return await get_anthropic_advice(packet, user_query, language)
    if provider == "groq":
        return await get_groq_advice(packet, user_query, language)
    if provider == "gemini":
        return await get_gemini_advice(packet, user_query, language)
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {CONFIG['llm_provider']}")
