import numpy as np
from faster_whisper import WhisperModel

from backend.config import CONFIG

WAKE_WORDS = {phrase.strip().lower().strip("\"'") for phrase in CONFIG["wake_word_phrases"].split(",") if phrase.strip()}

_models: dict[str, WhisperModel] = {}


def _get_model(model_name: str) -> WhisperModel:
    if model_name not in _models:
        _models[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _models[model_name]


def transcribe_audio_chunk(audio: np.ndarray, language: str | None = None, model_name: str | None = None) -> str:
    model_name = model_name or CONFIG["question_stt_model"]
    model = _get_model(model_name)
    language = language if language is not None else CONFIG["question_stt_language"]
    language = language or None
    segments, _ = model.transcribe(audio, beam_size=1, language=language)
    return " ".join(segment.text.strip() for segment in segments).lower()


def contains_wake_word(transcript: str) -> bool:
    lower = transcript.lower().strip()
    return any(wake in lower for wake in WAKE_WORDS)
