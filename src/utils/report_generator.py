"""Utility functions for generating reports from evidence when LLM fails."""

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from src.utils.models import Evidence

logger = structlog.get_logger()


def generate_report_from_evidence(
    query: str,
    evidence: list["Evidence"] | None = None,
    findings: str | None = None,
) -> str:
    """
    Generate a structured markdown report from evidence or findings when LLM fails.

    This function creates a proper report structure even without LLM assistance,
    formatting the collected evidence into a readable, well-structured document.

    Args:
        query: The original research query
        evidence: List of Evidence objects (preferred if available)
        findings: Pre-formatted findings string (fallback if evidence not available)

    Returns:
        Markdown formatted report string
    """
    report_parts: list[str] = []

    # Title
    report_parts.append(f"# Research Report: {query}\n")

    # Introduction
    report_parts.append("## Introduction\n")
    report_parts.append(
        f"This report addresses the following research query: **{query}**\n"
    )
    report_parts.append(
        "*Note: This report was generated from collected evidence. "
        "LLM-based synthesis was unavailable due to API limitations.*\n\n"
    )

    # Evidence Summary
    if evidence and len(evidence) > 0:
        report_parts.append("## Evidence Summary\n")
        report_parts.append(
            f"**Total Sources Found:** {len(evidence)}\n\n"
        )

        # Group evidence by source
        by_source: dict[str, list["Evidence"]] = {}
        for ev in evidence:
            source = ev.citation.source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(ev)

        # Organize by source
        for source in sorted(by_source.keys()):
            source_evidence = by_source[source]
            report_parts.append(f"### {source.upper()} Sources ({len(source_evidence)})\n\n")

            for i, ev in enumerate(source_evidence, 1):
                # Format citation
                authors = ", ".join(ev.citation.authors[:3])
                if len(ev.citation.authors) > 3:
                    authors += " et al."

                report_parts.append(f"#### {i}. {ev.citation.title}\n")
                if authors:
                    report_parts.append(f"**Authors:** {authors}  \n")
                report_parts.append(f"**Date:** {ev.citation.date}  \n")
                report_parts.append(f"**Source:** {ev.citation.source.upper()}  \n")
                report_parts.append(f"**URL:** {ev.citation.url}  \n\n")

                # Content (truncated if too long)
                content = ev.content
                if len(content) > 500:
                    content = content[:500] + "... [truncated]"
                report_parts.append(f"{content}\n\n")

        # Key Findings Section
        report_parts.append("## Key Findings\n\n")
        report_parts.append(
            "Based on the evidence collected, the following key points were identified:\n\n"
        )

        # Extract key points from evidence (first sentence or summary)
        key_points: list[str] = []
        for ev in evidence[:10]:  # Limit to top 10
            # Try to extract first meaningful sentence
            content = ev.content.strip()
            if content:
                # Find first sentence
                first_period = content.find(".")
                if first_period > 0 and first_period < 200:
                    key_point = content[: first_period + 1].strip()
                else:
                    # Fallback: first 150 chars
                    key_point = content[:150].strip()
                    if len(content) > 150:
                        key_point += "..."
                key_points.append(f"- {key_point} [[{len(key_points) + 1}]](#references)")

        if key_points:
            report_parts.append("\n".join(key_points))
            report_parts.append("\n\n")
        else:
            report_parts.append(
                "*No specific key findings could be extracted from the evidence.*\n\n"
            )

    elif findings:
        # Fallback: use findings string if evidence not available
        report_parts.append("## Research Findings\n\n")
        # Truncate if too long
        if len(findings) > 10000:
            findings = findings[:10000] + "\n\n[Content truncated due to length]"
        report_parts.append(f"{findings}\n\n")
    else:
        report_parts.append("## Research Findings\n\n")
        report_parts.append(
            "*No evidence or findings were collected during the research process.*\n\n"
        )

    # References Section
    if evidence and len(evidence) > 0:
        report_parts.append("## References\n\n")
        for i, ev in enumerate(evidence, 1):
            authors = ", ".join(ev.citation.authors[:3])
            if len(ev.citation.authors) > 3:
                authors += " et al."
            elif not authors:
                authors = "Unknown"

            report_parts.append(
                f"[{i}] {authors} ({ev.citation.date}). "
                f"*{ev.citation.title}*. "
                f"{ev.citation.source.upper()}. "
                f"Available at: {ev.citation.url}\n\n"
            )

    # Conclusion
    report_parts.append("## Conclusion\n\n")
    if evidence and len(evidence) > 0:
        report_parts.append(
            f"This report synthesized information from {len(evidence)} sources "
            f"to address the research query: **{query}**\n\n"
        )
        report_parts.append(
            "*Note: Due to API limitations, this report was generated directly from "
            "collected evidence without LLM-based synthesis. For a more comprehensive "
            "analysis, please retry when API access is available.*\n"
        )
    else:
        report_parts.append(
            "This report could not be fully generated due to limited evidence collection "
            "and API access issues.\n\n"
        )
        report_parts.append(
            "*Please retry your query when API access is available for a more "
            "comprehensive research report.*\n"
        )

    return "".join(report_parts)








