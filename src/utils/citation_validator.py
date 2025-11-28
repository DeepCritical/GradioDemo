"""Citation validation to prevent LLM hallucination.

CRITICAL: Medical research requires accurate citations.
This module validates that all references exist in collected evidence.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.models import Evidence, ResearchReport

logger = logging.getLogger(__name__)

# Max characters to display for URLs in log messages
_MAX_URL_DISPLAY_LENGTH = 80


def validate_references(report: "ResearchReport", evidence: list["Evidence"]) -> "ResearchReport":
    """Ensure all references actually exist in collected evidence.

    CRITICAL: Prevents LLM hallucination of citations.

    Note:
        This function MUTATES report.references in-place and returns the same
        report object. This is intentional for efficiency.

    Args:
        report: The generated research report (will be mutated)
        evidence: All evidence collected during research

    Returns:
        The same report object with references updated in-place
    """
    # Build set of valid URLs from evidence
    valid_urls = {e.citation.url for e in evidence}
    # Also check titles (case-insensitive, exact match) as fallback
    valid_titles = {e.citation.title.lower() for e in evidence}

    validated_refs = []
    removed_count = 0

    for ref in report.references:
        ref_url = ref.get("url", "")
        ref_title = ref.get("title", "").lower()

        # Check if URL matches collected evidence
        if ref_url in valid_urls:
            validated_refs.append(ref)
        # Fallback: exact title match (case-insensitive)
        elif ref_title and ref_title in valid_titles:
            validated_refs.append(ref)
        else:
            removed_count += 1
            # Truncate URL for display
            if len(ref_url) > _MAX_URL_DISPLAY_LENGTH:
                url_display = ref_url[:_MAX_URL_DISPLAY_LENGTH] + "..."
            else:
                url_display = ref_url
            logger.warning(
                f"Removed hallucinated reference: '{ref.get('title', 'Unknown')}' "
                f"(URL: {url_display})"
            )

    if removed_count > 0:
        logger.info(
            f"Citation validation removed {removed_count} hallucinated references. "
            f"{len(validated_refs)} valid references remain."
        )

    # Update report with validated references
    report.references = validated_refs
    return report


def build_reference_from_evidence(evidence: "Evidence") -> dict[str, str]:
    """Build a properly formatted reference from evidence.

    Use this to ensure references match the original evidence exactly.
    """
    return {
        "title": evidence.citation.title,
        "authors": ", ".join(evidence.citation.authors or ["Unknown"]),
        "source": evidence.citation.source,
        "date": evidence.citation.date or "n.d.",
        "url": evidence.citation.url,
    }


def validate_markdown_citations(
    markdown_report: str, evidence: list["Evidence"]
) -> tuple[str, int]:
    """Validate citations in a markdown report against collected evidence.

    This function validates citations in markdown format (e.g., [1], [2]) by:
    1. Extracting URLs from the references section
    2. Matching them against Evidence objects
    3. Removing invalid citations from the report

    Note:
        This is a basic validation. For full validation, use ResearchReport
        objects with validate_references().

    Args:
        markdown_report: The markdown report string with citations
        evidence: List of Evidence objects collected during research

    Returns:
        Tuple of (validated_markdown, removed_count)
    """
    import re

    # Build set of valid URLs from evidence
    valid_urls = {e.citation.url for e in evidence}
    valid_urls_lower = {url.lower() for url in valid_urls}

    # Extract references section (everything after "## References" or "References:")
    ref_section_pattern = r"(?i)(?:##\s*)?References:?\s*\n(.*?)(?=\n##|\Z)"
    ref_match = re.search(ref_section_pattern, markdown_report, re.DOTALL)

    if not ref_match:
        # No references section found, return as-is
        return markdown_report, 0

    ref_section = ref_match.group(1)
    ref_lines = ref_section.strip().split("\n")

    # Parse references: [1] https://example.com or [1] https://example.com Title
    valid_refs = []
    removed_count = 0

    for ref_line in ref_lines:
        stripped_line = ref_line.strip()
        if not stripped_line:
            continue

        # Extract URL from reference line
        # Pattern: [N] URL or [N] URL Title
        url_match = re.search(r"https?://[^\s\)]+", stripped_line)
        if url_match:
            url = url_match.group(0).rstrip(".,;")
            url_lower = url.lower()

            # Check if URL is valid
            if url in valid_urls or url_lower in valid_urls_lower:
                valid_refs.append(stripped_line)
            else:
                removed_count += 1
                logger.warning(
                    f"Removed invalid citation from markdown: {url[:80]}"
                    + ("..." if len(url) > 80 else "")
                )
        else:
            # No URL found, keep the line (might be formatted differently)
            valid_refs.append(stripped_line)

    # Rebuild references section
    if valid_refs:
        new_ref_section = "\n".join(valid_refs)
        # Replace the old references section
        validated_markdown = (
            markdown_report[: ref_match.start(1)]
            + new_ref_section
            + markdown_report[ref_match.end(1) :]
        )
    else:
        # No valid references, remove the entire section
        validated_markdown = (
            markdown_report[: ref_match.start()] + markdown_report[ref_match.end() :]
        )

    if removed_count > 0:
        logger.info(
            f"Citation validation removed {removed_count} invalid citations from markdown report. "
            f"{len(valid_refs)} valid citations remain."
        )

    return validated_markdown, removed_count
