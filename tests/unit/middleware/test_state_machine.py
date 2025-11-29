"""Unit tests for WorkflowState and Conversation models."""

from contextvars import copy_context
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.middleware.state_machine import (
    WorkflowState,
    get_workflow_state,
    init_workflow_state,
)
from src.utils.models import Citation, Conversation, Evidence, IterationData


@pytest.mark.unit
class TestWorkflowState:
    """Tests for WorkflowState model."""

    def test_initialization(self) -> None:
        """WorkflowState should initialize with empty evidence and conversation."""
        state = WorkflowState()
        assert state.evidence == []
        assert isinstance(state.conversation, Conversation)
        assert state.conversation.history == []
        assert state.embedding_service is None

    def test_add_evidence_deduplicates_by_url(self) -> None:
        """add_evidence should deduplicate evidence by URL."""
        state = WorkflowState()

        ev1 = Evidence(
            content="Content 1",
            citation=Citation(
                source="pubmed",
                title="Title 1",
                url="https://example.com/1",
                date="2024-01-01",
            ),
        )
        ev2 = Evidence(
            content="Content 2",
            citation=Citation(
                source="pubmed",
                title="Title 2",
                url="https://example.com/2",
                date="2024-01-02",
            ),
        )
        ev3_duplicate = Evidence(
            content="Content 3",
            citation=Citation(
                source="pubmed",
                title="Title 1 Duplicate",
                url="https://example.com/1",  # Same URL as ev1
                date="2024-01-01",
            ),
        )

        # Add first two
        count1 = state.add_evidence([ev1, ev2])
        assert count1 == 2
        assert len(state.evidence) == 2

        # Try to add duplicate
        count2 = state.add_evidence([ev3_duplicate])
        assert count2 == 0  # No new items added
        assert len(state.evidence) == 2  # Still only 2 items

    def test_add_evidence_returns_count(self) -> None:
        """add_evidence should return the number of new items added."""
        state = WorkflowState()

        ev1 = Evidence(
            content="Content 1",
            citation=Citation(
                source="pubmed", title="Title 1", url="https://example.com/1", date="2024-01-01"
            ),
        )

        count = state.add_evidence([ev1])
        assert count == 1

        # Adding same again should return 0
        count2 = state.add_evidence([ev1])
        assert count2 == 0

    @pytest.mark.asyncio
    async def test_search_related_without_embedding_service(self) -> None:
        """search_related should return empty list if embedding service is None."""
        state = WorkflowState()
        results = await state.search_related("test query", n_results=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_related_with_embedding_service(self) -> None:
        """search_related should use embedding service to find similar evidence."""
        # Mock embedding service
        mock_embedding_service = MagicMock()
        mock_embedding_service.search_similar = AsyncMock(
            return_value=[
                {
                    "id": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                    "content": "Test content",
                    "metadata": {
                        "title": "Test Title",
                        "authors": "Smith J, Doe J",
                        "date": "2024-01-01",
                    },
                    "distance": 0.2,
                }
            ]
        )

        state = WorkflowState(embedding_service=mock_embedding_service)
        results = await state.search_related("test query", n_results=5)

        assert len(results) == 1
        assert results[0].content == "Test content"
        assert results[0].citation.url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
        assert results[0].citation.title == "Test Title"
        assert results[0].relevance == 0.8  # 1.0 - 0.2
        mock_embedding_service.search_similar.assert_called_once_with("test query", n_results=5)

    @pytest.mark.asyncio
    async def test_search_related_handles_empty_authors(self) -> None:
        """search_related should handle empty authors string."""
        mock_embedding_service = MagicMock()
        mock_embedding_service.search_similar = AsyncMock(
            return_value=[
                {
                    "id": "https://example.com/1",
                    "content": "Test",
                    "metadata": {"title": "Title", "authors": "", "date": "2024-01-01"},
                    "distance": 0.1,
                }
            ]
        )

        state = WorkflowState(embedding_service=mock_embedding_service)
        results = await state.search_related("query")

        assert len(results) == 1
        assert results[0].citation.authors == []


@pytest.mark.unit
class TestConversation:
    """Tests for Conversation model methods."""

    def test_add_iteration(self) -> None:
        """add_iteration should add a new iteration to history."""
        conv = Conversation()
        assert len(conv.history) == 0

        conv.add_iteration()
        assert len(conv.history) == 1
        assert isinstance(conv.history[0], IterationData)

    def test_add_iteration_with_data(self) -> None:
        """add_iteration should accept custom IterationData."""
        conv = Conversation()
        iteration = IterationData(gap="Test gap", tool_calls=["tool1"], findings=["finding1"])

        conv.add_iteration(iteration)
        assert len(conv.history) == 1
        assert conv.history[0].gap == "Test gap"

    def test_set_latest_gap(self) -> None:
        """set_latest_gap should set gap for latest iteration."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_gap("New gap")
        assert conv.get_latest_gap() == "New gap"

    def test_set_latest_gap_auto_creates_iteration(self) -> None:
        """set_latest_gap should auto-create iteration if history is empty."""
        conv = Conversation()
        conv.set_latest_gap("Auto gap")
        assert len(conv.history) == 1
        assert conv.get_latest_gap() == "Auto gap"

    def test_set_latest_tool_calls(self) -> None:
        """set_latest_tool_calls should set tool calls for latest iteration."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_tool_calls(["tool1", "tool2"])
        assert conv.get_latest_tool_calls() == ["tool1", "tool2"]

    def test_set_latest_findings(self) -> None:
        """set_latest_findings should set findings for latest iteration."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_findings(["finding1", "finding2"])
        assert conv.get_latest_findings() == ["finding1", "finding2"]

    def test_set_latest_thought(self) -> None:
        """set_latest_thought should set thought for latest iteration."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_thought("This is a thought")
        assert conv.get_latest_thought() == "This is a thought"

    def test_get_all_findings(self) -> None:
        """get_all_findings should return findings from all iterations."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_findings(["finding1", "finding2"])
        conv.add_iteration()
        conv.set_latest_findings(["finding3"])

        all_findings = conv.get_all_findings()
        assert len(all_findings) == 3
        assert "finding1" in all_findings
        assert "finding2" in all_findings
        assert "finding3" in all_findings

    def test_compile_conversation_history(self) -> None:
        """compile_conversation_history should format conversation as string."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_gap("Gap 1")
        conv.set_latest_tool_calls(["tool1"])
        conv.set_latest_findings(["finding1"])
        conv.set_latest_thought("Thought 1")

        history = conv.compile_conversation_history()
        assert "[ITERATION 1]" in history
        assert "Gap 1" in history
        assert "tool1" in history
        assert "finding1" in history
        assert "Thought 1" in history

    def test_get_task_string(self) -> None:
        """get_task_string should format task correctly."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_gap("Test gap")

        task_str = conv.get_task_string(0)
        assert "<task>" in task_str
        assert "Test gap" in task_str

    def test_get_action_string(self) -> None:
        """get_action_string should format action correctly."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_tool_calls(["tool1", "tool2"])

        action_str = conv.get_action_string(0)
        assert "<action>" in action_str
        assert "tool1" in action_str
        assert "tool2" in action_str

    def test_get_findings_string(self) -> None:
        """get_findings_string should format findings correctly."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_findings(["finding1", "finding2"])

        findings_str = conv.get_findings_string(0)
        assert "<findings>" in findings_str
        assert "finding1" in findings_str
        assert "finding2" in findings_str

    def test_get_thought_string(self) -> None:
        """get_thought_string should format thought correctly."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_thought("Test thought")

        thought_str = conv.get_thought_string(0)
        assert "<thought>" in thought_str
        assert "Test thought" in thought_str

    def test_latest_helper_methods(self) -> None:
        """latest_* methods should work on most recent iteration."""
        conv = Conversation()
        conv.add_iteration()
        conv.set_latest_gap("Gap 1")
        conv.add_iteration()
        conv.set_latest_gap("Gap 2")

        assert conv.latest_task_string() == conv.get_task_string(1)
        assert "Gap 2" in conv.latest_task_string()


@pytest.mark.unit
class TestContextVarIsolation:
    """Tests for ContextVar isolation between contexts."""

    def test_init_workflow_state(self) -> None:
        """init_workflow_state should create state in current context."""
        state = init_workflow_state()
        assert isinstance(state, WorkflowState)
        assert get_workflow_state() == state

    def test_get_workflow_state_auto_initializes(self) -> None:
        """get_workflow_state should auto-initialize if not set."""
        # Create new context
        ctx = copy_context()
        state = ctx.run(get_workflow_state)
        assert isinstance(state, WorkflowState)

    def test_context_isolation(self) -> None:
        """Different contexts should have isolated state."""

        # Context 1
        def context1():
            state1 = init_workflow_state()
            state1.add_evidence(
                [
                    Evidence(
                        content="Evidence 1",
                        citation=Citation(
                            source="pubmed",
                            title="Title 1",
                            url="https://example.com/1",
                            date="2024",
                        ),
                    )
                ]
            )
            return get_workflow_state()

        # Context 2
        def context2():
            state2 = init_workflow_state()
            state2.add_evidence(
                [
                    Evidence(
                        content="Evidence 2",
                        citation=Citation(
                            source="pubmed",
                            title="Title 2",
                            url="https://example.com/2",
                            date="2024",
                        ),
                    )
                ]
            )
            return get_workflow_state()

        # Run in separate contexts
        ctx1 = copy_context()
        ctx2 = copy_context()
        state1 = ctx1.run(context1)
        state2 = ctx2.run(context2)

        # States should be different objects
        assert state1 is not state2
        # Each should have their own evidence
        assert len(state1.evidence) == 1
        assert len(state2.evidence) == 1
        assert state1.evidence[0].citation.url == "https://example.com/1"
        assert state2.evidence[0].citation.url == "https://example.com/2"
