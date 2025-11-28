"""Budget tracking for research loops.

Tracks token usage, time elapsed, and iteration counts per loop and globally.
Enforces budget constraints to prevent infinite loops and excessive resource usage.
"""

import time

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class BudgetStatus(BaseModel):
    """Status of a budget (tokens, time, iterations)."""

    tokens_used: int = Field(default=0, description="Total tokens used")
    tokens_limit: int = Field(default=100000, description="Token budget limit", ge=0)
    time_elapsed_seconds: float = Field(default=0.0, description="Time elapsed", ge=0.0)
    time_limit_seconds: float = Field(
        default=600.0, description="Time budget limit (10 min default)", ge=0.0
    )
    iterations: int = Field(default=0, description="Number of iterations completed", ge=0)
    iterations_limit: int = Field(default=10, description="Maximum iterations", ge=1)
    iteration_tokens: dict[int, int] = Field(
        default_factory=dict,
        description="Tokens used per iteration (iteration number -> token count)",
    )

    def is_exceeded(self) -> bool:
        """Check if any budget limit has been exceeded.

        Returns:
            True if any limit is exceeded, False otherwise.
        """
        return (
            self.tokens_used >= self.tokens_limit
            or self.time_elapsed_seconds >= self.time_limit_seconds
            or self.iterations >= self.iterations_limit
        )

    def remaining_tokens(self) -> int:
        """Get remaining token budget.

        Returns:
            Remaining tokens (may be negative if exceeded).
        """
        return self.tokens_limit - self.tokens_used

    def remaining_time_seconds(self) -> float:
        """Get remaining time budget.

        Returns:
            Remaining time in seconds (may be negative if exceeded).
        """
        return self.time_limit_seconds - self.time_elapsed_seconds

    def remaining_iterations(self) -> int:
        """Get remaining iteration budget.

        Returns:
            Remaining iterations (may be negative if exceeded).
        """
        return self.iterations_limit - self.iterations

    def add_iteration_tokens(self, iteration: int, tokens: int) -> None:
        """Add tokens for a specific iteration.

        Args:
            iteration: Iteration number (1-indexed).
            tokens: Number of tokens to add.
        """
        if iteration not in self.iteration_tokens:
            self.iteration_tokens[iteration] = 0
        self.iteration_tokens[iteration] += tokens
        # Also add to total tokens
        self.tokens_used += tokens

    def get_iteration_tokens(self, iteration: int) -> int:
        """Get tokens used for a specific iteration.

        Args:
            iteration: Iteration number.

        Returns:
            Token count for the iteration, or 0 if not found.
        """
        return self.iteration_tokens.get(iteration, 0)


class BudgetTracker:
    """Tracks budgets per loop and globally."""

    def __init__(self) -> None:
        """Initialize the budget tracker."""
        self._budgets: dict[str, BudgetStatus] = {}
        self._start_times: dict[str, float] = {}
        self._global_budget: BudgetStatus | None = None

    def create_budget(
        self,
        loop_id: str,
        tokens_limit: int = 100000,
        time_limit_seconds: float = 600.0,
        iterations_limit: int = 10,
    ) -> BudgetStatus:
        """Create a budget for a specific loop.

        Args:
            loop_id: Unique identifier for the loop.
            tokens_limit: Maximum tokens allowed.
            time_limit_seconds: Maximum time allowed in seconds.
            iterations_limit: Maximum iterations allowed.

        Returns:
            The created BudgetStatus instance.
        """
        budget = BudgetStatus(
            tokens_limit=tokens_limit,
            time_limit_seconds=time_limit_seconds,
            iterations_limit=iterations_limit,
        )
        self._budgets[loop_id] = budget
        logger.debug(
            "Budget created",
            loop_id=loop_id,
            tokens_limit=tokens_limit,
            time_limit=time_limit_seconds,
            iterations_limit=iterations_limit,
        )
        return budget

    def get_budget(self, loop_id: str) -> BudgetStatus | None:
        """Get the budget for a specific loop.

        Args:
            loop_id: Unique identifier for the loop.

        Returns:
            The BudgetStatus instance, or None if not found.
        """
        return self._budgets.get(loop_id)

    def add_tokens(self, loop_id: str, tokens: int) -> None:
        """Add tokens to a loop's budget.

        Args:
            loop_id: Unique identifier for the loop.
            tokens: Number of tokens to add (can be negative).
        """
        if loop_id not in self._budgets:
            logger.warning("Budget not found for loop", loop_id=loop_id)
            return
        self._budgets[loop_id].tokens_used += tokens
        logger.debug("Tokens added", loop_id=loop_id, tokens=tokens)

    def add_iteration_tokens(self, loop_id: str, iteration: int, tokens: int) -> None:
        """Add tokens for a specific iteration.

        Args:
            loop_id: Loop identifier.
            iteration: Iteration number (1-indexed).
            tokens: Number of tokens to add.
        """
        if loop_id not in self._budgets:
            logger.warning("Budget not found for loop", loop_id=loop_id)
            return

        budget = self._budgets[loop_id]
        budget.add_iteration_tokens(iteration, tokens)

        logger.debug(
            "Iteration tokens added",
            loop_id=loop_id,
            iteration=iteration,
            tokens=tokens,
            total_iteration=budget.get_iteration_tokens(iteration),
        )

    def get_iteration_tokens(self, loop_id: str, iteration: int) -> int:
        """Get tokens used for a specific iteration.

        Args:
            loop_id: Loop identifier.
            iteration: Iteration number.

        Returns:
            Token count for the iteration, or 0 if not found.
        """
        if loop_id not in self._budgets:
            return 0

        return self._budgets[loop_id].get_iteration_tokens(iteration)

    def start_timer(self, loop_id: str) -> None:
        """Start the timer for a loop.

        Args:
            loop_id: Unique identifier for the loop.
        """
        self._start_times[loop_id] = time.time()
        logger.debug("Timer started", loop_id=loop_id)

    def update_timer(self, loop_id: str) -> None:
        """Update the elapsed time for a loop.

        Args:
            loop_id: Unique identifier for the loop.
        """
        if loop_id not in self._start_times:
            logger.warning("Timer not started for loop", loop_id=loop_id)
            return
        if loop_id not in self._budgets:
            logger.warning("Budget not found for loop", loop_id=loop_id)
            return

        elapsed = time.time() - self._start_times[loop_id]
        self._budgets[loop_id].time_elapsed_seconds = elapsed
        logger.debug("Timer updated", loop_id=loop_id, elapsed=elapsed)

    def increment_iteration(self, loop_id: str) -> None:
        """Increment the iteration count for a loop.

        Args:
            loop_id: Unique identifier for the loop.
        """
        if loop_id not in self._budgets:
            logger.warning("Budget not found for loop", loop_id=loop_id)
            return
        self._budgets[loop_id].iterations += 1
        logger.debug(
            "Iteration incremented",
            loop_id=loop_id,
            iterations=self._budgets[loop_id].iterations,
        )

    def check_budget(self, loop_id: str) -> tuple[bool, str]:
        """Check if a loop's budget has been exceeded.

        Args:
            loop_id: Unique identifier for the loop.

        Returns:
            Tuple of (exceeded: bool, reason: str). Reason is empty if not exceeded.
        """
        if loop_id not in self._budgets:
            return False, ""

        budget = self._budgets[loop_id]
        self.update_timer(loop_id)  # Update time before checking

        if budget.is_exceeded():
            reasons = []
            if budget.tokens_used >= budget.tokens_limit:
                reasons.append("tokens")
            if budget.time_elapsed_seconds >= budget.time_limit_seconds:
                reasons.append("time")
            if budget.iterations >= budget.iterations_limit:
                reasons.append("iterations")
            reason = f"Budget exceeded: {', '.join(reasons)}"
            logger.warning("Budget exceeded", loop_id=loop_id, reason=reason)
            return True, reason

        return False, ""

    def can_continue(self, loop_id: str) -> bool:
        """Check if a loop can continue based on budget.

        Args:
            loop_id: Unique identifier for the loop.

        Returns:
            True if the loop can continue, False if budget is exceeded.
        """
        exceeded, _ = self.check_budget(loop_id)
        return not exceeded

    def get_budget_summary(self, loop_id: str) -> str:
        """Get a formatted summary of a loop's budget status.

        Args:
            loop_id: Unique identifier for the loop.

        Returns:
            Formatted string summary.
        """
        if loop_id not in self._budgets:
            return f"Budget not found for loop: {loop_id}"

        budget = self._budgets[loop_id]
        self.update_timer(loop_id)

        return (
            f"Loop {loop_id}: "
            f"Tokens: {budget.tokens_used}/{budget.tokens_limit} "
            f"({budget.remaining_tokens()} remaining), "
            f"Time: {budget.time_elapsed_seconds:.1f}/{budget.time_limit_seconds:.1f}s "
            f"({budget.remaining_time_seconds():.1f}s remaining), "
            f"Iterations: {budget.iterations}/{budget.iterations_limit} "
            f"({budget.remaining_iterations()} remaining)"
        )

    def reset_budget(self, loop_id: str) -> None:
        """Reset the budget for a loop.

        Args:
            loop_id: Unique identifier for the loop.
        """
        if loop_id in self._budgets:
            old_budget = self._budgets[loop_id]
            # Preserve iteration_tokens when resetting
            old_iteration_tokens = old_budget.iteration_tokens
            self._budgets[loop_id] = BudgetStatus(
                tokens_limit=old_budget.tokens_limit,
                time_limit_seconds=old_budget.time_limit_seconds,
                iterations_limit=old_budget.iterations_limit,
                iteration_tokens=old_iteration_tokens,  # Restore old iteration tokens
            )
            if loop_id in self._start_times:
                self._start_times[loop_id] = time.time()
            logger.debug("Budget reset", loop_id=loop_id)

    def set_global_budget(
        self,
        tokens_limit: int = 100000,
        time_limit_seconds: float = 600.0,
        iterations_limit: int = 10,
    ) -> None:
        """Set a global budget that applies to all loops.

        Args:
            tokens_limit: Maximum tokens allowed globally.
            time_limit_seconds: Maximum time allowed in seconds.
            iterations_limit: Maximum iterations allowed globally.
        """
        self._global_budget = BudgetStatus(
            tokens_limit=tokens_limit,
            time_limit_seconds=time_limit_seconds,
            iterations_limit=iterations_limit,
        )
        logger.debug(
            "Global budget set",
            tokens_limit=tokens_limit,
            time_limit=time_limit_seconds,
            iterations_limit=iterations_limit,
        )

    def get_global_budget(self) -> BudgetStatus | None:
        """Get the global budget.

        Returns:
            The global BudgetStatus instance, or None if not set.
        """
        return self._global_budget

    def add_global_tokens(self, tokens: int) -> None:
        """Add tokens to the global budget.

        Args:
            tokens: Number of tokens to add (can be negative).
        """
        if self._global_budget is None:
            logger.warning("Global budget not set")
            return
        self._global_budget.tokens_used += tokens
        logger.debug("Global tokens added", tokens=tokens)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough estimate: ~4 chars per token).

        Args:
            text: Text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return len(text) // 4

    def estimate_llm_call_tokens(self, prompt: str, response: str) -> int:
        """Estimate token count for an LLM call.

        Args:
            prompt: The prompt text.
            response: The response text.

        Returns:
            Estimated total token count (prompt + response).
        """
        return self.estimate_tokens(prompt) + self.estimate_tokens(response)
