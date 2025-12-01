"""Unit tests for WorkflowManager."""

import asyncio

import pytest

from src.middleware.workflow_manager import ResearchLoop, WorkflowManager
from src.utils.models import Citation, Evidence


@pytest.mark.unit
class TestResearchLoop:
    """Tests for ResearchLoop model."""

    def test_initialization(self) -> None:
        """ResearchLoop should initialize with default values."""
        loop = ResearchLoop(loop_id="test1", query="Test query")
        assert loop.loop_id == "test1"
        assert loop.query == "Test query"
        assert loop.status == "pending"
        assert loop.evidence == []
        assert loop.iteration_count == 0
        assert loop.error is None

    def test_status_mutable(self) -> None:
        """ResearchLoop status should be mutable."""
        loop = ResearchLoop(loop_id="test1", query="Test")
        loop.status = "running"
        assert loop.status == "running"


@pytest.mark.unit
class TestWorkflowManager:
    """Tests for WorkflowManager class."""

    @pytest.mark.asyncio
    async def test_add_loop(self) -> None:
        """add_loop should create a new research loop."""
        manager = WorkflowManager()
        loop = await manager.add_loop("loop1", "Test query")

        assert loop.loop_id == "loop1"
        assert loop.query == "Test query"
        assert loop.status == "pending"

    @pytest.mark.asyncio
    async def test_get_loop(self) -> None:
        """get_loop should return loop by ID."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query 1")
        loop = await manager.get_loop("loop1")

        assert loop is not None
        assert loop.loop_id == "loop1"

    @pytest.mark.asyncio
    async def test_get_loop_not_found(self) -> None:
        """get_loop should return None if loop not found."""
        manager = WorkflowManager()
        loop = await manager.get_loop("nonexistent")
        assert loop is None

    @pytest.mark.asyncio
    async def test_update_loop_status(self) -> None:
        """update_loop_status should update loop status."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query")
        await manager.update_loop_status("loop1", "running")

        loop = await manager.get_loop("loop1")
        assert loop is not None
        assert loop.status == "running"

    @pytest.mark.asyncio
    async def test_update_loop_status_with_error(self) -> None:
        """update_loop_status should set error message."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query")
        await manager.update_loop_status("loop1", "failed", error="Test error")

        loop = await manager.get_loop("loop1")
        assert loop is not None
        assert loop.status == "failed"
        assert loop.error == "Test error"

    @pytest.mark.asyncio
    async def test_add_loop_evidence(self) -> None:
        """add_loop_evidence should add evidence to loop."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query")

        ev = Evidence(
            content="Test content",
            citation=Citation(
                source="pubmed", title="Title", url="https://example.com", date="2024"
            ),
        )
        await manager.add_loop_evidence("loop1", [ev])

        loop = await manager.get_loop("loop1")
        assert loop is not None
        assert len(loop.evidence) == 1

    @pytest.mark.asyncio
    async def test_increment_loop_iteration(self) -> None:
        """increment_loop_iteration should increment iteration count."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query")
        await manager.increment_loop_iteration("loop1")
        await manager.increment_loop_iteration("loop1")

        loop = await manager.get_loop("loop1")
        assert loop is not None
        assert loop.iteration_count == 2

    @pytest.mark.asyncio
    async def test_run_loops_parallel(self) -> None:
        """run_loops_parallel should run multiple loops concurrently."""

        async def mock_loop_func(config: dict) -> str:
            loop_id = config.get("loop_id", "unknown")
            await asyncio.sleep(0.01)  # Simulate work
            return f"Result from {loop_id}"

        manager = WorkflowManager()
        configs = [
            {"loop_id": "loop1", "query": "Query 1"},
            {"loop_id": "loop2", "query": "Query 2"},
            {"loop_id": "loop3", "query": "Query 3"},
        ]

        results = await manager.run_loops_parallel(configs, mock_loop_func)

        assert len(results) == 3
        assert any("loop1" in str(r) for r in results)
        assert any("loop2" in str(r) for r in results)
        assert any("loop3" in str(r) for r in results)

        # Check all loops were created
        loop1 = await manager.get_loop("loop1")
        loop2 = await manager.get_loop("loop2")
        loop3 = await manager.get_loop("loop3")
        assert loop1 is not None
        assert loop2 is not None
        assert loop3 is not None
        assert loop1.status == "completed"
        assert loop2.status == "completed"
        assert loop3.status == "completed"

    @pytest.mark.asyncio
    async def test_run_loops_parallel_handles_errors(self) -> None:
        """run_loops_parallel should handle errors per loop."""

        async def failing_loop_func(config: dict) -> str:
            loop_id = config.get("loop_id", "unknown")
            if loop_id == "loop2":
                raise ValueError("Test error")
            return f"Result from {loop_id}"

        manager = WorkflowManager()
        configs = [
            {"loop_id": "loop1", "query": "Query 1"},
            {"loop_id": "loop2", "query": "Query 2"},
            {"loop_id": "loop3", "query": "Query 3"},
        ]

        results = await manager.run_loops_parallel(configs, failing_loop_func)

        # Should have 3 results (including exception)
        assert len(results) == 3

        # Check loop statuses
        loop1 = await manager.get_loop("loop1")
        loop2 = await manager.get_loop("loop2")
        loop3 = await manager.get_loop("loop3")
        assert loop1 is not None
        assert loop1.status == "completed"
        assert loop2 is not None
        assert loop2.status == "failed"
        assert loop2.error == "Test error"
        assert loop3 is not None
        assert loop3.status == "completed"

    @pytest.mark.asyncio
    async def test_wait_for_loops(self) -> None:
        """wait_for_loops should wait for loops to complete."""

        async def slow_loop_func(config: dict) -> str:
            await asyncio.sleep(0.05)
            return "done"

        manager = WorkflowManager()
        configs = [
            {"loop_id": "loop1", "query": "Query 1"},
            {"loop_id": "loop2", "query": "Query 2"},
        ]

        # Start loops
        await manager.run_loops_parallel(configs, slow_loop_func)

        # Wait for them
        loops = await manager.wait_for_loops(["loop1", "loop2"], timeout=1.0)

        assert len(loops) == 2
        assert all(loop.status in ("completed", "failed") for loop in loops)

    @pytest.mark.asyncio
    async def test_wait_for_loops_timeout(self) -> None:
        """wait_for_loops should respect timeout."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query")
        await manager.update_loop_status("loop1", "running")

        # Should timeout quickly since loop is still running
        loops = await manager.wait_for_loops(["loop1"], timeout=0.01)

        # Should return the loop even if not completed
        assert len(loops) == 1

    @pytest.mark.asyncio
    async def test_cancel_loop(self) -> None:
        """cancel_loop should set status to cancelled."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query")
        await manager.cancel_loop("loop1")

        loop = await manager.get_loop("loop1")
        assert loop is not None
        assert loop.status == "cancelled"

    @pytest.mark.asyncio
    async def test_get_all_loops(self) -> None:
        """get_all_loops should return all loops."""
        manager = WorkflowManager()
        await manager.add_loop("loop1", "Query 1")
        await manager.add_loop("loop2", "Query 2")
        await manager.add_loop("loop3", "Query 3")

        all_loops = await manager.get_all_loops()
        assert len(all_loops) == 3

    @pytest.mark.asyncio
    async def test_sync_loop_evidence_to_state(self, monkeypatch) -> None:
        """sync_loop_evidence_to_state should merge evidence into global state."""
        from src.middleware.state_machine import init_workflow_state

        # Initialize state
        state = init_workflow_state()
        manager = WorkflowManager()

        await manager.add_loop("loop1", "Query")
        ev = Evidence(
            content="Test",
            citation=Citation(
                source="pubmed", title="Title", url="https://example.com", date="2024"
            ),
        )
        await manager.add_loop_evidence("loop1", [ev])

        # Sync to state
        await manager.sync_loop_evidence_to_state("loop1")

        # Check state has evidence
        assert len(state.evidence) == 1
        assert state.evidence[0].citation.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_get_shared_evidence(self, monkeypatch) -> None:
        """get_shared_evidence should return evidence from global state."""
        from src.middleware.state_machine import init_workflow_state

        # Initialize state and add evidence
        state = init_workflow_state()
        ev = Evidence(
            content="Shared",
            citation=Citation(
                source="pubmed", title="Title", url="https://example.com", date="2024"
            ),
        )
        state.add_evidence([ev])

        manager = WorkflowManager()
        shared = await manager.get_shared_evidence()

        assert len(shared) == 1
        assert shared[0].content == "Shared"
