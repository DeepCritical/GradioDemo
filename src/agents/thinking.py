"""Thinking agent for generating observations and reflections.

Converts the folder/thinking_agent.py implementation to use Pydantic AI.
"""

from datetime import datetime
from typing import Any

import structlog
from pydantic_ai import Agent

from src.agent_factory.judges import get_model
from src.utils.exceptions import ConfigurationError

logger = structlog.get_logger()


# System prompt for the thinking agent
SYSTEM_PROMPT = f"""
You are a research expert who is managing a research process in iterations. Today's date is {datetime.now().strftime("%Y-%m-%d")}.

You are given:
1. The original research query along with some supporting background context
2. A history of the tasks, actions, findings and thoughts you've made up until this point in the research process (on iteration 1 you will be at the start of the research process, so this will be empty)

Your objective is to reflect on the research process so far and share your latest thoughts.

Specifically, your thoughts should include reflections on questions such as:
- What have you learned from the last iteration?
- What new areas would you like to explore next, or existing topics you'd like to go deeper into?
- Were you able to retrieve the information you were looking for in the last iteration?
- If not, should we change our approach or move to the next topic?
- Is there any info that is contradictory or conflicting?

Guidelines:
- Share your stream of consciousness on the above questions as raw text
- Keep your response concise and informal
- Focus most of your thoughts on the most recent iteration and how that influences this next iteration
- Our aim is to do very deep and thorough research - bear this in mind when reflecting on the research process
- DO NOT produce a draft of the final report. This is not your job.
- If this is the first iteration (i.e. no data from prior iterations), provide thoughts on what info we need to gather in the first iteration to get started
"""


class ThinkingAgent:
    """
    Agent that generates observations and reflections on the research process.

    Uses Pydantic AI to generate unstructured text observations about
    the current state of research and next steps.
    """

    def __init__(self, model: Any | None = None) -> None:
        """
        Initialize the thinking agent.

        Args:
            model: Optional Pydantic AI model. If None, uses config default.
        """
        self.model = model or get_model()
        self.logger = logger

        # Initialize Pydantic AI Agent (no structured output - returns text)
        self.agent = Agent(
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

    async def generate_observations(
        self,
        query: str,
        background_context: str = "",
        conversation_history: str = "",
        iteration: int = 1,
    ) -> str:
        """
        Generate observations about the research process.

        Args:
            query: The original research query
            background_context: Optional background context
            conversation_history: History of actions, findings, and thoughts
            iteration: Current iteration number

        Returns:
            String containing observations and reflections

        Raises:
            ConfigurationError: If generation fails
        """
        self.logger.info(
            "Generating observations",
            query=query[:100],
            iteration=iteration,
        )

        background = f"BACKGROUND CONTEXT:\n{background_context}" if background_context else ""

        user_message = f"""
You are starting iteration {iteration} of your research process.

ORIGINAL QUERY:
{query}

{background}

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
{conversation_history or "No previous actions, findings or thoughts available."}
"""

        try:
            # Run the agent
            result = await self.agent.run(user_message)
            observations = result.output

            self.logger.info("Observations generated", length=len(observations))

            return observations

        except Exception as e:
            self.logger.error("Observation generation failed", error=str(e))
            # Return fallback observations
            return f"Starting iteration {iteration}. Need to gather information about: {query}"


def create_thinking_agent(model: Any | None = None) -> ThinkingAgent:
    """
    Factory function to create a thinking agent.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured ThinkingAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    try:
        if model is None:
            model = get_model()

        return ThinkingAgent(model=model)

    except Exception as e:
        logger.error("Failed to create thinking agent", error=str(e))
        raise ConfigurationError(f"Failed to create thinking agent: {e}") from e
