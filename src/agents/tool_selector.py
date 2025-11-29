"""Tool selector agent for choosing which tools to use for knowledge gaps.

Converts the folder/tool_selector_agent.py implementation to use Pydantic AI.
"""

from datetime import datetime
from typing import Any

import structlog
from pydantic_ai import Agent

from src.agent_factory.judges import get_model
from src.utils.exceptions import ConfigurationError
from src.utils.models import AgentSelectionPlan

logger = structlog.get_logger()


# System prompt for the tool selector agent
SYSTEM_PROMPT = f"""
You are a Tool Selector responsible for determining which specialized agents should address a knowledge gap in a research project.
Today's date is {datetime.now().strftime("%Y-%m-%d")}.

You will be given:
1. The original user query
2. A knowledge gap identified in the research
3. A full history of the tasks, actions, findings and thoughts you've made up until this point in the research process

Your task is to decide:
1. Which specialized agents are best suited to address the gap
2. What specific queries should be given to the agents (keep this short - 3-6 words)

Available specialized agents:
- WebSearchAgent: General web search for broad topics (can be called multiple times with different queries)
- SiteCrawlerAgent: Crawl the pages of a specific website to retrieve information about it - use this if you want to find out something about a particular company, entity or product
- RAGAgent: Semantic search within previously collected evidence - use when you need to find information from evidence already gathered in this research session. Best for finding connections, summarizing collected evidence, or retrieving specific details from earlier findings.

Guidelines:
- Aim to call at most 3 agents at a time in your final output
- You can list the WebSearchAgent multiple times with different queries if needed to cover the full scope of the knowledge gap
- Be specific and concise (3-6 words) with the agent queries - they should target exactly what information is needed
- If you know the website or domain name of an entity being researched, always include it in the query
- Use RAGAgent when: (1) You need to search within evidence already collected, (2) You want to find connections between different findings, (3) You need to retrieve specific details from earlier research iterations
- Use WebSearchAgent or SiteCrawlerAgent when: (1) You need fresh information from the web, (2) You're starting a new research direction, (3) You need information not yet in the collected evidence
- If a gap doesn't clearly match any agent's capability, default to the WebSearchAgent
- Use the history of actions / tool calls as a guide - try not to repeat yourself if an approach didn't work previously

Only output JSON. Follow the JSON schema for AgentSelectionPlan. Do not output anything else.
"""


class ToolSelectorAgent:
    """
    Agent that selects appropriate tools to address knowledge gaps.

    Uses Pydantic AI to generate structured AgentSelectionPlan with
    specific tasks for web search and crawl agents.
    """

    def __init__(self, model: Any | None = None) -> None:
        """
        Initialize the tool selector agent.

        Args:
            model: Optional Pydantic AI model. If None, uses config default.
        """
        self.model = model or get_model()
        self.logger = logger

        # Initialize Pydantic AI Agent
        self.agent = Agent(
            model=self.model,
            output_type=AgentSelectionPlan,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

    async def select_tools(
        self,
        gap: str,
        query: str,
        background_context: str = "",
        conversation_history: str = "",
    ) -> AgentSelectionPlan:
        """
        Select tools to address a knowledge gap.

        Args:
            gap: The knowledge gap to address
            query: The original research query
            background_context: Optional background context
            conversation_history: History of actions, findings, and thoughts

        Returns:
            AgentSelectionPlan with tasks for selected agents

        Raises:
            ConfigurationError: If selection fails
        """
        self.logger.info("Selecting tools for gap", gap=gap[:100], query=query[:100])

        background = f"BACKGROUND CONTEXT:\n{background_context}" if background_context else ""

        user_message = f"""
ORIGINAL QUERY:
{query}

KNOWLEDGE GAP TO ADDRESS:
{gap}

{background}

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
{conversation_history or "No previous actions, findings or thoughts available."}
"""

        try:
            # Run the agent
            result = await self.agent.run(user_message)
            selection_plan = result.output

            self.logger.info(
                "Tool selection complete",
                tasks_count=len(selection_plan.tasks),
                agents=[task.agent for task in selection_plan.tasks],
            )

            return selection_plan

        except Exception as e:
            self.logger.error("Tool selection failed", error=str(e))
            # Return fallback: use web search
            from src.utils.models import AgentTask

            return AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap=gap,
                        agent="WebSearchAgent",
                        query=gap[:50],  # Use gap as query
                        entity_website=None,
                    )
                ]
            )


def create_tool_selector_agent(model: Any | None = None) -> ToolSelectorAgent:
    """
    Factory function to create a tool selector agent.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured ToolSelectorAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    try:
        if model is None:
            model = get_model()

        return ToolSelectorAgent(model=model)

    except Exception as e:
        logger.error("Failed to create tool selector agent", error=str(e))
        raise ConfigurationError(f"Failed to create tool selector agent: {e}") from e
