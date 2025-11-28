"""Proofreader agent for finalizing report drafts.

Converts the folder/proofreader_agent.py implementation to use Pydantic AI.
"""

from datetime import datetime
from typing import Any

import structlog
from pydantic_ai import Agent

from src.agent_factory.judges import get_model
from src.utils.exceptions import ConfigurationError
from src.utils.models import ReportDraft

logger = structlog.get_logger()


# System prompt for the proofreader agent
SYSTEM_PROMPT = f"""
You are a research expert who proofreads and edits research reports.
Today's date is {datetime.now().strftime("%Y-%m-%d")}.

You are given:
1. The original query topic for the report
2. A first draft of the report in ReportDraft format containing each section in sequence

Your task is to:
1. **Combine sections:** Concatenate the sections into a single string
2. **Add section titles:** Add the section titles to the beginning of each section in markdown format, as well as a main title for the report
3. **De-duplicate:** Remove duplicate content across sections to avoid repetition
4. **Remove irrelevant sections:** If any sections or sub-sections are completely irrelevant to the query, remove them
5. **Refine wording:** Edit the wording of the report to be polished, concise and punchy, but **without eliminating any detail** or large chunks of text
6. **Add a summary:** Add a short report summary / outline to the beginning of the report to provide an overview of the sections and what is discussed
7. **Preserve sources:** Preserve all sources / references - move the long list of references to the end of the report
8. **Update reference numbers:** Continue to include reference numbers in square brackets  ([1], [2], [3], etc.) in the main body of the report, but update the numbering to match the new order of references at the end of the report
9. **Output final report:** Output the final report in markdown format (do not wrap it in a code block)

Guidelines:
- Do not add any new facts or data to the report
- Do not remove any content from the report unless it is very clearly wrong, contradictory or irrelevant
- Remove or reformat any redundant or excessive headings, and ensure that the final nesting of heading levels is correct
- Ensure that the final report flows well and has a logical structure
- Include all sources and references that are present in the final report
"""


class ProofreaderAgent:
    """
    Agent that proofreads and finalizes report drafts.

    Uses Pydantic AI to generate polished markdown reports from draft sections.
    """

    def __init__(self, model: Any | None = None) -> None:
        """
        Initialize the proofreader agent.

        Args:
            model: Optional Pydantic AI model. If None, uses config default.
        """
        self.model = model or get_model()
        self.logger = logger

        # Initialize Pydantic AI Agent (no structured output - returns markdown text)
        self.agent = Agent(
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

    async def proofread(
        self,
        query: str,
        report_draft: ReportDraft,
    ) -> str:
        """
        Proofread and finalize a report draft.

        Args:
            query: The original research query
            report_draft: ReportDraft with all sections

        Returns:
            Final polished markdown report string

        Raises:
            ConfigurationError: If proofreading fails
        """
        # Input validation
        if not query or not query.strip():
            self.logger.warning("Empty query provided, using default")
            query = "Research query"

        if not report_draft or not report_draft.sections:
            self.logger.warning("Empty report draft provided, returning minimal report")
            return f"# Research Report\n\n## Query\n{query}\n\n*No sections available.*"

        # Validate section structure
        valid_sections = []
        for section in report_draft.sections:
            if section.section_title and section.section_title.strip():
                valid_sections.append(section)
            else:
                self.logger.warning("Skipping section with empty title")

        if not valid_sections:
            self.logger.warning("No valid sections in draft, returning minimal report")
            return f"# Research Report\n\n## Query\n{query}\n\n*No valid sections available.*"

        self.logger.info(
            "Proofreading report",
            query=query[:100],
            sections_count=len(valid_sections),
        )

        # Create validated draft
        validated_draft = ReportDraft(sections=valid_sections)

        user_message = f"""
QUERY:
{query}

REPORT DRAFT:
{validated_draft.model_dump_json()}
"""

        # Retry logic for transient failures
        max_retries = 3
        last_exception: Exception | None = None

        for attempt in range(max_retries):
            try:
                # Run the agent
                result = await self.agent.run(user_message)
                final_report = result.output

                # Validate output
                if not final_report or not final_report.strip():
                    self.logger.warning("Empty report generated, using fallback")
                    raise ValueError("Empty report generated")

                self.logger.info("Report proofread", length=len(final_report), attempt=attempt + 1)

                return final_report

            except (TimeoutError, ConnectionError) as e:
                # Transient errors - retry
                last_exception = e
                if attempt < max_retries - 1:
                    self.logger.warning(
                        "Transient error, retrying",
                        error=str(e),
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    continue
                else:
                    self.logger.error("Max retries exceeded for transient error", error=str(e))
                    break

            except Exception as e:
                # Non-transient errors - don't retry
                last_exception = e
                self.logger.error(
                    "Proofreading failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                break

        # Return fallback: combine sections manually
        self.logger.error(
            "Proofreading failed after all attempts",
            error=str(last_exception) if last_exception else "Unknown error",
        )
        sections = [
            f"## {section.section_title}\n\n{section.section_content or 'Content unavailable.'}"
            for section in valid_sections
        ]
        return f"# Research Report\n\n## Query\n{query}\n\n" + "\n\n".join(sections)


def create_proofreader_agent(model: Any | None = None) -> ProofreaderAgent:
    """
    Factory function to create a proofreader agent.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured ProofreaderAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    try:
        if model is None:
            model = get_model()

        return ProofreaderAgent(model=model)

    except Exception as e:
        logger.error("Failed to create proofreader agent", error=str(e))
        raise ConfigurationError(f"Failed to create proofreader agent: {e}") from e
