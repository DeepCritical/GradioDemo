"""Text-to-Speech service using Kokoro 82M via Modal GPU."""

import asyncio
import os
from functools import lru_cache
from typing import Any

import numpy as np
import structlog

# Load .env file BEFORE importing Modal SDK
# Modal SDK reads MODAL_TOKEN_ID and MODAL_TOKEN_SECRET from environment on import
from dotenv import load_dotenv
load_dotenv()

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
_tts_image: Any | None = None


def _get_modal_app() -> Any:
    """Get or create Modal app instance.

    Retrieves Modal credentials directly from environment variables (.env file)
    instead of relying on settings configuration.
    """
    global _modal_app
    if _modal_app is None:
        try:
            import modal

            # Get credentials directly from environment variables
            token_id = os.getenv("MODAL_TOKEN_ID")
            token_secret = os.getenv("MODAL_TOKEN_SECRET")

            # Validate Modal credentials
            if not token_id or not token_secret:
                raise ConfigurationError(
                    "Modal credentials not found in environment. "
                    "Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in .env file."
                )

            # Validate token ID format (Modal token IDs are typically UUIDs or specific formats)
            if len(token_id.strip()) < 10:
                raise ConfigurationError(
                    f"Modal token ID appears malformed (too short: {len(token_id)} chars). "
                    "Token ID should be a valid Modal token identifier."
                )

            logger.info(
                "modal_credentials_loaded",
                token_id_prefix=token_id[:8] + "...",  # Log prefix for debugging
                has_secret=bool(token_secret),
            )

            try:
                _modal_app = modal.App("deepcritical-tts")
            except Exception as e:
                error_msg = str(e).lower()
                if "token" in error_msg or "malformed" in error_msg or "invalid" in error_msg:
                    raise ConfigurationError(
                        f"Modal token validation failed: {e}. "
                        "Please check that MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in .env are correctly set."
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
    global _tts_image
    if _tts_image is not None:
        return _tts_image

    try:
        import modal

        _tts_image = (
            modal.Image.debian_slim(python_version="3.11")
            .pip_install(*KOKORO_DEPENDENCIES)
            .pip_install("git+https://github.com/hexgrad/kokoro.git")
        )
        return _tts_image
    except ImportError:
        return None


# Modal TTS function - Using serialized=True to allow dynamic creation
# This will be initialized lazily when _setup_modal_function() is called
def _create_tts_function() -> Any:
    """Create the Modal TTS function using serialized=True.

    The serialized=True parameter allows the function to be defined outside
    of global scope, which is necessary for dynamic initialization.
    """
    app = _get_modal_app()
    tts_image = _get_tts_image()

    if tts_image is None:
        raise ConfigurationError("Modal image setup failed")

    # Get GPU and timeout from settings (with defaults)
    gpu_type = getattr(settings, "tts_gpu", None) or "T4"
    timeout_seconds = getattr(settings, "tts_timeout", None) or 60

    @app.function(
        image=tts_image,
        gpu=gpu_type,
        timeout=timeout_seconds,
        serialized=True,  # Allow function to be defined outside global scope
    )
    def kokoro_tts_function(text: str, voice: str, speed: float) -> tuple[int, np.ndarray]:
        """Modal GPU function for Kokoro TTS.

        This function runs on Modal's GPU infrastructure.
        Based on: https://huggingface.co/spaces/hexgrad/Kokoro-TTS
        Reference: https://huggingface.co/spaces/hexgrad/Kokoro-TTS/raw/main/app.py
        """
        import numpy as np

        # Import Kokoro inside function (lazy load)
        try:
            import torch
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

    return kokoro_tts_function


def _setup_modal_function() -> None:
    """Setup Modal GPU function for TTS (called once, lazy initialization).

    Looks up the deployed Modal function instead of creating a new one.
    This requires the 'deepcritical-tts' app to be deployed on Modal.

    To deploy: modal deploy <script_with_tts_function>.py
    """
    global _tts_function

    if _tts_function is not None:
        return  # Already set up

    try:
        import modal

        # Look up the deployed function from the Modal server
        # This requires the app to be deployed: modal deploy tts_modal.py
        _tts_function = modal.Function.from_name(
            "deepcritical-tts",
            "kokoro_tts_function"
        )

        logger.info(
            "modal_tts_function_lookup_complete",
            app_name="deepcritical-tts",
            function_name="kokoro_tts_function",
        )

    except Exception as e:
        logger.error("modal_tts_function_setup_failed", error=str(e))
        raise ConfigurationError(
            f"Failed to lookup Modal TTS function: {e}. "
            "Make sure the 'deepcritical-tts' app is deployed on Modal."
        ) from e


class ModalTTSExecutor:
    """Execute Kokoro TTS synthesis on Modal GPU.

    This class provides TTS synthesis using Kokoro 82M model on Modal's GPU infrastructure.
    Follows the same pattern as ModalCodeExecutor but uses GPU functions for TTS.
    """

    def __init__(self) -> None:
        """Initialize Modal TTS executor.

        Note:
            Logs a warning if Modal credentials are not configured in environment.
            Execution will fail at runtime without valid credentials in .env file.
        """
        # Check for Modal credentials directly from environment
        token_id = os.getenv("MODAL_TOKEN_ID")
        token_secret = os.getenv("MODAL_TOKEN_SECRET")

        if not token_id or not token_secret:
            logger.warning(
                "Modal credentials not found in environment. "
                "TTS will not be available. Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in .env file."
            )

    def synthesize(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        timeout: int = 60,
    ) -> tuple[int, np.ndarray]:
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

            return result

        except Exception as e:
            logger.error("tts_synthesis_failed", error=str(e), error_type=type(e).__name__)
            raise ConfigurationError(f"TTS synthesis failed: {e}") from e


class TTSService:
    """TTS service wrapper for async usage."""

    def __init__(self) -> None:
        """Initialize TTS service.

        Validates Modal credentials from environment variables (.env file).
        """
        # Check credentials directly from environment
        token_id = os.getenv("MODAL_TOKEN_ID")
        token_secret = os.getenv("MODAL_TOKEN_SECRET")

        if not token_id or not token_secret:
            raise ConfigurationError(
                "Modal credentials required for TTS. "
                "Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in .env file."
            )
        self.executor = ModalTTSExecutor()

    async def synthesize_async(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
    ) -> tuple[int, np.ndarray] | None:
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
