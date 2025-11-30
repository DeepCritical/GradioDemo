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


def _get_graph_orchestrator_factory() -> Any:
    """Import create_graph_orchestrator lazily to avoid circular dependencies."""
    try:
        from src.orchestrator.graph_orchestrator import create_graph_orchestrator

        return create_graph_orchestrator
    except ImportError as e:
        logger.error("Failed to import create_graph_orchestrator", error=str(e))
        raise ValueError(
            "Graph orchestrators require Pydantic Graph. Please check dependencies."
        ) from e


def create_orchestrator(
    search_handler: SearchHandlerProtocol | None = None,
    judge_handler: JudgeHandlerProtocol | None = None,
    config: OrchestratorConfig | None = None,
    mode: Literal["simple", "magentic", "advanced", "iterative", "deep", "auto"] | None = None,
) -> Any:
    """
    Create an orchestrator instance.

    Args:
        search_handler: The search handler (required for simple mode)
        judge_handler: The judge handler (required for simple mode)
        config: Optional configuration
        mode: Orchestrator mode - "simple", "advanced", "iterative", "deep", "auto", or None (auto-detect)
            - "simple": Linear search-judge loop (Free Tier)
            - "advanced": Multi-agent coordination (Requires OpenAI)
            - "iterative": Knowledge-gap-driven research (Free Tier)
            - "deep": Parallel section-based research (Free Tier)
            - "auto": Intelligent mode detection (Free Tier)

    Returns:
        Orchestrator instance
    """
    effective_mode = _determine_mode(mode)
    logger.info("Creating orchestrator", mode=effective_mode)

    if effective_mode == "advanced":
        orchestrator_cls = _get_magentic_orchestrator_class()
        return orchestrator_cls(
            max_rounds=config.max_iterations if config else 10,
        )

    # Graph-based orchestrators (iterative, deep, auto)
    if effective_mode in ("iterative", "deep", "auto"):
        create_graph_orchestrator = _get_graph_orchestrator_factory()
        return create_graph_orchestrator(
            mode=effective_mode,  # type: ignore[arg-type]
            max_iterations=config.max_iterations if config else 5,
            max_time_minutes=10,
            use_graph=True,
            search_handler=search_handler,
            judge_handler=judge_handler,
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
        if explicit_mode in ("iterative", "deep", "auto"):
            return explicit_mode
        return "simple"

    # Auto-detect: advanced if paid API key available, otherwise simple
    if settings.has_openai_key:
        return "advanced"

    return "simple"
