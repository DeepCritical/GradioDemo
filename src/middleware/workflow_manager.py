"""Workflow manager for coordinating parallel research loops.

Manages multiple research loops running in parallel, tracks their status,
and synchronizes evidence between loops and the global state.
"""

import asyncio
from collections.abc import Callable
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from src.middleware.state_machine import get_workflow_state
from src.utils.models import Evidence

logger = structlog.get_logger()

LoopStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class ResearchLoop(BaseModel):
    """Represents a single research loop."""

    loop_id: str = Field(description="Unique identifier for the loop")
    query: str = Field(description="The research query for this loop")
    status: LoopStatus = Field(default="pending")
    evidence: list[Evidence] = Field(default_factory=list)
    iteration_count: int = Field(default=0, ge=0)
    error: str | None = Field(default=None)

    model_config = {"frozen": False}  # Mutable for status updates


class WorkflowManager:
    """Manages parallel research loops and state synchronization."""

    def __init__(self) -> None:
        """Initialize the workflow manager."""
        self._loops: dict[str, ResearchLoop] = {}

    async def add_loop(self, loop_id: str, query: str) -> ResearchLoop:
        """Add a new research loop.

        Args:
            loop_id: Unique identifier for the loop.
            query: The research query for this loop.

        Returns:
            The created ResearchLoop instance.
        """
        loop = ResearchLoop(loop_id=loop_id, query=query, status="pending")
        self._loops[loop_id] = loop
        logger.info("Loop added", loop_id=loop_id, query=query)
        return loop

    async def get_loop(self, loop_id: str) -> ResearchLoop | None:
        """Get a research loop by ID.

        Args:
            loop_id: Unique identifier for the loop.

        Returns:
            The ResearchLoop instance, or None if not found.
        """
        return self._loops.get(loop_id)

    async def update_loop_status(
        self, loop_id: str, status: LoopStatus, error: str | None = None
    ) -> None:
        """Update the status of a research loop.

        Args:
            loop_id: Unique identifier for the loop.
            status: New status for the loop.
            error: Optional error message if status is "failed".
        """
        if loop_id not in self._loops:
            logger.warning("Loop not found", loop_id=loop_id)
            return

        self._loops[loop_id].status = status
        if error:
            self._loops[loop_id].error = error
        logger.info("Loop status updated", loop_id=loop_id, status=status)

    async def add_loop_evidence(self, loop_id: str, evidence: list[Evidence]) -> None:
        """Add evidence to a research loop.

        Args:
            loop_id: Unique identifier for the loop.
            evidence: List of Evidence objects to add.
        """
        if loop_id not in self._loops:
            logger.warning("Loop not found", loop_id=loop_id)
            return

        self._loops[loop_id].evidence.extend(evidence)
        logger.debug(
            "Evidence added to loop",
            loop_id=loop_id,
            evidence_count=len(evidence),
        )

    async def increment_loop_iteration(self, loop_id: str) -> None:
        """Increment the iteration count for a research loop.

        Args:
            loop_id: Unique identifier for the loop.
        """
        if loop_id not in self._loops:
            logger.warning("Loop not found", loop_id=loop_id)
            return

        self._loops[loop_id].iteration_count += 1
        logger.debug(
            "Iteration incremented",
            loop_id=loop_id,
            iteration=self._loops[loop_id].iteration_count,
        )

    async def run_loops_parallel(
        self,
        loop_configs: list[dict[str, Any]],
        loop_func: Callable[[dict[str, Any]], Any],
        judge_handler: Any | None = None,
        budget_tracker: Any | None = None,
    ) -> list[Any]:
        """Run multiple research loops in parallel.

        Args:
            loop_configs: List of configuration dicts, each must contain 'loop_id' and 'query'.
            loop_func: Async function that takes a config dict and returns loop results.
            judge_handler: Optional JudgeHandler for early termination based on evidence sufficiency.
            budget_tracker: Optional BudgetTracker for budget enforcement.

        Returns:
            List of results from each loop (in order of completion, not original order).
        """
        logger.info("Starting parallel loops", loop_count=len(loop_configs))

        # Create loops
        for config in loop_configs:
            loop_id = config.get("loop_id")
            query = config.get("query", "")
            if loop_id:
                await self.add_loop(loop_id, query)
                await self.update_loop_status(loop_id, "running")

        # Run loops in parallel
        async def run_single_loop(config: dict[str, Any]) -> Any:
            loop_id = config.get("loop_id", "unknown")
            query = config.get("query", "")
            try:
                # Check budget before starting
                if budget_tracker:
                    exceeded, reason = budget_tracker.check_budget(loop_id)
                    if exceeded:
                        await self.update_loop_status(loop_id, "cancelled", error=reason)
                        logger.warning(
                            "Loop cancelled due to budget", loop_id=loop_id, reason=reason
                        )
                        return None

                # If loop_func supports periodic checkpoints, we could check judge here
                # For now, the loop_func itself handles judge checks internally
                result = await loop_func(config)

                # Final check with judge if available
                if judge_handler and query:
                    should_complete, reason = await self.check_loop_completion(
                        loop_id, query, judge_handler
                    )
                    if should_complete:
                        logger.info(
                            "Loop completed early based on judge assessment",
                            loop_id=loop_id,
                            reason=reason,
                        )

                await self.update_loop_status(loop_id, "completed")
                return result
            except Exception as e:
                error_msg = str(e)
                await self.update_loop_status(loop_id, "failed", error=error_msg)
                logger.error("Loop failed", loop_id=loop_id, error=error_msg)
                raise

        results = await asyncio.gather(
            *(run_single_loop(config) for config in loop_configs),
            return_exceptions=True,
        )

        # Log completion
        completed = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - completed
        logger.info(
            "Parallel loops completed",
            total=len(loop_configs),
            completed=completed,
            failed=failed,
        )

        return results

    async def wait_for_loops(
        self, loop_ids: list[str], timeout: float | None = None
    ) -> list[ResearchLoop]:
        """Wait for loops to complete.

        Args:
            loop_ids: List of loop IDs to wait for.
            timeout: Optional timeout in seconds.

        Returns:
            List of ResearchLoop instances (may be incomplete if timeout occurs).
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            loops = [self._loops.get(loop_id) for loop_id in loop_ids]
            all_complete = all(
                loop and loop.status in ("completed", "failed", "cancelled") for loop in loops
            )

            if all_complete:
                return [loop for loop in loops if loop is not None]

            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    logger.warning("Timeout waiting for loops", timeout=timeout)
                    return [loop for loop in loops if loop is not None]

            await asyncio.sleep(0.1)  # Small delay to avoid busy waiting

    async def cancel_loop(self, loop_id: str) -> None:
        """Cancel a research loop.

        Args:
            loop_id: Unique identifier for the loop.
        """
        await self.update_loop_status(loop_id, "cancelled")
        logger.info("Loop cancelled", loop_id=loop_id)

    async def get_all_loops(self) -> list[ResearchLoop]:
        """Get all research loops.

        Returns:
            List of all ResearchLoop instances.
        """
        return list(self._loops.values())

    async def sync_loop_evidence_to_state(self, loop_id: str) -> None:
        """Synchronize evidence from a loop to the global state.

        Args:
            loop_id: Unique identifier for the loop.
        """
        if loop_id not in self._loops:
            logger.warning("Loop not found", loop_id=loop_id)
            return

        loop = self._loops[loop_id]
        state = get_workflow_state()
        added_count = state.add_evidence(loop.evidence)
        logger.debug(
            "Loop evidence synced to state",
            loop_id=loop_id,
            evidence_count=len(loop.evidence),
            added_count=added_count,
        )

    async def get_shared_evidence(self) -> list[Evidence]:
        """Get evidence from the global state.

        Returns:
            List of Evidence objects from the global state.
        """
        state = get_workflow_state()
        return state.evidence

    async def get_loop_evidence(self, loop_id: str) -> list[Evidence]:
        """Get evidence collected by a specific loop.

        Args:
            loop_id: Loop identifier.

        Returns:
            List of Evidence objects from the loop.
        """
        if loop_id not in self._loops:
            return []

        return self._loops[loop_id].evidence

    async def check_loop_completion(
        self, loop_id: str, query: str, judge_handler: Any
    ) -> tuple[bool, str]:
        """Check if a loop should complete using judge assessment.

        Args:
            loop_id: Loop identifier.
            query: Research query.
            judge_handler: JudgeHandler instance.

        Returns:
            Tuple of (should_complete: bool, reason: str).
        """
        evidence = await self.get_loop_evidence(loop_id)

        if not evidence:
            return False, "No evidence collected yet"

        try:
            assessment = await judge_handler.assess(query, evidence)
            if assessment.sufficient:
                return True, f"Judge assessment: {assessment.reasoning}"
            return False, f"Judge assessment: {assessment.reasoning}"
        except Exception as e:
            logger.error("Judge assessment failed", error=str(e), loop_id=loop_id)
            return False, f"Judge assessment failed: {e!s}"
