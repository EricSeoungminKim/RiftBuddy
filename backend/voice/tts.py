import httpx

from backend.config import CONFIG

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
SILENT_MP3_BYTES = (
    b"\xff\xfb\x90\xc4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


class TextToSpeechError(RuntimeError):
    pass


async def text_to_speech_bytes(text: str) -> bytes:
    if CONFIG["test_mode"] == "1":
        return SILENT_MP3_BYTES

    voice_id = CONFIG["elevenlabs_voice_id"]
    headers = {
        "xi-api-key": CONFIG["elevenlabs_api_key"],
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": CONFIG["elevenlabs_model_id"],
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{ELEVENLABS_URL}/{voice_id}",
            json=payload,
            headers=headers,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TextToSpeechError(
                f"ElevenLabs TTS failed with {response.status_code}: {response.text}"
            ) from exc
        return response.content
