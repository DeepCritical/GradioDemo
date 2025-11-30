"""Utility for converting markdown to PDF."""

import os
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

# Try to import md2pdf
try:
    from md2pdf import md2pdf

    _MD2PDF_AVAILABLE = True
except ImportError:
    md2pdf = None  # type: ignore[assignment, misc]
    _MD2PDF_AVAILABLE = False
    logger.warning("md2pdf not available - PDF generation will be disabled")


def get_css_path() -> Path:
    """Get the path to the markdown.css file."""
    curdir = Path(__file__).parent
    css_path = curdir / "markdown.css"
    return css_path


def md_to_pdf(md_text: str, pdf_file_path: str) -> None:
    """
    Convert markdown text to PDF.

    Args:
        md_text: Markdown text content
        pdf_file_path: Path where PDF should be saved

    Raises:
        ImportError: If md2pdf is not installed
        ValueError: If markdown text is empty
        OSError: If PDF file cannot be written
    """
    if not _MD2PDF_AVAILABLE:
        raise ImportError(
            "md2pdf is not installed. Install it with: pip install md2pdf"
        )

    if not md_text or not md_text.strip():
        raise ValueError("Markdown text cannot be empty")

    css_path = get_css_path()

    if not css_path.exists():
        logger.warning(
            "CSS file not found, PDF will be generated without custom styling",
            css_path=str(css_path),
        )
        # Generate PDF without CSS
        md2pdf(pdf_file_path, md_text)
    else:
        # Generate PDF with CSS
        md2pdf(pdf_file_path, md_text, css_file_path=str(css_path))

    logger.debug("PDF generated successfully", pdf_path=pdf_file_path)


