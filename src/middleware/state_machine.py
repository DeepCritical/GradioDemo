"""Thread-safe state management for workflow agents.

Uses contextvars to ensure isolation between concurrent requests (e.g., multiple users
searching simultaneously via Gradio). Refactored from MagenticState to support both
iterative and deep research patterns.
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from src.utils.models import Citation, Conversation, Evidence

if TYPE_CHECKING:
    from src.services.embeddings import EmbeddingService

logger = structlog.get_logger()


class WorkflowState(BaseModel):
    """Mutable state for a workflow session.

    Supports both iterative and deep research patterns by tracking evidence,
    conversation history, and providing semantic search capabilities.
    """

    evidence: list[Evidence] = Field(default_factory=list)
    conversation: Conversation = Field(default_factory=Conversation)
    # Type as Any to avoid circular imports/runtime resolution issues
    # The actual object injected will be an EmbeddingService instance
    embedding_service: Any = Field(default=None)

    model_config = {"arbitrary_types_allowed": True}

    def add_evidence(self, new_evidence: list[Evidence]) -> int:
        """Add new evidence, deduplicating by URL.

        Args:
            new_evidence: List of Evidence objects to add.

        Returns:
            Number of *new* items added (excluding duplicates).
        """
        existing_urls = {e.citation.url for e in self.evidence}
        count = 0
        for item in new_evidence:
            if item.citation.url not in existing_urls:
                self.evidence.append(item)
                existing_urls.add(item.citation.url)
                count += 1
        return count

    async def search_related(self, query: str, n_results: int = 5) -> list[Evidence]:
        """Search for semantically related evidence using the embedding service.

        Args:
            query: Search query string.
            n_results: Maximum number of results to return.

        Returns:
            List of Evidence objects, ordered by relevance.
        """
        if not self.embedding_service:
            logger.warning("Embedding service not available, returning empty results")
            return []

        results = await self.embedding_service.search_similar(query, n_results=n_results)

        # Convert dict results back to Evidence objects
        evidence_list = []
        for item in results:
            meta = item.get("metadata", {})
            authors_str = meta.get("authors", "")
            authors = [a.strip() for a in authors_str.split(",") if a.strip()]

            ev = Evidence(
                content=item["content"],
                citation=Citation(
                    title=meta.get("title", "Related Evidence"),
                    url=item["id"],
                    source="pubmed",  # Defaulting to pubmed if unknown
                    date=meta.get("date", "n.d."),
                    authors=authors,
                ),
                relevance=max(0.0, 1.0 - item.get("distance", 0.5)),
            )
            evidence_list.append(ev)

        return evidence_list


# The ContextVar holds the WorkflowState for the current execution context
_workflow_state_var: ContextVar[WorkflowState | None] = ContextVar("workflow_state", default=None)


def init_workflow_state(
    embedding_service: "EmbeddingService | None" = None,
) -> WorkflowState:
    """Initialize a new state for the current context.

    Args:
        embedding_service: Optional embedding service for semantic search.

    Returns:
        The initialized WorkflowState instance.
    """
    state = WorkflowState(embedding_service=embedding_service)
    _workflow_state_var.set(state)
    logger.debug("Workflow state initialized", has_embeddings=embedding_service is not None)
    return state


def get_workflow_state() -> WorkflowState:
    """Get the current state. Auto-initializes if not set.

    Returns:
        The current WorkflowState instance.

    Raises:
        RuntimeError: If state is not initialized and auto-initialization fails.
    """
    state = _workflow_state_var.get()
    if state is None:
        # Auto-initialize if missing (e.g. during tests or simple scripts)
        logger.debug("Workflow state not found, auto-initializing")
        return init_workflow_state()
    return state
