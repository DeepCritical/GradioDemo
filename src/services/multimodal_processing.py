"""Unified multimodal processing service for text, audio, and image inputs."""

from functools import lru_cache
from typing import Any

import structlog
from gradio.data_classes import FileData

from src.services.audio_processing import AudioService, get_audio_service
from src.services.image_ocr import ImageOCRService, get_image_ocr_service
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class MultimodalService:
    """Unified multimodal processing service."""

    def __init__(
        self,
        audio_service: AudioService | None = None,
        ocr_service: ImageOCRService | None = None,
    ) -> None:
        """Initialize multimodal service.

        Args:
            audio_service: Audio service instance (default: get_audio_service())
            ocr_service: Image OCR service instance (default: get_image_ocr_service())
        """
        self.audio = audio_service or get_audio_service()
        self.ocr = ocr_service or get_image_ocr_service()

    async def process_multimodal_input(
        self,
        text: str,
        files: list[FileData] | None = None,
        audio_input: tuple[int, Any] | None = None,
        hf_token: str | None = None,
    ) -> str:
        """Process multimodal input (text + images + audio) and return combined text.

        Args:
            text: Text input string
            files: List of uploaded files (images, audio, etc.)
            audio_input: Audio input tuple (sample_rate, audio_array)
            hf_token: HuggingFace token for authenticated Gradio Spaces

        Returns:
            Combined text from all inputs
        """
        text_parts: list[str] = []

        # Add original text if present
        if text and text.strip():
            text_parts.append(text.strip())

        # Process audio input
        if audio_input is not None and settings.enable_audio_input:
            try:
                transcribed = await self.audio.process_audio_input(audio_input, hf_token=hf_token)
                if transcribed:
                    text_parts.append(f"[Audio transcription: {transcribed}]")
            except Exception as e:
                logger.warning("audio_processing_failed", error=str(e))

        # Process uploaded files
        if files:
            for file_data in files:
                file_path = file_data.path if isinstance(file_data, FileData) else str(file_data)

                # Check if it's an image
                if self._is_image_file(file_path):
                    try:
                        extracted_text = await self.ocr.extract_text(file_path, hf_token=hf_token)
                        if extracted_text:
                            text_parts.append(f"[Image OCR: {extracted_text}]")
                    except Exception as e:
                        logger.warning("image_ocr_failed", file_path=file_path, error=str(e))

                # Check if it's an audio file
                elif self._is_audio_file(file_path):
                    try:
                        # For audio files, we'd need to load and transcribe
                        # For now, log a warning
                        logger.warning("audio_file_upload_not_supported", file_path=file_path)
                    except Exception as e:
                        logger.warning("audio_file_processing_failed", file_path=file_path, error=str(e))

        # Combine all text parts
        combined_text = "\n\n".join(text_parts) if text_parts else ""

        logger.info(
            "multimodal_input_processed",
            text_length=len(combined_text),
            num_files=len(files) if files else 0,
            has_audio=audio_input is not None,
        )

        return combined_text

    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is an image.

        Args:
            file_path: Path to file

        Returns:
            True if file is an image
        """
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
        return any(file_path.lower().endswith(ext) for ext in image_extensions)

    def _is_audio_file(self, file_path: str) -> bool:
        """Check if file is an audio file.

        Args:
            file_path: Path to file

        Returns:
            True if file is an audio file
        """
        audio_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
        return any(file_path.lower().endswith(ext) for ext in audio_extensions)


@lru_cache(maxsize=1)
def get_multimodal_service() -> MultimodalService:
    """Get or create singleton multimodal service instance.

    Returns:
        MultimodalService instance
    """
    return MultimodalService()



