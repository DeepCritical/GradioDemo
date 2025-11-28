"""Knowledge gap agent for evaluating research completeness.

Converts the folder/knowledge_gap_agent.py implementation to use Pydantic AI.
"""

from datetime import datetime
from typing import Any

import structlog
from pydantic_ai import Agent

from src.agent_factory.judges import get_model
from src.utils.exceptions import ConfigurationError
from src.utils.models import KnowledgeGapOutput

logger = structlog.get_logger()


# System prompt for the knowledge gap agent
SYSTEM_PROMPT = f"""
You are a Research State Evaluator. Today's date is {datetime.now().strftime("%Y-%m-%d")}.
Your job is to critically analyze the current state of a research report, 
identify what knowledge gaps still exist and determine the best next step to take.

You will be given:
1. The original user query and any relevant background context to the query
2. A full history of the tasks, actions, findings and thoughts you've made up until this point in the research process

Your task is to:
1. Carefully review the findings and thoughts, particularly from the latest iteration, and assess their completeness in answering the original query
2. Determine if the findings are sufficiently complete to end the research loop
3. If not, identify up to 3 knowledge gaps that need to be addressed in sequence in order to continue with research - these should be relevant to the original query

Be specific in the gaps you identify and include relevant information as this will be passed onto another agent to process without additional context.

Only output JSON. Follow the JSON schema for KnowledgeGapOutput. Do not output anything else.
"""


class KnowledgeGapAgent:
    """
    Agent that evaluates research state and identifies knowledge gaps.

    Uses Pydantic AI to generate structured KnowledgeGapOutput indicating
    whether research is complete and what gaps remain.
    """

    def __init__(self, model: Any | None = None) -> None:
        """
        Initialize the knowledge gap agent.

        Args:
            model: Optional Pydantic AI model. If None, uses config default.
        """
        self.model = model or get_model()
        self.logger = logger

        # Initialize Pydantic AI Agent
        self.agent = Agent(
            model=self.model,
            output_type=KnowledgeGapOutput,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

    async def evaluate(
        self,
        query: str,
        background_context: str = "",
        conversation_history: str = "",
        iteration: int = 0,
        time_elapsed_minutes: float = 0.0,
        max_time_minutes: int = 10,
    ) -> KnowledgeGapOutput:
        """
        Evaluate research state and identify knowledge gaps.

        Args:
            query: The original research query
            background_context: Optional background context
            conversation_history: History of actions, findings, and thoughts
            iteration: Current iteration number
            time_elapsed_minutes: Time elapsed so far
            max_time_minutes: Maximum time allowed

        Returns:
            KnowledgeGapOutput with research completeness and outstanding gaps

        Raises:
            JudgeError: If evaluation fails after retries
        """
        self.logger.info(
            "Evaluating knowledge gaps",
            query=query[:100],
            iteration=iteration,
        )

        background = f"BACKGROUND CONTEXT:\n{background_context}" if background_context else ""

        user_message = f"""
Current Iteration Number: {iteration}
Time Elapsed: {time_elapsed_minutes:.2f} minutes of maximum {max_time_minutes} minutes

ORIGINAL QUERY:
{query}

{background}

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
{conversation_history or "No previous actions, findings or thoughts available."}
"""

        try:
            # Run the agent
            result = await self.agent.run(user_message)
            evaluation = result.output

            self.logger.info(
                "Knowledge gap evaluation complete",
                research_complete=evaluation.research_complete,
                gaps_count=len(evaluation.outstanding_gaps),
            )

            return evaluation

        except Exception as e:
            self.logger.error("Knowledge gap evaluation failed", error=str(e))
            # Return fallback: research not complete, suggest continuing
            return KnowledgeGapOutput(
                research_complete=False,
                outstanding_gaps=[f"Continue research on: {query}"],
            )


def create_knowledge_gap_agent(model: Any | None = None) -> KnowledgeGapAgent:
    """
    Factory function to create a knowledge gap agent.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured KnowledgeGapAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    try:
        if model is None:
            model = get_model()

        return KnowledgeGapAgent(model=model)

    except Exception as e:
        logger.error("Failed to create knowledge gap agent", error=str(e))
        raise ConfigurationError(f"Failed to create knowledge gap agent: {e}") from e
