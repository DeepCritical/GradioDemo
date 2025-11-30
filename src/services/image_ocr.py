"""Image-to-text service using Gradio Client API (Multimodal-OCR3)."""

import asyncio
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import structlog
from gradio_client import Client, handle_file
from PIL import Image

from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

logger = structlog.get_logger(__name__)


class ImageOCRService:
    """Image OCR service using prithivMLmods/Multimodal-OCR3 Gradio Space."""

    def __init__(self, api_url: str | None = None, hf_token: str | None = None) -> None:
        """Initialize Image OCR service.

        Args:
            api_url: Gradio Space URL (default: settings.ocr_api_url)
            hf_token: HuggingFace token for authenticated Spaces (default: None)

        Raises:
            ConfigurationError: If API URL not configured
        """
        self.api_url = api_url or settings.ocr_api_url
        if not self.api_url:
            raise ConfigurationError("OCR API URL not configured")
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
            # Gradio Client uses 'token' parameter, not 'hf_token'
            if token:
                self.client = await loop.run_in_executor(
                    None,
                    lambda: Client(self.api_url, token=token),
                )
            else:
                self.client = await loop.run_in_executor(
                    None,
                    lambda: Client(self.api_url),
                )
            # Update instance token for future use
            self.hf_token = token
        return self.client

    async def extract_text(
        self,
        image_path: str,
        model: str | None = None,
        hf_token: str | None = None,
    ) -> str:
        """Extract text from image using Gradio API.

        Args:
            image_path: Path to image file
            model: Optional model selection (default: None, uses API default)

        Returns:
            Extracted text string

        Raises:
            ConfigurationError: If OCR extraction fails
        """
        client = await self._get_client(hf_token=hf_token)

        logger.info(
            "extracting_text_from_image",
            image_path=image_path,
            model=model,
        )

        try:
            # Call /Multimodal_OCR3_generate_image API endpoint
            # According to the MCP tool description, this yields raw text and Markdown-formatted text
            loop = asyncio.get_running_loop()

            # The API might require file upload first, then call the generate function
            # For now, we'll use handle_file to upload and pass the path
            result = await loop.run_in_executor(
                None,
                lambda: client.predict(
                    image_path=handle_file(image_path),
                    api_name="/Multimodal_OCR3_generate_image",
                ),
            )

            # Extract text from result
            extracted_text = self._extract_text_from_result(result)

            logger.info(
                "image_ocr_complete",
                text_length=len(extracted_text),
            )

            return extracted_text

        except Exception as e:
            logger.error("image_ocr_failed", error=str(e), error_type=type(e).__name__)
            raise ConfigurationError(f"Image OCR failed: {e}") from e

    async def extract_text_from_image(
        self,
        image_data: np.ndarray | Image.Image | str,
        hf_token: str | None = None,
    ) -> str:
        """Extract text from image data (numpy array, PIL Image, or file path).

        Args:
            image_data: Image as numpy array, PIL Image, or file path string

        Returns:
            Extracted text string
        """
        # Handle different input types
        if isinstance(image_data, str):
            # Assume it's a file path
            image_path = image_data
        elif isinstance(image_data, Image.Image):
            # Save PIL Image to temp file
            image_path = self._save_image_temp(image_data)
        elif isinstance(image_data, np.ndarray):
            # Convert numpy array to PIL Image, then save
            pil_image = Image.fromarray(image_data)
            image_path = self._save_image_temp(pil_image)
        else:
            raise ValueError(f"Unsupported image data type: {type(image_data)}")

        try:
            # Extract text from the image file
            extracted_text = await self.extract_text(image_path, hf_token=hf_token)
            return extracted_text
        finally:
            # Clean up temp file if we created it
            if image_path != image_data or not isinstance(image_data, str):
                try:
                    Path(image_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("failed_to_cleanup_temp_file", path=image_path, error=str(e))

    def _extract_text_from_result(self, api_result: Any) -> str:
        """Extract text from API result.

        Args:
            api_result: Result from Gradio API

        Returns:
            Extracted text string
        """
        # The API yields raw text and Markdown-formatted text
        # Result might be a string, tuple, or generator
        if isinstance(api_result, str):
            return api_result.strip()

        if isinstance(api_result, tuple):
            # Try to extract text from tuple
            for item in api_result:
                if isinstance(item, str):
                    return item.strip()
                # Check if it's a dict with text fields
                if isinstance(item, dict):
                    if "text" in item:
                        return str(item["text"]).strip()
                    if "content" in item:
                        return str(item["content"]).strip()

        # If result is a generator or async generator, we'd need to iterate
        # For now, convert to string representation
        if api_result is not None:
            text = str(api_result).strip()
            if text and text != "None":
                return text

        logger.warning("could_not_extract_text_from_result", result_type=type(api_result).__name__)
        return ""

    def _save_image_temp(self, image: Image.Image) -> str:
        """Save PIL Image to temporary file.

        Args:
            image: PIL Image object

        Returns:
            Path to temporary image file
        """
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        )
        temp_path = temp_file.name
        temp_file.close()

        try:
            # Save image as PNG
            image.save(temp_path, "PNG")

            logger.debug("saved_image_temp", path=temp_path, size=image.size)

            return temp_path

        except Exception as e:
            logger.error("failed_to_save_image_temp", error=str(e))
            raise ConfigurationError(f"Failed to save image to temp file: {e}") from e


@lru_cache(maxsize=1)
def get_image_ocr_service() -> ImageOCRService:
    """Get or create singleton Image OCR service instance.

    Returns:
        ImageOCRService instance
    """
    return ImageOCRService()




