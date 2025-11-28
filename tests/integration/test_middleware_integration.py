"""Integration tests for middleware components.

Tests the interaction between WorkflowState, WorkflowManager, and BudgetTracker.
"""

import pytest

from src.middleware.budget_tracker import BudgetTracker
from src.middleware.state_machine import init_workflow_state
from src.middleware.workflow_manager import WorkflowManager
from src.utils.models import Citation, Evidence


@pytest.mark.integration
class TestMiddlewareIntegration:
    """Integration tests for middleware components."""

    @pytest.mark.asyncio
    async def test_state_manager_integration(self) -> None:
        """Test WorkflowState and WorkflowManager integration."""
        # Initialize state
        state = init_workflow_state()
        manager = WorkflowManager()

        # Create a loop
        loop = await manager.add_loop("test_loop", "Test query")

        # Add evidence to loop
        ev = Evidence(
            content="Test evidence",
            citation=Citation(
                source="pubmed", title="Test Title", url="https://example.com/1", date="2024-01-01"
            ),
        )
        await manager.add_loop_evidence("test_loop", [ev])

        # Sync to global state
        await manager.sync_loop_evidence_to_state("test_loop")

        # Verify state has evidence
        assert len(state.evidence) == 1
        assert state.evidence[0].content == "Test evidence"

        # Verify loop still has evidence
        loop = await manager.get_loop("test_loop")
        assert loop is not None
        assert len(loop.evidence) == 1

    @pytest.mark.asyncio
    async def test_budget_tracker_with_workflow_manager(self) -> None:
        """Test BudgetTracker integration with WorkflowManager."""
        manager = WorkflowManager()
        tracker = BudgetTracker()

        # Create loop and budget
        await manager.add_loop("budget_loop", "Test query")
        tracker.create_budget("budget_loop", tokens_limit=1000, time_limit_seconds=60.0)
        tracker.start_timer("budget_loop")

        # Simulate some work
        tracker.add_tokens("budget_loop", 500)
        await manager.increment_loop_iteration("budget_loop")
        tracker.increment_iteration("budget_loop")

        # Check budget
        can_continue = tracker.can_continue("budget_loop")
        assert can_continue is True

        # Exceed budget
        tracker.add_tokens("budget_loop", 600)  # Total: 1100 > 1000
        can_continue = tracker.can_continue("budget_loop")
        assert can_continue is False

        # Update loop status based on budget
        if not can_continue:
            await manager.update_loop_status("budget_loop", "cancelled")

        loop = await manager.get_loop("budget_loop")
        assert loop is not None
        assert loop.status == "cancelled"

    @pytest.mark.asyncio
    async def test_parallel_loops_with_budget_tracking(self) -> None:
        """Test parallel loops with budget tracking."""

        async def mock_research_loop(config: dict) -> str:
            """Mock research loop function."""
            loop_id = config.get("loop_id", "unknown")
            tracker = BudgetTracker()
            manager = WorkflowManager()

            # Get or create budget
            budget = tracker.get_budget(loop_id)
            if not budget:
                tracker.create_budget(loop_id, tokens_limit=500, time_limit_seconds=10.0)
                tracker.start_timer(loop_id)

            # Simulate work
            tracker.add_tokens(loop_id, 100)
            await manager.increment_loop_iteration(loop_id)
            tracker.increment_iteration(loop_id)

            # Check if can continue
            if not tracker.can_continue(loop_id):
                await manager.update_loop_status(loop_id, "cancelled")
                return f"Cancelled: {loop_id}"

            await manager.update_loop_status(loop_id, "completed")
            return f"Completed: {loop_id}"

        manager = WorkflowManager()
        tracker = BudgetTracker()

        # Create budgets for all loops
        configs = [
            {"loop_id": "loop1", "query": "Query 1"},
            {"loop_id": "loop2", "query": "Query 2"},
            {"loop_id": "loop3", "query": "Query 3"},
        ]

        for config in configs:
            loop_id = config["loop_id"]
            await manager.add_loop(loop_id, config["query"])
            tracker.create_budget(loop_id, tokens_limit=500, time_limit_seconds=10.0)
            tracker.start_timer(loop_id)

        # Run loops in parallel
        results = await manager.run_loops_parallel(configs, mock_research_loop)

        # Verify all loops completed
        assert len(results) == 3
        for config in configs:
            loop_id = config["loop_id"]
            loop = await manager.get_loop(loop_id)
            assert loop is not None
            assert loop.status in ("completed", "cancelled")

    @pytest.mark.asyncio
    async def test_state_conversation_integration(self) -> None:
        """Test WorkflowState conversation integration."""
        state = init_workflow_state()

        # Add iteration data
        state.conversation.add_iteration()
        state.conversation.set_latest_gap("Knowledge gap 1")
        state.conversation.set_latest_tool_calls(["tool1", "tool2"])
        state.conversation.set_latest_findings(["finding1", "finding2"])
        state.conversation.set_latest_thought("Thought about findings")

        # Verify conversation history
        assert len(state.conversation.history) == 1
        assert state.conversation.get_latest_gap() == "Knowledge gap 1"
        assert len(state.conversation.get_latest_tool_calls()) == 2
        assert len(state.conversation.get_latest_findings()) == 2

        # Compile history
        history_str = state.conversation.compile_conversation_history()
        assert "Knowledge gap 1" in history_str
        assert "tool1" in history_str
        assert "finding1" in history_str
        assert "Thought about findings" in history_str

    @pytest.mark.asyncio
    async def test_multiple_iterations_with_budget(self) -> None:
        """Test multiple iterations with budget enforcement."""
        manager = WorkflowManager()
        tracker = BudgetTracker()

        loop_id = "iterative_loop"
        await manager.add_loop(loop_id, "Iterative query")
        tracker.create_budget(loop_id, tokens_limit=1000, iterations_limit=5)
        tracker.start_timer(loop_id)

        # Simulate multiple iterations
        for _ in range(7):  # Try 7 iterations, but limit is 5
            tracker.add_tokens(loop_id, 100)
            await manager.increment_loop_iteration(loop_id)
            tracker.increment_iteration(loop_id)

            can_continue = tracker.can_continue(loop_id)
            if not can_continue:
                await manager.update_loop_status(loop_id, "cancelled")
                break

        loop = await manager.get_loop(loop_id)
        assert loop is not None
        # Should be cancelled after 5 iterations
        assert loop.status == "cancelled"
        assert loop.iteration_count == 5

    @pytest.mark.asyncio
    async def test_evidence_deduplication_across_loops(self) -> None:
        """Test evidence deduplication when syncing from multiple loops."""
        state = init_workflow_state()
        manager = WorkflowManager()

        # Create two loops with same evidence
        ev1 = Evidence(
            content="Same content",
            citation=Citation(
                source="pubmed", title="Title", url="https://example.com/1", date="2024"
            ),
        )
        ev2 = Evidence(
            content="Different content",
            citation=Citation(
                source="pubmed", title="Title 2", url="https://example.com/2", date="2024"
            ),
        )

        # Add to loop1
        await manager.add_loop("loop1", "Query 1")
        await manager.add_loop_evidence("loop1", [ev1, ev2])
        await manager.sync_loop_evidence_to_state("loop1")

        # Add duplicate to loop2
        await manager.add_loop("loop2", "Query 2")
        ev1_duplicate = Evidence(
            content="Same content (duplicate)",
            citation=Citation(
                source="pubmed", title="Title Duplicate", url="https://example.com/1", date="2024"
            ),
        )
        await manager.add_loop_evidence("loop2", [ev1_duplicate])
        await manager.sync_loop_evidence_to_state("loop2")

        # State should have only 2 unique items (deduplicated by URL)
        assert len(state.evidence) == 2

    @pytest.mark.asyncio
    async def test_global_budget_enforcement(self) -> None:
        """Test global budget enforcement across all loops."""
        tracker = BudgetTracker()
        tracker.set_global_budget(tokens_limit=2000, time_limit_seconds=60.0)

        # Simulate multiple loops consuming global budget
        tracker.add_global_tokens(500)  # Loop 1
        tracker.add_global_tokens(600)  # Loop 2
        tracker.add_global_tokens(700)  # Loop 3
        tracker.add_global_tokens(300)  # Loop 4 - would exceed

        global_budget = tracker.get_global_budget()
        assert global_budget is not None
        assert global_budget.tokens_used == 2100
        assert global_budget.is_exceeded() is True
