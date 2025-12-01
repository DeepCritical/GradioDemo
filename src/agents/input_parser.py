"""Input parser agent for analyzing and improving user queries.

Determines research mode (iterative vs deep) and extracts key information
from user queries to improve research quality.
"""

from typing import TYPE_CHECKING, Any, Literal

import structlog
from pydantic_ai import Agent

from src.agent_factory.judges import get_model
from src.utils.exceptions import ConfigurationError, JudgeError
from src.utils.models import ParsedQuery

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

# System prompt for the input parser agent
SYSTEM_PROMPT = """
You are an expert research query analyzer for a generalist deep research agent. Your job is to analyze user queries and determine:
1. Whether the query requires iterative research (single focused question) or deep research (multiple sections/topics)
2. Whether the query requires medical/biomedical knowledge sources (PubMed, ClinicalTrials.gov) or general knowledge sources (web search)
3. Improve and refine the query for better research results
4. Extract key entities (drugs, diseases, companies, technologies, concepts, etc.)
5. Extract specific research questions

Guidelines for determining research mode:
- **Iterative mode**: Single focused question, straightforward research goal, can be answered with a focused search loop
  Examples: "What is the mechanism of metformin?", "How does quantum computing work?", "What are the latest AI models?"
  
- **Deep mode**: Complex query requiring multiple sections, comprehensive report, multiple related topics
  Examples: "Write a comprehensive report on diabetes treatment", "Analyze the market for quantum computing", "Review the state of AI in healthcare"
  Indicators: words like "comprehensive", "report", "sections", "analyze", "market analysis", "overview"

Guidelines for determining if medical knowledge is needed:
- **Medical knowledge needed**: Queries about diseases, treatments, drugs, clinical trials, medical conditions, biomedical mechanisms, health outcomes, etc.
  Examples: "Alzheimer's treatment", "metformin mechanism", "cancer clinical trials", "diabetes research"
  
- **General knowledge sufficient**: Queries about technology, business, science (non-medical), history, current events, etc.
  Examples: "quantum computing", "AI models", "market analysis", "historical events"

Your output must be valid JSON matching the ParsedQuery schema. Always provide:
- original_query: The exact input query
- improved_query: A refined, clearer version of the query
- research_mode: Either "iterative" or "deep"
- key_entities: List of important entities (drugs, diseases, companies, technologies, etc.)
- research_questions: List of specific questions to answer

Only output JSON. Do not output anything else.
"""


class InputParserAgent:
    """
    Input parser agent that analyzes queries and determines research mode.

    Uses Pydantic AI to generate structured ParsedQuery output with research
    mode detection, query improvement, and entity extraction.
    """

    def __init__(self, model: Any | None = None) -> None:
        """
        Initialize the input parser agent.

        Args:
            model: Optional Pydantic AI model. If None, uses config default.
        """
        self.model = model or get_model()
        self.logger = logger

        # Initialize Pydantic AI Agent
        self.agent = Agent(
            model=self.model,
            output_type=ParsedQuery,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

    async def parse(self, query: str) -> ParsedQuery:
        """
        Parse and analyze a user query.

        Args:
            query: The user's research query

        Returns:
            ParsedQuery with research mode, improved query, entities, and questions

        Raises:
            JudgeError: If parsing fails after retries
            ConfigurationError: If agent configuration is invalid
        """
        self.logger.info("Parsing user query", query=query[:100])

        user_message = f"QUERY: {query}"

        try:
            # Run the agent
            result = await self.agent.run(user_message)
            parsed_query = result.output

            # Validate parsed query
            if not parsed_query.original_query:
                self.logger.warning("Parsed query missing original_query", query=query[:100])
                raise JudgeError("Parsed query must have original_query")

            if not parsed_query.improved_query:
                self.logger.warning("Parsed query missing improved_query", query=query[:100])
                # Use original as fallback
                parsed_query = ParsedQuery(
                    original_query=parsed_query.original_query,
                    improved_query=parsed_query.original_query,
                    research_mode=parsed_query.research_mode,
                    key_entities=parsed_query.key_entities,
                    research_questions=parsed_query.research_questions,
                )

            self.logger.info(
                "Query parsed successfully",
                mode=parsed_query.research_mode,
                entities=len(parsed_query.key_entities),
                questions=len(parsed_query.research_questions),
            )

            return parsed_query

        except Exception as e:
            self.logger.error("Query parsing failed", error=str(e), query=query[:100])

            # Fallback: return basic parsed query with heuristic mode detection
            if isinstance(e, JudgeError | ConfigurationError):
                raise

            # Heuristic fallback
            query_lower = query.lower()
            research_mode: Literal["iterative", "deep"] = "iterative"
            if any(
                keyword in query_lower
                for keyword in [
                    "comprehensive",
                    "report",
                    "sections",
                    "analyze",
                    "analysis",
                    "overview",
                    "market",
                ]
            ):
                research_mode = "deep"

            return ParsedQuery(
                original_query=query,
                improved_query=query,
                research_mode=research_mode,
                key_entities=[],
                research_questions=[],
            )


def create_input_parser_agent(
    model: Any | None = None, oauth_token: str | None = None
) -> InputParserAgent:
    """
    Factory function to create an input parser agent.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.
        oauth_token: Optional OAuth token from HuggingFace login (takes priority over env vars)

    Returns:
        Configured InputParserAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    try:
        # Get model from settings if not provided
        if model is None:
            model = get_model(oauth_token=oauth_token)

        # Create and return input parser agent
        return InputParserAgent(model=model)

    except Exception as e:
        logger.error("Failed to create input parser agent", error=str(e))
        raise ConfigurationError(f"Failed to create input parser agent: {e}") from e
