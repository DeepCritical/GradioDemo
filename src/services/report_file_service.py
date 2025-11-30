"""Service for saving research reports to files."""

import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog

from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

logger = structlog.get_logger()


class ReportFileService:
    """
    Service for saving research reports to files.

    Handles file creation, naming, and directory management for report outputs.
    Supports saving reports in multiple formats (markdown, HTML, PDF).
    """

    def __init__(
        self,
        output_directory: str | None = None,
        enabled: bool | None = None,
        file_format: Literal["md", "md_html", "md_pdf"] | None = None,
    ) -> None:
        """
        Initialize the report file service.

        Args:
            output_directory: Directory to save reports. If None, uses settings or temp directory.
            enabled: Whether file saving is enabled. If None, uses settings.
            file_format: File format to save. If None, uses settings.
        """
        self.enabled = enabled if enabled is not None else settings.save_reports_to_file
        self.file_format = file_format or settings.report_file_format
        self.filename_template = settings.report_filename_template

        # Determine output directory
        if output_directory:
            self.output_directory = Path(output_directory)
        elif settings.report_output_directory:
            self.output_directory = Path(settings.report_output_directory)
        else:
            # Use system temp directory
            self.output_directory = Path(tempfile.gettempdir()) / "deepcritical_reports"

        # Create output directory if it doesn't exist
        if self.enabled:
            try:
                self.output_directory.mkdir(parents=True, exist_ok=True)
                logger.debug(
                    "Report output directory initialized",
                    path=str(self.output_directory),
                    enabled=self.enabled,
                )
            except Exception as e:
                logger.error("Failed to create report output directory", error=str(e), path=str(self.output_directory))
                raise ConfigurationError(f"Failed to create report output directory: {e}") from e

    def _generate_filename(self, query: str | None = None, extension: str = ".md") -> str:
        """
        Generate filename for report using template.

        Args:
            query: Optional query string for hash generation
            extension: File extension (e.g., ".md", ".html")

        Returns:
            Generated filename
        """
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate query hash if query provided
        query_hash = ""
        if query:
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]

        # Generate date
        date = datetime.now().strftime("%Y-%m-%d")

        # Replace template placeholders
        filename = self.filename_template
        filename = filename.replace("{timestamp}", timestamp)
        filename = filename.replace("{query_hash}", query_hash)
        filename = filename.replace("{date}", date)

        # Ensure correct extension
        if not filename.endswith(extension):
            # Remove existing extension if present
            if "." in filename:
                filename = filename.rsplit(".", 1)[0]
            filename += extension

        return filename

    def save_report(
        self,
        report_content: str,
        query: str | None = None,
        filename: str | None = None,
    ) -> str:
        """
        Save a report to a file.

        Args:
            report_content: The report content (markdown string)
            query: Optional query string for filename generation
            filename: Optional custom filename. If None, generates from template.

        Returns:
            Path to saved file

        Raises:
            ConfigurationError: If file saving is disabled or fails
        """
        if not self.enabled:
            logger.debug("File saving disabled, skipping")
            raise ConfigurationError("Report file saving is disabled")

        if not report_content or not report_content.strip():
            raise ValueError("Report content cannot be empty")

        # Generate filename if not provided
        if not filename:
            filename = self._generate_filename(query=query, extension=".md")

        # Ensure filename is safe
        filename = self._sanitize_filename(filename)

        # Build full file path
        file_path = self.output_directory / filename

        try:
            # Write file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info(
                "Report saved to file",
                path=str(file_path),
                size=len(report_content),
                query=query[:50] if query else None,
            )

            return str(file_path)

        except Exception as e:
            logger.error("Failed to save report to file", error=str(e), path=str(file_path))
            raise ConfigurationError(f"Failed to save report to file: {e}") from e

    def save_report_multiple_formats(
        self,
        report_content: str,
        query: str | None = None,
    ) -> dict[str, str]:
        """
        Save a report in multiple formats.

        Args:
            report_content: The report content (markdown string)
            query: Optional query string for filename generation

        Returns:
            Dictionary mapping format to file path (e.g., {"md": "/path/to/report.md"})

        Raises:
            ConfigurationError: If file saving is disabled or fails
        """
        if not self.enabled:
            logger.debug("File saving disabled, skipping")
            raise ConfigurationError("Report file saving is disabled")

        saved_files: dict[str, str] = {}

        # Always save markdown
        md_path = self.save_report(report_content, query=query, filename=None)
        saved_files["md"] = md_path

        # Save additional formats based on file_format setting
        if self.file_format == "md_html":
            # TODO: Implement HTML conversion
            logger.warning("HTML format not yet implemented, saving markdown only")
        elif self.file_format == "md_pdf":
            # TODO: Implement PDF conversion
            logger.warning("PDF format not yet implemented, saving markdown only")

        return saved_files

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to remove unsafe characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in unsafe_chars:
            sanitized = sanitized.replace(char, "_")

        # Limit length
        if len(sanitized) > 200:
            name, ext = sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
            sanitized = name[:190] + ext

        return sanitized

    def cleanup_old_files(self, max_age_days: int = 7) -> int:
        """
        Clean up old report files.

        Args:
            max_age_days: Maximum age in days for files to keep

        Returns:
            Number of files deleted
        """
        if not self.output_directory.exists():
            return 0

        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

        try:
            for file_path in self.output_directory.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning("Failed to delete old file", path=str(file_path), error=str(e))

            if deleted_count > 0:
                logger.info("Cleaned up old report files", deleted=deleted_count, max_age_days=max_age_days)

        except Exception as e:
            logger.error("Failed to cleanup old files", error=str(e))

        return deleted_count


def get_report_file_service() -> ReportFileService:
    """
    Get or create a ReportFileService instance (singleton pattern).

    Returns:
        ReportFileService instance
    """
    # Use lru_cache for singleton pattern
    from functools import lru_cache

    @lru_cache(maxsize=1)
    def _get_service() -> ReportFileService:
        return ReportFileService()

    return _get_service()



