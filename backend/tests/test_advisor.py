from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.context.engine import ContextPacket
from backend.llm.advisor import (
    clean_response_language,
    get_advice,
    get_gemini_advice,
    get_groq_advice,
    get_mock_advice,
)


@pytest.mark.asyncio
async def test_get_advice_returns_string():
    packet = ContextPacket(
        health_percent=45.0,
        gold=1800,
        level=7,
        game_time_minutes=8.5,
        summary="Player is moderate health (45% HP). Gold: 1800. Level: 7. Game time: 8.5 minutes.",
    )
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Consider recalling to base to restore health.")]

    with patch.dict("backend.llm.advisor.CONFIG", {"llm_provider": "anthropic"}), patch(
        "backend.llm.advisor.anthropic_client"
    ) as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        advice = await get_advice(packet, user_query=None)

    assert isinstance(advice, str)


def test_get_mock_advice_low_health():
    packet = ContextPacket(
        health_percent=20.0,
        gold=900,
        level=5,
        game_time_minutes=5.0,
        summary="Player is low health (20% HP). Gold: 900. Level: 5. Game time: 5.0 minutes.",
    )

    advice = get_mock_advice(packet, user_query=None)

    assert "back off" in advice.lower() or "health" in advice.lower()
    assert len(advice) > 0


def test_clean_response_language_keeps_korean_lol_terms():
    text = "Focus on CS and KDA before bottom lane objective."

    cleaned = clean_response_language(text, "ko")

    assert "Focus" not in cleaned
    assert "bottom lane" not in cleaned
    assert "집중하세요" in cleaned
    assert "CS" in cleaned
    assert "KDA" in cleaned
    assert "바텀" in cleaned
    assert "오브젝트" in cleaned


def test_clean_response_language_normalizes_lane_terms():
    text = "Go bottom lane, then help jungle and support around middle lane."

    cleaned = clean_response_language(text, "ko")

    assert "bottom lane" not in cleaned
    assert "jungle" not in cleaned
    assert "support" not in cleaned
    assert "middle lane" not in cleaned
    assert "바텀" in cleaned
    assert "정글" in cleaned
    assert "서폿" in cleaned
    assert "미드" in cleaned


@pytest.mark.asyncio
async def test_get_groq_advice_posts_chat_completion_payload():
    packet = ContextPacket(
        health_percent=80.0,
        gold=3200,
        level=11,
        game_time_minutes=15.0,
        summary="Player is healthy (80% HP). Gold: 3200. Level: 11. Game time: 15.0 minutes.",
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Push the wave, then reset before dragon."}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.dict(
        "backend.llm.advisor.CONFIG",
        {"groq_api_key": "test-key", "groq_model": "llama-3.3-70b-versatile"},
    ), patch("backend.llm.advisor.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        advice = await get_groq_advice(packet, user_query="should I push?")

    assert "Push" in advice
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["model"] == "llama-3.3-70b-versatile"
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_get_groq_advice_uses_korean_only_system_prompt():
    packet = ContextPacket(
        health_percent=80.0,
        gold=3200,
        level=11,
        game_time_minutes=15.0,
        summary="Player is healthy (80% HP). Gold: 3200. Level: 11. Game time: 15.0 minutes.",
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Focus on CS, then recall."}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.dict(
        "backend.llm.advisor.CONFIG",
        {"groq_api_key": "test-key", "groq_model": "llama-3.3-70b-versatile"},
    ), patch("backend.llm.advisor.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        advice = await get_groq_advice(packet, user_query="지금 뭐 해야 해?", language="ko")

    _, kwargs = mock_client.post.call_args
    assert "Korean League of Legends server terms" in kwargs["json"]["messages"][0]["content"]
    assert "CS" in advice
    assert "집중하세요" in advice


@pytest.mark.asyncio
async def test_get_gemini_advice_posts_generate_content_payload():
    packet = ContextPacket(
        health_percent=70.0,
        gold=1200,
        level=8,
        game_time_minutes=10.0,
        summary="Player is healthy (70% HP). Gold: 1200. Level: 8. Game time: 10.0 minutes.",
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Hold the wave and ward river."}]}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.dict(
        "backend.llm.advisor.CONFIG",
        {"gemini_api_key": "test-key", "gemini_model": "gemini-2.5-flash"},
    ), patch("backend.llm.advisor.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        advice = await get_gemini_advice(packet, user_query=None)

    assert "ward" in advice
    url = mock_client.post.call_args.args[0]
    assert "gemini-2.5-flash:generateContent" in url
    assert "key=test-key" in url


@pytest.mark.asyncio
async def test_get_advice_with_user_query():
    packet = ContextPacket(
        health_percent=80.0,
        gold=3200,
        level=11,
        game_time_minutes=15.0,
        summary="Player is healthy (80% HP). Gold: 3200. Level: 11. Game time: 15.0 minutes.",
    )
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="You should push the wave and take dragon.")]

    with patch.dict("backend.llm.advisor.CONFIG", {"llm_provider": "anthropic"}), patch(
        "backend.llm.advisor.anthropic_client"
    ) as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        advice = await get_advice(packet, user_query="should I push or freeze?")

    assert isinstance(advice, str)
