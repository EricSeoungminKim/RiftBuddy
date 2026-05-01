import asyncio
import logging
from collections.abc import Awaitable, Callable

import numpy as np
import sounddevice as sd

from backend.config import CONFIG
from backend.voice.stt import contains_wake_word, transcribe_audio_chunk

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
QUESTION_FRAME_SECONDS = 0.25


def _record_chunk() -> np.ndarray:
    chunk_seconds = float(CONFIG["wake_chunk_seconds"])
    audio = sd.rec(
        int(SAMPLE_RATE * chunk_seconds),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    return audio.reshape(-1)


def _rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def _record_question_until_silence() -> np.ndarray:
    max_seconds = float(CONFIG["question_max_seconds"])
    silence_seconds = float(CONFIG["question_silence_seconds"])
    silence_threshold = float(CONFIG["question_silence_threshold"])
    frame_samples = int(SAMPLE_RATE * QUESTION_FRAME_SECONDS)
    max_frames = max(1, int(max_seconds / QUESTION_FRAME_SECONDS))
    max_silent_frames = max(1, int(silence_seconds / QUESTION_FRAME_SECONDS))

    frames: list[np.ndarray] = []
    silent_frames = 0
    speech_started = False

    for _ in range(max_frames):
        frame = sd.rec(frame_samples, samplerate=SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        flat = frame.reshape(-1)
        volume = _rms(flat)

        if volume >= silence_threshold:
            speech_started = True
            silent_frames = 0
        elif speech_started:
            silent_frames += 1

        if speech_started:
            frames.append(flat)

        if speech_started and silent_frames >= max_silent_frames:
            break

    if not frames:
        return np.array([], dtype=np.float32)
    return np.concatenate(frames)


def _strip_wake_words(transcript: str) -> str:
    cleaned = transcript
    for phrase in CONFIG["wake_word_phrases"].split(","):
        wake = phrase.strip().lower().strip("\"'")
        if wake:
            cleaned = cleaned.replace(wake, " ")
    return " ".join(cleaned.split()).strip()


async def run_wake_word_loop(
    on_wake: Callable[[str], Awaitable[None]],
    on_question: Callable[[str], Awaitable[None]],
) -> None:
    logger.info(
        "Wake word listener started. phrases=%s model=%s language=%s",
        sorted(CONFIG["wake_word_phrases"].split(",")),
        {"wake": CONFIG["wake_stt_model"], "question": CONFIG["question_stt_model"]},
        {"wake": CONFIG["wake_stt_language"], "question": CONFIG["question_stt_language"]},
    )

    while True:
        try:
            audio = await asyncio.to_thread(_record_chunk)
            transcript = await asyncio.to_thread(
                transcribe_audio_chunk,
                audio,
                CONFIG["wake_stt_language"],
                CONFIG["wake_stt_model"],
            )
            if transcript:
                logger.info("Wake word transcript: %s", transcript)

            if transcript and contains_wake_word(transcript):
                question = _strip_wake_words(transcript)
                logger.info("Wake word detected: %s", transcript)
                await on_wake(transcript)
                if question:
                    await on_question(question)
                else:
                    question_audio = await asyncio.to_thread(_record_question_until_silence)
                    if question_audio.size == 0:
                        logger.info("No question speech captured after wake word")
                        continue
                    question = await asyncio.to_thread(
                        transcribe_audio_chunk,
                        question_audio,
                        CONFIG["question_stt_language"],
                        CONFIG["question_stt_model"],
                    )
                    question = _strip_wake_words(question)
                    if question:
                        logger.info("Wake word question captured: %s", question)
                        await on_question(question)
                    else:
                        logger.info("Question audio captured but transcript was empty")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Wake word listener error: %s", exc)
            await asyncio.sleep(2)
