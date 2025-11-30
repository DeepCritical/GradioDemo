"""Factory for creating orchestrators."""

from typing import Any, Literal

import structlog

from src.legacy_orchestrator import (
    JudgeHandlerProtocol,
    Orchestrator,
    SearchHandlerProtocol,
)
from src.utils.config import settings
from src.utils.models import OrchestratorConfig

logger = structlog.get_logger()


def _get_magentic_orchestrator_class() -> Any:
    """Import MagenticOrchestrator lazily to avoid hard dependency."""
    try:
        from src.orchestrator_magentic import MagenticOrchestrator

        return MagenticOrchestrator
    except ImportError as e:
        logger.error("Failed to import MagenticOrchestrator", error=str(e))
        raise ValueError(
            "Advanced mode requires agent-framework-core. Please install it or use mode='simple'."
        ) from e


def _get_graph_orchestrator_class() -> Any:
    """Import GraphOrchestrator lazily to avoid circular imports."""
    from src.orchestrator.graph_orchestrator import GraphOrchestrator

    return GraphOrchestrator


def create_orchestrator(
    search_handler: SearchHandlerProtocol | None = None,
    judge_handler: JudgeHandlerProtocol | None = None,
    config: OrchestratorConfig | None = None,
    mode: Literal["simple", "magentic", "advanced"] | None = None,
    graph_mode: Literal["iterative", "deep", "auto"] | None = None,
    use_graph: bool | None = None,
) -> Any:
    """
    Create an orchestrator instance.

    Args:
        search_handler: The search handler (required for simple mode)
        judge_handler: The judge handler (required for simple mode)
        config: Optional configuration
        mode: "simple", "magentic", "advanced" or None (auto-detect)
        graph_mode: Graph research mode (iterative/deep/auto)
        use_graph: Whether to run the graph orchestrator path

    Returns:
        Orchestrator instance
    """
    effective_mode = _determine_mode(mode)
    effective_graph_mode = graph_mode or "auto"
    use_graph_execution = settings.use_graph_execution if use_graph is None else use_graph
    logger.info(
        "Creating orchestrator",
        mode=effective_mode,
        use_graph=use_graph_execution,
        graph_mode=effective_graph_mode,
    )

    if use_graph_execution:
        orchestrator_cls = _get_graph_orchestrator_class()
        return orchestrator_cls(
            mode=effective_graph_mode,  # type: ignore[arg-type]
            max_iterations=config.max_iterations if config else settings.default_iterations_limit,
            max_time_minutes=settings.default_time_limit_minutes,
            use_graph=use_graph_execution,
            search_handler=search_handler,
            judge_handler=judge_handler,
        )

    if effective_mode == "advanced":
        orchestrator_cls = _get_magentic_orchestrator_class()
        return orchestrator_cls(
            max_rounds=config.max_iterations if config else 10,
        )

    # Simple mode requires handlers
    if search_handler is None or judge_handler is None:
        raise ValueError("Simple mode requires search_handler and judge_handler")

    return Orchestrator(
        search_handler=search_handler,
        judge_handler=judge_handler,
        config=config,
    )


def _determine_mode(explicit_mode: str | None) -> str:
    """Determine which mode to use."""
    if explicit_mode:
        if explicit_mode in ("magentic", "advanced"):
            return "advanced"
        return "simple"

    # Auto-detect: advanced if paid API key available
    if settings.has_openai_key:
        return "advanced"

    return "simple"
