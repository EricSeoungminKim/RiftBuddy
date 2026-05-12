import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED = [
    "ANTHROPIC_API_KEY",
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
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", ""),
        "riot_api_key": os.getenv("RIOT_API_KEY", ""),
        "riot_game_name": os.getenv("RIOT_GAME_NAME", ""),
        "riot_tag_line": os.getenv("RIOT_TAG_LINE", ""),
        "riot_region": os.getenv("RIOT_REGION", "KR"),
        "riot_benchmark_tier": os.getenv("RIOT_BENCHMARK_TIER", "DIAMOND"),
        "riot_benchmark_samples": os.getenv("RIOT_BENCHMARK_SAMPLES", "25"),
        "riot_benchmark_matches_per_player": os.getenv("RIOT_BENCHMARK_MATCHES_PER_PLAYER", "3"),
        "riot_benchmark_ttl_seconds": os.getenv("RIOT_BENCHMARK_TTL_SECONDS", "604800"),
        "test_mode": os.getenv("RIFTBUDDY_TEST_MODE", "0"),
        "bypass_auth": os.getenv("RIFTBUDDY_BYPASS_AUTH", "0"),
    }


CONFIG = load_config(require_env=os.getenv("RIFTBUDDY_REQUIRE_ENV") == "1")
