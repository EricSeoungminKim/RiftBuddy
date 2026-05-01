import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED = [
    "ANTHROPIC_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
]


def load_config(require_env: bool = True) -> dict[str, str]:
    missing = [key for key in REQUIRED if not os.getenv(key)]
    if missing and require_env:
        raise RuntimeError(f"Missing required env vars: {missing}")
    return {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
        "response_language": os.getenv("RIFTBUDDY_RESPONSE_LANGUAGE", "en"),
        "wake_word": os.getenv("RIFTBUDDY_WAKE_WORD", "0"),
        "wake_word_phrases": os.getenv(
            "RIFTBUDDY_WAKE_WORD_PHRASES",
            "롤롤아,롤롤 야,롤롤,roll roll,lol lol,hey buddy",
        ),
        "wake_stt_model": os.getenv(
            "RIFTBUDDY_WAKE_STT_MODEL",
            os.getenv("RIFTBUDDY_STT_MODEL", "tiny"),
        ),
        "question_stt_model": os.getenv(
            "RIFTBUDDY_QUESTION_STT_MODEL",
            os.getenv("RIFTBUDDY_STT_MODEL", "tiny"),
        ),
        "wake_stt_language": os.getenv(
            "RIFTBUDDY_WAKE_STT_LANGUAGE",
            os.getenv("RIFTBUDDY_STT_LANGUAGE", "ko"),
        ),
        "question_stt_language": os.getenv(
            "RIFTBUDDY_QUESTION_STT_LANGUAGE",
            os.getenv("RIFTBUDDY_STT_LANGUAGE", "ko"),
        ),
        "wake_chunk_seconds": os.getenv("RIFTBUDDY_WAKE_CHUNK_SECONDS", "3"),
        "question_max_seconds": os.getenv("RIFTBUDDY_QUESTION_MAX_SECONDS", "10"),
        "question_silence_seconds": os.getenv("RIFTBUDDY_QUESTION_SILENCE_SECONDS", "1.2"),
        "question_silence_threshold": os.getenv("RIFTBUDDY_QUESTION_SILENCE_THRESHOLD", "0.01"),
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", ""),
        "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", ""),
        "elevenlabs_model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"),
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", ""),
        "riot_api_key": os.getenv("RIOT_API_KEY", ""),
        "test_mode": os.getenv("RIFTBUDDY_TEST_MODE", "0"),
        "bypass_auth": os.getenv("RIFTBUDDY_BYPASS_AUTH", "0"),
    }


CONFIG = load_config(require_env=os.getenv("RIFTBUDDY_REQUIRE_ENV") == "1")
