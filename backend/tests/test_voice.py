from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from backend.voice.stt import contains_wake_word, transcribe_audio_chunk
from backend.voice.tts import text_to_speech_bytes
from backend.voice.wake_word import _rms, _strip_wake_words


@pytest.mark.asyncio
async def test_text_to_speech_returns_bytes():
    fake_audio = b"fake_audio_data_bytes"
    mock_response = MagicMock()
    mock_response.content = fake_audio
    mock_response.raise_for_status = MagicMock()

    with patch("backend.voice.tts.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await text_to_speech_bytes("Hello summoner")

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_text_to_speech_returns_silent_bytes_in_test_mode():
    with patch.dict("backend.voice.tts.CONFIG", {"test_mode": "1"}):
        result = await text_to_speech_bytes("Hello summoner")

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_contains_wake_word_positive():
    with patch("backend.voice.stt.WAKE_WORDS", {"hey buddy", "롤롤아"}):
        assert contains_wake_word("hey buddy should I push this wave") is True
        assert contains_wake_word("롤롤아 지금 뭐해") is True


def test_contains_wake_word_negative():
    assert contains_wake_word("I think we should push") is False
    assert contains_wake_word("") is False


def test_strip_wake_words_keeps_question():
    with patch.dict(
        "backend.voice.wake_word.CONFIG",
        {"wake_word_phrases": "롤롤아,롤롤 야,롤롤,roll roll,lol lol,hey buddy"},
    ):
        assert _strip_wake_words("롤롤아 지금 집 가야 돼") == "지금 집 가야 돼"


def test_rms_detects_silence_and_speech():
    assert _rms(np.zeros(16000, dtype=np.float32)) == 0.0
    assert _rms(np.ones(16000, dtype=np.float32) * 0.5) > 0.4


def test_transcribe_audio_chunk_returns_string():
    silent_audio = np.zeros(16000, dtype=np.float32)
    segment = MagicMock()
    segment.text = ""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([segment], None)

    with patch("backend.voice.stt._get_model", return_value=mock_model):
        result = transcribe_audio_chunk(silent_audio, language="ko", model_name="base")

    assert isinstance(result, str)
    mock_model.transcribe.assert_called_once()
    assert mock_model.transcribe.call_args.args == (silent_audio,)
    assert mock_model.transcribe.call_args.kwargs["language"] == "ko"
