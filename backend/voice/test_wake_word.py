import asyncio

from backend.voice.wake_word import _record_chunk
from backend.voice.stt import contains_wake_word, transcribe_audio_chunk
from backend.config import CONFIG


async def main() -> None:
    print("Speak a wake phrase now. Recording 2 seconds...")
    audio = await asyncio.to_thread(_record_chunk)
    transcript = await asyncio.to_thread(
        transcribe_audio_chunk,
        audio,
        CONFIG["wake_stt_language"],
        CONFIG["wake_stt_model"],
    )
    print(f"transcript={transcript!r}")
    print(f"wake_word_detected={contains_wake_word(transcript)}")


if __name__ == "__main__":
    asyncio.run(main())
