"""Unified audio processing service for STT and TTS integration."""

from functools import lru_cache
from typing import Any

import numpy as np
import structlog

from src.services.stt_gradio import STTService, get_stt_service
from src.utils.config import settings

logger = structlog.get_logger(__name__)

# Type stub for TTS service (will be imported when available)
try:
    from src.services.tts_modal import TTSService, get_tts_service

    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False
    TTSService = None  # type: ignore[assignment, misc]
    get_tts_service = None  # type: ignore[assignment, misc]


class AudioService:
    """Unified audio processing service."""

    def __init__(
        self,
        stt_service: STTService | None = None,
        tts_service: Any | None = None,
    ) -> None:
        """Initialize audio service with STT and TTS.

        Args:
            stt_service: STT service instance (default: get_stt_service())
            tts_service: TTS service instance (default: get_tts_service() if available)
        """
        self.stt = stt_service or get_stt_service()

        # TTS is optional (requires Modal)
        if tts_service is not None:
            self.tts = tts_service
        elif _TTS_AVAILABLE and settings.modal_available:
            try:
                self.tts = get_tts_service()  # type: ignore[misc]
            except Exception as e:
                logger.warning("tts_service_unavailable", error=str(e))
                self.tts = None
        else:
            self.tts = None

    async def process_audio_input(
        self,
        audio_input: tuple[int, np.ndarray[Any, Any]] | None,  # type: ignore[type-arg]
        hf_token: str | None = None,
    ) -> str | None:
        """Process audio input and return transcribed text.

        Args:
            audio_input: Tuple of (sample_rate, audio_array) or None
            hf_token: HuggingFace token for authenticated Gradio Spaces

        Returns:
            Transcribed text string or None if no audio input
        """
        if audio_input is None:
            return None

        try:
            transcribed_text = await self.stt.transcribe_audio(audio_input, hf_token=hf_token)
            logger.info("audio_input_processed", text_length=len(transcribed_text))
            return transcribed_text
        except Exception as e:
            logger.error("audio_input_processing_failed", error=str(e))
            # Return None on failure (graceful degradation)
            return None

    async def generate_audio_output(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> tuple[int, np.ndarray[Any, Any]] | None:  # type: ignore[type-arg]
        """Generate audio output from text.

        Args:
            text: Text to synthesize
            voice: Voice ID (default: settings.tts_voice)
            speed: Speech speed (default: settings.tts_speed)

        Returns:
            Tuple of (sample_rate, audio_array) or None if TTS unavailable
        """
        if self.tts is None:
            logger.warning("tts_unavailable", message="TTS service not available")
            return None

        if not text or not text.strip():
            logger.warning("empty_text_for_tts")
            return None

        try:
            # Use provided voice/speed or fallback to settings defaults
            voice = voice if voice else settings.tts_voice
            speed = speed if speed is not None else settings.tts_speed

            audio_output = await self.tts.synthesize_async(text, voice, speed)  # type: ignore[misc]

            if audio_output:
                logger.info(
                    "audio_output_generated",
                    text_length=len(text),
                    sample_rate=audio_output[0],
                )

            return audio_output  # type: ignore[no-any-return]

        except Exception as e:
            logger.error("audio_output_generation_failed", error=str(e))
            # Return None on failure (graceful degradation)
            return None


@lru_cache(maxsize=1)
def get_audio_service() -> AudioService:
    """Get or create singleton audio service instance.

    Returns:
        AudioService instance
    """
    return AudioService()
