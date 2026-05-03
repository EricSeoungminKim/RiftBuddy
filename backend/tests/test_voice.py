from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from backend.voice.stt import clean_transcript, contains_wake_word, is_valid_transcript, transcribe_audio_chunk
from backend.voice.tts import text_to_speech_bytes
from backend.voice.wake_word import SAMPLE_RATE, _record_question_until_silence, _rms, _strip_wake_words


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
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": ""}

    with patch("backend.voice.stt._get_model", return_value=mock_model):
        result = transcribe_audio_chunk(silent_audio, language="ko", model_name="base")

    assert isinstance(result, str)
    mock_model.transcribe.assert_called_once()
    np.testing.assert_array_equal(mock_model.transcribe.call_args.args[0], silent_audio)
    assert mock_model.transcribe.call_args.kwargs["language"] == "ko"
    assert mock_model.transcribe.call_args.kwargs["fp16"] is False
    assert "initial_prompt" in mock_model.transcribe.call_args.kwargs


def test_clean_transcript_removes_broken_noise_but_keeps_lol_terms():
    assert clean_transcript("디� op� speaker CS 밀리는데 바텀 가도 돼?") == "디 CS 밀리는데 바텀 가도 돼?"


def test_is_valid_transcript_rejects_empty_or_broken_noise():
    assert is_valid_transcript("") is False
    assert is_valid_transcript("op speaker") is False
    assert is_valid_transcript("바텀 웨이브 밀어도 돼?") is True


def test_record_question_keeps_minimum_audio_before_silence_stop():
    silent_frame = np.zeros(int(SAMPLE_RATE * 0.25), dtype=np.float32).reshape(-1, 1)
    speech_frame = np.ones(int(SAMPLE_RATE * 0.25), dtype=np.float32).reshape(-1, 1) * 0.2
    frames = [speech_frame, silent_frame, silent_frame, silent_frame, silent_frame]

    with patch.dict(
        "backend.voice.wake_word.CONFIG",
        {
            "question_max_seconds": "1.25",
            "question_min_seconds": "1.0",
            "question_silence_seconds": "0.5",
            "question_silence_threshold": "0.01",
        },
    ), patch("backend.voice.wake_word.sd.rec", side_effect=frames) as mock_rec, patch(
        "backend.voice.wake_word.sd.wait"
    ):
        audio = _record_question_until_silence()

    assert mock_rec.call_count == 4
    assert audio.size == int(SAMPLE_RATE * 0.25) * 4
