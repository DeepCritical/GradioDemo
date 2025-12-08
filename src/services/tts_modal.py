"""Text-to-Speech service using Kokoro 82M via Modal GPU."""

import asyncio
import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
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


@contextmanager
def modal_credentials_override(token_id: str | None, token_secret: str | None) -> Iterator[None]:
    """Context manager to temporarily override Modal credentials.

    Args:
        token_id: Modal token ID (overrides env if provided)
        token_secret: Modal token secret (overrides env if provided)

    Yields:
        None

    Note:
        Resets global Modal state to force re-initialization with new credentials.
    """
    global _modal_app, _tts_function

    # Save original credentials
    original_token_id = os.environ.get("MODAL_TOKEN_ID")
    original_token_secret = os.environ.get("MODAL_TOKEN_SECRET")

    # Save original Modal state
    original_app = _modal_app
    original_function = _tts_function

    try:
        # Override environment variables if provided
        if token_id:
            os.environ["MODAL_TOKEN_ID"] = token_id
        if token_secret:
            os.environ["MODAL_TOKEN_SECRET"] = token_secret

        # Reset Modal state to force re-initialization
        _modal_app = None
        _tts_function = None

        yield

    finally:
        # Restore original credentials
        if original_token_id is not None:
            os.environ["MODAL_TOKEN_ID"] = original_token_id
        elif "MODAL_TOKEN_ID" in os.environ:
            del os.environ["MODAL_TOKEN_ID"]

        if original_token_secret is not None:
            os.environ["MODAL_TOKEN_SECRET"] = original_token_secret
        elif "MODAL_TOKEN_SECRET" in os.environ:
            del os.environ["MODAL_TOKEN_SECRET"]

        # Restore original Modal state
        _modal_app = original_app
        _tts_function = original_function


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
                # Use lookup with create_if_missing for inline function fallback
                _modal_app = modal.App.lookup("deepcritical-tts", create_if_missing=True)
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
    timeout_seconds = getattr(settings, "tts_timeout", None) or 120  # 2 minutes for cold starts

    @app.function(
        image=tts_image,
        gpu=gpu_type,
        timeout=timeout_seconds,
        serialized=True,  # Allow function to be defined outside global scope
    )
    def kokoro_tts_function(text: str, voice: str, speed: float) -> tuple[int, NDArray[np.float32]]:
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

    Hybrid approach:
    1. Try to lookup pre-deployed function (fast path for advanced users)
    2. If lookup fails, create function inline (fallback for casual users)

    This allows both workflows:
    - Advanced: Deploy with `modal deploy deployments/modal_tts.py` for best performance
    - Casual: Just add Modal keys and it auto-creates function on first use
    """
    global _tts_function

    if _tts_function is not None:
        return  # Already set up

    try:
        import modal

        # Try path 1: Lookup pre-deployed function (fast path)
        try:
            _tts_function = modal.Function.from_name("deepcritical-tts", "kokoro_tts_function")
            logger.info(
                "modal_tts_function_lookup_success",
                app_name="deepcritical-tts",
                function_name="kokoro_tts_function",
                method="lookup",
            )
            return
        except Exception as lookup_error:
            logger.info(
                "modal_tts_function_lookup_failed",
                error=str(lookup_error),
                fallback="Creating function inline",
            )

        # Try path 2: Create function inline (fallback for casual users)
        logger.info("modal_tts_creating_inline_function")
        _tts_function = _create_tts_function()
        logger.info(
            "modal_tts_function_setup_complete",
            app_name="deepcritical-tts",
            function_name="kokoro_tts_function",
            method="inline",
        )

    except Exception as e:
        logger.error("modal_tts_function_setup_failed", error=str(e))
        raise ConfigurationError(
            f"Failed to setup Modal TTS function: {e}. "
            "Ensure Modal credentials (MODAL_TOKEN_ID, MODAL_TOKEN_SECRET) are valid."
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
        timeout: int = 120,
    ) -> tuple[int, NDArray[np.float32]]:
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
            result = cast(tuple[int, NDArray[np.float32]], _tts_function.remote(text, voice, speed))

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
    ) -> tuple[int, NDArray[np.float32]] | None:
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


async def generate_audio_on_demand(
    text: str,
    modal_token_id: str | None = None,
    modal_token_secret: str | None = None,
    voice: str = "af_heart",
    speed: float = 1.0,
    use_llm_polish: bool = False,
) -> tuple[tuple[int, NDArray[np.float32]] | None, str]:
    """Generate audio on-demand with optional runtime credentials.

    Args:
        text: Text to synthesize
        modal_token_id: Modal token ID (UI input, overrides .env)
        modal_token_secret: Modal token secret (UI input, overrides .env)
        voice: Voice ID (default: af_heart)
        speed: Speech speed (default: 1.0)
        use_llm_polish: Apply LLM polish to text (default: False)

    Returns:
        Tuple of (audio_output, status_message)
        - audio_output: (sample_rate, audio_array) or None if failed
        - status_message: Status/error message for user

    Priority: UI credentials > .env credentials
    """
    # Priority: UI keys > .env keys
    token_id = (modal_token_id or "").strip() or os.getenv("MODAL_TOKEN_ID")
    token_secret = (modal_token_secret or "").strip() or os.getenv("MODAL_TOKEN_SECRET")

    if not token_id or not token_secret:
        return (
            None,
            "❌ Modal credentials required. Enter keys above or set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in .env",
        )

    try:
        # Use credentials override context
        with modal_credentials_override(token_id, token_secret):
            # Import audio_processing here to avoid circular import
            from src.services.audio_processing import AudioService

            # Temporarily override LLM polish setting
            original_llm_polish = settings.tts_use_llm_polish
            try:
                settings.tts_use_llm_polish = use_llm_polish

                # Create fresh AudioService instance (bypass cache to pick up new credentials)
                audio_service = AudioService()
                audio_output = await audio_service.generate_audio_output(
                    text=text,
                    voice=voice,
                    speed=speed,
                )

                if audio_output:
                    return audio_output, "✅ Audio generated successfully"
                else:
                    return None, "⚠️ Audio generation returned no output"

            finally:
                settings.tts_use_llm_polish = original_llm_polish

    except ConfigurationError as e:
        logger.error("audio_generation_config_error", error=str(e))
        return None, f"❌ Configuration error: {e}"
    except Exception as e:
        logger.error("audio_generation_failed", error=str(e), exc_info=True)
        return None, f"❌ Audio generation failed: {e}"
