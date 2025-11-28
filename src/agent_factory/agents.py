"""Agent factory functions for creating research agents.

Provides factory functions for creating all Pydantic AI agents used in
the research workflows, following the pattern from judges.py.
"""

from typing import TYPE_CHECKING, Any

import structlog

from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

if TYPE_CHECKING:
    from src.agent_factory.graph_builder import GraphBuilder
    from src.agents.input_parser import InputParserAgent
    from src.agents.knowledge_gap import KnowledgeGapAgent
    from src.agents.long_writer import LongWriterAgent
    from src.agents.proofreader import ProofreaderAgent
    from src.agents.thinking import ThinkingAgent
    from src.agents.tool_selector import ToolSelectorAgent
    from src.agents.writer import WriterAgent
    from src.orchestrator.graph_orchestrator import GraphOrchestrator
    from src.orchestrator.planner_agent import PlannerAgent
    from src.orchestrator.research_flow import DeepResearchFlow, IterativeResearchFlow

logger = structlog.get_logger()


def create_input_parser_agent(model: Any | None = None) -> "InputParserAgent":
    """
    Create input parser agent for query analysis and research mode detection.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured InputParserAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    from src.agents.input_parser import create_input_parser_agent as _create_agent

    try:
        logger.debug("Creating input parser agent")
        return _create_agent(model=model)
    except Exception as e:
        logger.error("Failed to create input parser agent", error=str(e))
        raise ConfigurationError(f"Failed to create input parser agent: {e}") from e


def create_planner_agent(model: Any | None = None) -> "PlannerAgent":
    """
    Create planner agent with web search and crawl tools.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured PlannerAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    # Lazy import to avoid circular dependencies
    from src.orchestrator.planner_agent import create_planner_agent as _create_planner_agent

    try:
        logger.debug("Creating planner agent")
        return _create_planner_agent(model=model)
    except Exception as e:
        logger.error("Failed to create planner agent", error=str(e))
        raise ConfigurationError(f"Failed to create planner agent: {e}") from e


def create_knowledge_gap_agent(model: Any | None = None) -> "KnowledgeGapAgent":
    """
    Create knowledge gap agent for evaluating research completeness.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured KnowledgeGapAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    from src.agents.knowledge_gap import create_knowledge_gap_agent as _create_agent

    try:
        logger.debug("Creating knowledge gap agent")
        return _create_agent(model=model)
    except Exception as e:
        logger.error("Failed to create knowledge gap agent", error=str(e))
        raise ConfigurationError(f"Failed to create knowledge gap agent: {e}") from e


def create_tool_selector_agent(model: Any | None = None) -> "ToolSelectorAgent":
    """
    Create tool selector agent for choosing tools to address gaps.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured ToolSelectorAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    from src.agents.tool_selector import create_tool_selector_agent as _create_agent

    try:
        logger.debug("Creating tool selector agent")
        return _create_agent(model=model)
    except Exception as e:
        logger.error("Failed to create tool selector agent", error=str(e))
        raise ConfigurationError(f"Failed to create tool selector agent: {e}") from e


def create_thinking_agent(model: Any | None = None) -> "ThinkingAgent":
    """
    Create thinking agent for generating observations.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured ThinkingAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    from src.agents.thinking import create_thinking_agent as _create_agent

    try:
        logger.debug("Creating thinking agent")
        return _create_agent(model=model)
    except Exception as e:
        logger.error("Failed to create thinking agent", error=str(e))
        raise ConfigurationError(f"Failed to create thinking agent: {e}") from e


def create_writer_agent(model: Any | None = None) -> "WriterAgent":
    """
    Create writer agent for generating final reports.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured WriterAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    from src.agents.writer import create_writer_agent as _create_agent

    try:
        logger.debug("Creating writer agent")
        return _create_agent(model=model)
    except Exception as e:
        logger.error("Failed to create writer agent", error=str(e))
        raise ConfigurationError(f"Failed to create writer agent: {e}") from e


def create_long_writer_agent(model: Any | None = None) -> "LongWriterAgent":
    """
    Create long writer agent for iteratively writing report sections.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured LongWriterAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    from src.agents.long_writer import create_long_writer_agent as _create_agent

    try:
        logger.debug("Creating long writer agent")
        return _create_agent(model=model)
    except Exception as e:
        logger.error("Failed to create long writer agent", error=str(e))
        raise ConfigurationError(f"Failed to create long writer agent: {e}") from e


def create_proofreader_agent(model: Any | None = None) -> "ProofreaderAgent":
    """
    Create proofreader agent for finalizing report drafts.

    Args:
        model: Optional Pydantic AI model. If None, uses settings default.

    Returns:
        Configured ProofreaderAgent instance

    Raises:
        ConfigurationError: If required API keys are missing
    """
    from src.agents.proofreader import create_proofreader_agent as _create_agent

    try:
        logger.debug("Creating proofreader agent")
        return _create_agent(model=model)
    except Exception as e:
        logger.error("Failed to create proofreader agent", error=str(e))
        raise ConfigurationError(f"Failed to create proofreader agent: {e}") from e


def create_iterative_flow(
    max_iterations: int = 5,
    max_time_minutes: int = 10,
    verbose: bool = True,
    use_graph: bool | None = None,
) -> "IterativeResearchFlow":
    """
    Create iterative research flow.

    Args:
        max_iterations: Maximum number of iterations
        max_time_minutes: Maximum time in minutes
        verbose: Whether to log progress
        use_graph: Whether to use graph execution. If None, reads from settings.use_graph_execution

    Returns:
        Configured IterativeResearchFlow instance
    """
    from src.orchestrator.research_flow import IterativeResearchFlow

    try:
        # Use settings default if not explicitly provided
        if use_graph is None:
            use_graph = settings.use_graph_execution

        logger.debug("Creating iterative research flow", use_graph=use_graph)
        return IterativeResearchFlow(
            max_iterations=max_iterations,
            max_time_minutes=max_time_minutes,
            verbose=verbose,
            use_graph=use_graph,
        )
    except Exception as e:
        logger.error("Failed to create iterative flow", error=str(e))
        raise ConfigurationError(f"Failed to create iterative flow: {e}") from e


def create_deep_flow(
    max_iterations: int = 5,
    max_time_minutes: int = 10,
    verbose: bool = True,
    use_long_writer: bool = True,
    use_graph: bool | None = None,
) -> "DeepResearchFlow":
    """
    Create deep research flow.

    Args:
        max_iterations: Maximum iterations per section
        max_time_minutes: Maximum time per section
        verbose: Whether to log progress
        use_long_writer: Whether to use long writer (True) or proofreader (False)
        use_graph: Whether to use graph execution. If None, reads from settings.use_graph_execution

    Returns:
        Configured DeepResearchFlow instance
    """
    from src.orchestrator.research_flow import DeepResearchFlow

    try:
        # Use settings default if not explicitly provided
        if use_graph is None:
            use_graph = settings.use_graph_execution

        logger.debug("Creating deep research flow", use_graph=use_graph)
        return DeepResearchFlow(
            max_iterations=max_iterations,
            max_time_minutes=max_time_minutes,
            verbose=verbose,
            use_long_writer=use_long_writer,
            use_graph=use_graph,
        )
    except Exception as e:
        logger.error("Failed to create deep flow", error=str(e))
        raise ConfigurationError(f"Failed to create deep flow: {e}") from e


def create_graph_orchestrator(
    mode: str = "auto",
    max_iterations: int = 5,
    max_time_minutes: int = 10,
    use_graph: bool = True,
) -> "GraphOrchestrator":
    """
    Create graph orchestrator.

    Args:
        mode: Research mode ("iterative", "deep", or "auto")
        max_iterations: Maximum iterations per loop
        max_time_minutes: Maximum time per loop
        use_graph: Whether to use graph execution (True) or agent chains (False)

    Returns:
        Configured GraphOrchestrator instance
    """
    from src.orchestrator.graph_orchestrator import create_graph_orchestrator as _create

    try:
        logger.debug("Creating graph orchestrator", mode=mode, use_graph=use_graph)
        return _create(
            mode=mode,  # type: ignore[arg-type]
            max_iterations=max_iterations,
            max_time_minutes=max_time_minutes,
            use_graph=use_graph,
        )
    except Exception as e:
        logger.error("Failed to create graph orchestrator", error=str(e))
        raise ConfigurationError(f"Failed to create graph orchestrator: {e}") from e


def create_graph_builder() -> "GraphBuilder":
    """
    Create a graph builder instance.

    Returns:
        GraphBuilder instance
    """
    from src.agent_factory.graph_builder import GraphBuilder

    try:
        logger.debug("Creating graph builder")
        return GraphBuilder()
    except Exception as e:
        logger.error("Failed to create graph builder", error=str(e))
        raise ConfigurationError(f"Failed to create graph builder: {e}") from e
