"""Planner agent for creating report plans with sections and background context.

Converts the folder/planner_agent.py implementation to use Pydantic AI.
"""

from datetime import datetime
from typing import Any

import structlog
from pydantic_ai import Agent

from src.agent_factory.judges import get_model
from src.tools.crawl_adapter import crawl_website
from src.tools.web_search_adapter import web_search
from src.utils.exceptions import ConfigurationError, JudgeError
from src.utils.models import ReportPlan, ReportPlanSection

logger = structlog.get_logger()


# System prompt for the planner agent
SYSTEM_PROMPT = f"""
You are a research manager, managing a team of research agents. Today's date is {datetime.now().strftime("%Y-%m-%d")}.
Given a research query, your job is to produce an initial outline of the report (section titles and key questions),
as well as some background context. Each section will be assigned to a different researcher in your team who will then
carry out research on the section.

You will be given:
- An initial research query

Your task is to:
1. Produce 1-2 paragraphs of initial background context (if needed) on the query by running web searches or crawling websites
2. Produce an outline of the report that includes a list of section titles and the key question to be addressed in each section
3. Provide a title for the report that will be used as the main heading

Guidelines:
- Each section should cover a single topic/question that is independent of other sections
- The key question for each section should include both the NAME and DOMAIN NAME / WEBSITE (if available and applicable) if it is related to a company, product or similar
- The background_context should not be more than 2 paragraphs
- The background_context should be very specific to the query and include any information that is relevant for researchers across all sections of the report
- The background_context should be drawn only from web search or crawl results rather than prior knowledge (i.e. it should only be included if you have called tools)
- For example, if the query is about a company, the background context should include some basic information about what the company does
- DO NOT do more than 2 tool calls

Only output JSON. Follow the JSON schema for ReportPlan. Do not output anything else.
"""


class PlannerAgent:
    """
    Planner agent that creates report plans with sections and background context.

    Uses Pydantic AI to generate structured ReportPlan output with optional
    web search and crawl tool usage for background context.
    """

    def __init__(
        self,
        model: Any | None = None,
        web_search_tool: Any | None = None,
        crawl_tool: Any | None = None,
    ) -> None:
        """
        Initialize the planner agent.

        Args:
            model: Optional Pydantic AI model. If None, uses config default.
            web_search_tool: Optional web search tool function. If None, uses default.
            crawl_tool: Optional crawl tool function. If None, uses default.
        """
        self.model = model or get_model()
        self.web_search_tool = web_search_tool or web_search
        self.crawl_tool = crawl_tool or crawl_website
        self.logger = logger

        # Validate tools are callable
        if not callable(self.web_search_tool):
            raise ConfigurationError("web_search_tool must be callable")
        if not callable(self.crawl_tool):
            raise ConfigurationError("crawl_tool must be callable")

        # Initialize Pydantic AI Agent
        self.agent = Agent(
            model=self.model,
            output_type=ReportPlan,
            system_prompt=SYSTEM_PROMPT,
            tools=[self.web_search_tool, self.crawl_tool],
            retries=3,
        )

    async def run(self, query: str) -> ReportPlan:
        """
        Run the planner agent to generate a report plan.

        Args:
            query: The user's research query

        Returns:
            ReportPlan with sections, background context, and report title

        Raises:
            JudgeError: If planning fails after retries
            ConfigurationError: If agent configuration is invalid
        """
        self.logger.info("Starting report planning", query=query[:100])

        user_message = f"QUERY: {query}"

        try:
            # Run the agent
            result = await self.agent.run(user_message)
            report_plan = result.output

            # Validate report plan
            if not report_plan.report_outline:
                self.logger.warning("Report plan has no sections", query=query[:100])
                # Return fallback plan instead of raising error
                return ReportPlan(
                    background_context=report_plan.background_context or "",
                    report_outline=[
                        ReportPlanSection(
                            title="Overview",
                            key_question=query,
                        )
                    ],
                    report_title=report_plan.report_title or f"Research Report: {query[:50]}",
                )

            if not report_plan.report_title:
                self.logger.warning("Report plan has no title", query=query[:100])
                raise JudgeError("Report plan must have a title")

            self.logger.info(
                "Report plan created",
                sections=len(report_plan.report_outline),
                has_background=bool(report_plan.background_context),
            )

            return report_plan

        except Exception as e:
            self.logger.error("Planning failed", error=str(e), query=query[:100])

            # Fallback: return minimal report plan
            if isinstance(e, JudgeError | ConfigurationError):
                raise

            # For other errors, return a minimal plan
            return ReportPlan(
                background_context="",
                report_outline=[
                    ReportPlanSection(
                        title="Research Findings",
                        key_question=query,
                    )
                ],
                report_title=f"Research Report: {query[:50]}",
            )


def create_planner_agent(model: Any | None = None) -> PlannerAgent:
    """
    Factory function to create a planner agent.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured PlannerAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    try:
        # Get model from settings if not provided
        if model is None:
            model = get_model()

        # Create and return planner agent
        return PlannerAgent(model=model)

    except Exception as e:
        logger.error("Failed to create planner agent", error=str(e))
        raise ConfigurationError(f"Failed to create planner agent: {e}") from e
