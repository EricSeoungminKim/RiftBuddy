from supabase import Client, create_client

from backend.config import CONFIG

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(CONFIG["supabase_url"], CONFIG["supabase_anon_key"])
    return _client


async def verify_token(jwt: str) -> dict | None:
    try:
        supabase = get_supabase()
        response = supabase.auth.get_user(jwt)
        return response.user.model_dump() if response.user else None
    except Exception:
        return None
