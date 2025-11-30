"""Speech-to-Text service using Gradio Client API."""

import asyncio
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import structlog
from gradio_client import Client, handle_file

from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

logger = structlog.get_logger(__name__)


class STTService:
    """STT service using nvidia/canary-1b-v2 Gradio Space."""

    def __init__(self, api_url: str | None = None, hf_token: str | None = None) -> None:
        """Initialize STT service.

        Args:
            api_url: Gradio Space URL (default: settings.stt_api_url)
            hf_token: HuggingFace token for authenticated Spaces (default: None)

        Raises:
            ConfigurationError: If API URL not configured
        """
        self.api_url = api_url or settings.stt_api_url
        if not self.api_url:
            raise ConfigurationError("STT API URL not configured")
        self.hf_token = hf_token
        self.client: Client | None = None

    async def _get_client(self, hf_token: str | None = None) -> Client:
        """Get or create Gradio Client (lazy initialization).

        Args:
            hf_token: HuggingFace token for authenticated Spaces (overrides instance token)

        Returns:
            Gradio Client instance
        """
        # Use provided token or instance token
        token = hf_token or self.hf_token
        
        # If client exists but token changed, recreate it
        if self.client is not None and token != self.hf_token:
            self.client = None
        
        if self.client is None:
            loop = asyncio.get_running_loop()
            # Pass token to Client for authenticated Spaces
            if token:
                self.client = await loop.run_in_executor(
                    None,
                    lambda: Client(self.api_url, hf_token=token),
                )
            else:
                self.client = await loop.run_in_executor(
                    None,
                    lambda: Client(self.api_url),
                )
            # Update instance token for future use
            self.hf_token = token
        return self.client

    async def transcribe_file(
        self,
        audio_path: str,
        source_lang: str | None = None,
        target_lang: str | None = None,
        hf_token: str | None = None,
    ) -> str:
        """Transcribe audio file using Gradio API.

        Args:
            audio_path: Path to audio file
            source_lang: Source language (default: settings.stt_source_lang)
            target_lang: Target language (default: settings.stt_target_lang)

        Returns:
            Transcribed text string

        Raises:
            ConfigurationError: If transcription fails
        """
        client = await self._get_client(hf_token=hf_token)
        source_lang = source_lang or settings.stt_source_lang
        target_lang = target_lang or settings.stt_target_lang

        logger.info(
            "transcribing_audio_file",
            audio_path=audio_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        try:
            # Call /transcribe_file API endpoint
            # API returns: (dataframe, csv_path, srt_path)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.predict(
                    audio_path=handle_file(audio_path),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    api_name="/transcribe_file",
                ),
            )

            # Extract transcription from result
            transcribed_text = self._extract_transcription(result)

            logger.info(
                "audio_transcription_complete",
                text_length=len(transcribed_text),
            )

            return transcribed_text

        except Exception as e:
            logger.error("audio_transcription_failed", error=str(e), error_type=type(e).__name__)
            raise ConfigurationError(f"Audio transcription failed: {e}") from e

    async def transcribe_audio(
        self,
        audio_data: tuple[int, np.ndarray],
        hf_token: str | None = None,
    ) -> str:
        """Transcribe audio numpy array to text.

        Args:
            audio_data: Tuple of (sample_rate, audio_array)

        Returns:
            Transcribed text string
        """
        sample_rate, audio_array = audio_data

        logger.info(
            "transcribing_audio_array",
            sample_rate=sample_rate,
            audio_shape=audio_array.shape,
        )

        # Save audio to temp file
        temp_path = self._save_audio_temp(audio_data)

        try:
            # Transcribe the temp file
            transcribed_text = await self.transcribe_file(temp_path, hf_token=hf_token)
            return transcribed_text
        finally:
            # Clean up temp file
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning("failed_to_cleanup_temp_file", path=temp_path, error=str(e))

    def _extract_transcription(self, api_result: tuple) -> str:
        """Extract transcription text from API result.

        Args:
            api_result: Tuple from Gradio API (dataframe, csv_path, srt_path)

        Returns:
            Extracted transcription text
        """
        # API returns: (dataframe, csv_path, srt_path)
        # Try to extract from dataframe first
        if isinstance(api_result, tuple) and len(api_result) >= 1:
            dataframe = api_result[0]
            if isinstance(dataframe, dict) and "data" in dataframe:
                # Extract text from dataframe rows
                rows = dataframe.get("data", [])
                if rows:
                    # Combine all text segments
                    text_segments = []
                    for row in rows:
                        if isinstance(row, list) and len(row) > 0:
                            # First column is usually the text
                            text_segments.append(str(row[0]))
                    if text_segments:
                        return " ".join(text_segments)

            # Fallback: try to read CSV file if available
            if len(api_result) >= 2 and api_result[1]:
                csv_path = api_result[1]
                try:
                    import pandas as pd

                    df = pd.read_csv(csv_path)
                    if "text" in df.columns:
                        return " ".join(df["text"].astype(str).tolist())
                    elif len(df.columns) > 0:
                        # Use first column
                        return " ".join(df.iloc[:, 0].astype(str).tolist())
                except Exception as e:
                    logger.warning("failed_to_read_csv", csv_path=csv_path, error=str(e))

        # Last resort: return empty string
        logger.warning("could_not_extract_transcription", result_type=type(api_result).__name__)
        return ""

    def _save_audio_temp(
        self,
        audio_data: tuple[int, np.ndarray],
    ) -> str:
        """Save audio numpy array to temporary WAV file.

        Args:
            audio_data: Tuple of (sample_rate, audio_array)

        Returns:
            Path to temporary WAV file
        """
        sample_rate, audio_array = audio_data

        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        )
        temp_path = temp_file.name
        temp_file.close()

        # Save audio using soundfile
        try:
            import soundfile as sf

            # Ensure audio is float32 and mono
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)

            # Handle stereo -> mono conversion
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)

            # Normalize to [-1, 1] range
            if audio_array.max() > 1.0 or audio_array.min() < -1.0:
                audio_array = audio_array / np.max(np.abs(audio_array))

            sf.write(temp_path, audio_array, sample_rate)

            logger.debug("saved_audio_temp", path=temp_path, sample_rate=sample_rate)

            return temp_path

        except ImportError:
            raise ConfigurationError(
                "soundfile not installed. Install with: uv add soundfile"
            ) from None
        except Exception as e:
            logger.error("failed_to_save_audio_temp", error=str(e))
            raise ConfigurationError(f"Failed to save audio to temp file: {e}") from e


@lru_cache(maxsize=1)
def get_stt_service() -> STTService:
    """Get or create singleton STT service instance.

    Returns:
        STTService instance
    """
    return STTService()

