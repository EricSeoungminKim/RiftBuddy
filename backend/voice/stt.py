import re

import numpy as np
import whisper

from backend.config import CONFIG

WAKE_WORDS = {phrase.strip().lower().strip("\"'") for phrase in CONFIG["wake_word_phrases"].split(",") if phrase.strip()}
STT_INITIAL_PROMPT = (
    "한국어 League of Legends 질문입니다. 사용자는 한국어로 말하지만 롤 용어를 섞어 말할 수 있습니다. "
    "자주 나오는 단어: 탑, 정글, 미드, 바텀, 서폿, CS, KDA, 오브젝트, 용, 바론, 전령, 라인, 웨이브, "
    "귀환, 갱, 합류, 시야, 와드, 플래시, 점멸, 텔, 궁, 스킬, 로밍, 다이브, 프리징, 푸쉬."
)
ALLOWED_SHORT_ROMAN_TERMS = {"CS", "KDA", "AP", "AD", "CC"}
NOISE_WORDS = {
    "op",
    "speaker",
    "music",
    "subtitle",
    "subtitles",
    "caption",
    "captions",
}

_models: dict[str, whisper.Whisper] = {}


def _get_model(model_name: str) -> whisper.Whisper:
    if model_name not in _models:
        _models[model_name] = whisper.load_model(model_name, device="cpu")
    return _models[model_name]


def transcribe_audio_chunk(audio: np.ndarray, language: str | None = None, model_name: str | None = None) -> str:
    model_name = model_name or CONFIG["question_stt_model"]
    model = _get_model(model_name)
    language = language if language is not None else CONFIG["question_stt_language"]
    language = language or None
    kwargs = {"language": language, "fp16": False}
    if language == "ko":
        kwargs["initial_prompt"] = STT_INITIAL_PROMPT
    result = model.transcribe(audio.astype(np.float32), **kwargs)
    return clean_transcript(str(result.get("text", "")))


def clean_transcript(transcript: str) -> str:
    cleaned = transcript.replace("�", " ")
    cleaned = re.sub(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff]+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ?.!,%#/-]", " ", cleaned)
    words = []
    for word in cleaned.split():
        stripped = word.strip(".,!?")
        upper = stripped.upper()
        lower = stripped.lower()
        has_korean = bool(re.search(r"[가-힣]", stripped))
        has_digit = bool(re.search(r"\d", stripped))
        if lower in NOISE_WORDS:
            continue
        if re.fullmatch(r"[A-Za-z]{1,2}", stripped) and upper not in ALLOWED_SHORT_ROMAN_TERMS:
            continue
        if re.fullmatch(r"[A-Za-z]{3,}", stripped) and upper not in ALLOWED_SHORT_ROMAN_TERMS:
            continue
        if not has_korean and not has_digit and re.search(r"[A-Za-z]", stripped) and upper not in ALLOWED_SHORT_ROMAN_TERMS:
            continue
        words.append(word if upper not in ALLOWED_SHORT_ROMAN_TERMS else upper)
    return " ".join(words).strip()


def is_valid_transcript(transcript: str) -> bool:
    if not transcript.strip():
        return False
    if "�" in transcript:
        return False
    has_korean = bool(re.search(r"[가-힣]", transcript))
    has_allowed_term = any(term in transcript.upper().split() for term in ALLOWED_SHORT_ROMAN_TERMS)
    if not has_korean and not has_allowed_term:
        return False
    meaningful = re.sub(r"[^가-힣A-Za-z0-9]", "", transcript)
    return len(meaningful) >= 2


def contains_wake_word(transcript: str) -> bool:
    lower = transcript.lower().strip()
    return any(wake in lower for wake in WAKE_WORDS)
