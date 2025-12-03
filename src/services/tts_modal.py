"""Text-to-Speech service using Kokoro 82M via Modal GPU."""

import asyncio
from functools import lru_cache
from typing import Any

import numpy as np
import structlog

from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

logger = structlog.get_logger(__name__)

# Kokoro TTS dependencies for Modal image
KOKORO_DEPENDENCIES = [
    "torch>=2.0.0",
    "transformers>=4.30.0",
    "numpy<2.0",
    # kokoro-82M can be installed from source:
    # git+https://github.com/hexgrad/kokoro.git
]

# Modal app and function definitions (module-level for Modal)
_modal_app: Any | None = None
_tts_function: Any | None = None


def _get_modal_app() -> Any:
    """Get or create Modal app instance."""
    global _modal_app
    if _modal_app is None:
        try:
            import modal

            # Validate Modal credentials before attempting lookup
            if not settings.modal_available:
                raise ConfigurationError(
                    "Modal credentials not configured. Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET environment variables."
                )

            # Validate token ID format (Modal token IDs are typically UUIDs or specific formats)
            token_id = settings.modal_token_id
            if token_id:
                # Basic validation: token ID should not be empty and should be a reasonable length
                if len(token_id.strip()) < 10:
                    raise ConfigurationError(
                        f"Modal token ID appears malformed (too short: {len(token_id)} chars). "
                        "Token ID should be a valid Modal token identifier."
                    )

            try:
                _modal_app = modal.App.lookup("deepcritical-tts", create_if_missing=True)
            except Exception as e:
                error_msg = str(e).lower()
                if "token" in error_msg or "malformed" in error_msg or "invalid" in error_msg:
                    raise ConfigurationError(
                        f"Modal token validation failed: {e}. "
                        "Please check that MODAL_TOKEN_ID and MODAL_TOKEN_SECRET are correctly set."
                    ) from e
                raise
        except ImportError as e:
            raise ConfigurationError(
                "Modal SDK not installed. Run: uv sync or pip install modal>=0.63.0"
            ) from e
    return _modal_app


# Define Modal image with Kokoro dependencies (module-level)
def _get_tts_image() -> Any:
    """Get Modal image with Kokoro dependencies."""
    try:
        import modal

        return (
            modal.Image.debian_slim(python_version="3.11")
            .pip_install(*KOKORO_DEPENDENCIES)
            .pip_install("git+https://github.com/hexgrad/kokoro.git")
        )
    except ImportError:
        return None


def _setup_modal_function() -> None:
    """Setup Modal GPU function for TTS (called once, lazy initialization).

    Note: GPU type is set at function definition time. Changes to settings.tts_gpu
    require app restart to take effect.
    """
    global _tts_function

    if _tts_function is not None:
        return  # Already set up

    try:
        app = _get_modal_app()
        tts_image = _get_tts_image()

        if tts_image is None:
            raise ConfigurationError("Modal image setup failed")

        # Get GPU and timeout from settings (with defaults)
        # Note: These are evaluated at function definition time, not at call time
        # Changes to settings require app restart
        gpu_type = getattr(settings, "tts_gpu", None) or "T4"
        timeout_seconds = getattr(settings, "tts_timeout", None) or 60

        # Define GPU function at module level (required by Modal)
        # Modal functions are immutable once defined, so GPU changes require restart
        @app.function(  # type: ignore[misc]
            image=tts_image,
            gpu=gpu_type,
            timeout=timeout_seconds,
        )
        def kokoro_tts_function(
            text: str, voice: str, speed: float
        ) -> tuple[int, np.ndarray[Any, Any]]:  # type: ignore[type-arg]
            """Modal GPU function for Kokoro TTS.

            This function runs on Modal's GPU infrastructure.
            Based on: https://huggingface.co/spaces/hexgrad/Kokoro-TTS
            Reference: https://huggingface.co/spaces/hexgrad/Kokoro-TTS/raw/main/app.py
            """
            import numpy as np

            # Import Kokoro inside function (lazy load)
            try:
                from kokoro import KModel, KPipeline

                # Initialize model (cached on GPU)
                model = KModel().to("cuda").eval()
                pipeline = KPipeline(lang_code=voice[0])
                pack = pipeline.load_voice(voice)

                # Generate audio
                for _, ps, _ in pipeline(text, voice, speed):
                    ref_s = pack[len(ps) - 1]
                    audio = model(ps, ref_s, speed)
                    return (24000, audio.numpy())

                # If no audio generated, return empty
                return (24000, np.zeros(1, dtype=np.float32))

            except ImportError as e:
                raise ConfigurationError(
                    "Kokoro not installed. Install with: pip install git+https://github.com/hexgrad/kokoro.git"
                ) from e
            except Exception as e:
                raise ConfigurationError(f"TTS synthesis failed: {e}") from e

        # Store function reference for remote calls
        _tts_function = kokoro_tts_function

        # Verify function is properly attached to app
        if not hasattr(app, kokoro_tts_function.__name__):
            logger.warning(
                "modal_function_not_attached", function_name=kokoro_tts_function.__name__
            )

        logger.info(
            "modal_tts_function_setup_complete",
            gpu=gpu_type,
            timeout=timeout_seconds,
            function_name=kokoro_tts_function.__name__,
        )

    except Exception as e:
        logger.error("modal_tts_function_setup_failed", error=str(e))
        raise ConfigurationError(f"Failed to setup Modal TTS function: {e}") from e


class ModalTTSExecutor:
    """Execute Kokoro TTS synthesis on Modal GPU.

    This class provides TTS synthesis using Kokoro 82M model on Modal's GPU infrastructure.
    Follows the same pattern as ModalCodeExecutor but uses GPU functions for TTS.
    """

    def __init__(self) -> None:
        """Initialize Modal TTS executor.

        Note:
            Logs a warning if Modal credentials are not configured.
            Execution will fail at runtime without valid credentials.
        """
        # Check for Modal credentials
        if not settings.modal_available:
            logger.warning(
                "Modal credentials not found. TTS will not be available unless modal setup is run."
            )

    def synthesize(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        timeout: int = 60,
    ) -> tuple[int, np.ndarray[Any, Any]]:  # type: ignore[type-arg]
        """Synthesize text to speech using Kokoro on Modal GPU.

        Args:
            text: Text to synthesize (max 5000 chars for free tier)
            voice: Voice ID from Kokoro (e.g., af_heart, af_bella, am_michael)
            speed: Speech speed multiplier (0.5-2.0)
            timeout: Maximum execution time (not used, Modal function has its own timeout)

        Returns:
            Tuple of (sample_rate, audio_array)

        Raises:
            ConfigurationError: If synthesis fails
        """
        # Setup Modal function if not already done
        _setup_modal_function()

        if _tts_function is None:
            raise ConfigurationError("Modal TTS function not initialized")

        logger.info("synthesizing_tts", text_length=len(text), voice=voice, speed=speed)

        try:
            # Call the GPU function remotely
            result = _tts_function.remote(text, voice, speed)

            logger.info(
                "tts_synthesis_complete", sample_rate=result[0], audio_shape=result[1].shape
            )

            return result  # type: ignore[no-any-return]

        except Exception as e:
            logger.error("tts_synthesis_failed", error=str(e), error_type=type(e).__name__)
            raise ConfigurationError(f"TTS synthesis failed: {e}") from e


class TTSService:
    """TTS service wrapper for async usage."""

    def __init__(self) -> None:
        """Initialize TTS service."""
        if not settings.modal_available:
            raise ConfigurationError("Modal credentials required for TTS")
        self.executor = ModalTTSExecutor()

    async def synthesize_async(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
    ) -> tuple[int, np.ndarray[Any, Any]] | None:  # type: ignore[type-arg]
        """Async wrapper for TTS synthesis.

        Args:
            text: Text to synthesize
            voice: Voice ID (default: settings.tts_voice)
            speed: Speech speed (default: settings.tts_speed)

        Returns:
            Tuple of (sample_rate, audio_array) or None if error
        """
        voice = voice or settings.tts_voice
        speed = speed or settings.tts_speed

        loop = asyncio.get_running_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.executor.synthesize(text, voice, speed),
            )
            return result
        except Exception as e:
            logger.error("tts_synthesis_async_failed", error=str(e))
            return None


@lru_cache(maxsize=1)
def get_tts_service() -> TTSService:
    """Get or create singleton TTS service instance.

    Returns:
        TTSService instance

    Raises:
        ConfigurationError: If Modal credentials not configured
    """
    return TTSService()
