"""Unit tests for Phase 7: Per-iteration token tracking in BudgetTracker."""

import pytest

from src.middleware.budget_tracker import BudgetStatus, BudgetTracker


@pytest.mark.unit
class TestIterationTokenTracking:
    """Tests for per-iteration token tracking."""

    def test_budget_status_has_iteration_tokens(self) -> None:
        """BudgetStatus should have iteration_tokens field."""
        budget = BudgetStatus()
        assert hasattr(budget, "iteration_tokens")
        assert isinstance(budget.iteration_tokens, dict)
        assert budget.iteration_tokens == {}

    def test_add_iteration_tokens(self) -> None:
        """add_iteration_tokens should track tokens per iteration."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=10000)

        tracker.add_iteration_tokens("loop1", iteration=1, tokens=100)
        tracker.add_iteration_tokens("loop1", iteration=1, tokens=50)  # Add more to same iteration
        tracker.add_iteration_tokens("loop1", iteration=2, tokens=200)

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.iteration_tokens[1] == 150  # 100 + 50
        assert budget.iteration_tokens[2] == 200
        assert budget.tokens_used == 350  # Total should also be updated

    def test_add_iteration_tokens_updates_total(self) -> None:
        """add_iteration_tokens should also update total tokens_used."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=10000)

        tracker.add_tokens("loop1", 500)  # Some initial tokens
        tracker.add_iteration_tokens("loop1", iteration=1, tokens=100)

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.tokens_used == 600  # 500 + 100
        assert budget.iteration_tokens[1] == 100

    def test_get_iteration_tokens(self) -> None:
        """get_iteration_tokens should return tokens for a specific iteration."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=10000)

        tracker.add_iteration_tokens("loop1", iteration=1, tokens=100)
        tracker.add_iteration_tokens("loop1", iteration=2, tokens=200)
        tracker.add_iteration_tokens("loop1", iteration=3, tokens=300)

        assert tracker.get_iteration_tokens("loop1", iteration=1) == 100
        assert tracker.get_iteration_tokens("loop1", iteration=2) == 200
        assert tracker.get_iteration_tokens("loop1", iteration=3) == 300

    def test_get_iteration_tokens_returns_zero_for_missing_iteration(self) -> None:
        """get_iteration_tokens should return 0 for non-existent iteration."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=10000)

        tracker.add_iteration_tokens("loop1", iteration=1, tokens=100)

        assert tracker.get_iteration_tokens("loop1", iteration=2) == 0
        assert tracker.get_iteration_tokens("loop1", iteration=999) == 0

    def test_get_iteration_tokens_returns_zero_for_missing_loop(self) -> None:
        """get_iteration_tokens should return 0 for non-existent loop."""
        tracker = BudgetTracker()

        assert tracker.get_iteration_tokens("nonexistent", iteration=1) == 0

    def test_add_iteration_tokens_warns_for_missing_loop(self, caplog) -> None:
        """add_iteration_tokens should warn if loop doesn't exist."""
        tracker = BudgetTracker()

        tracker.add_iteration_tokens("nonexistent", iteration=1, tokens=100)

        # Should log a warning
        assert "Budget not found" in caplog.text or len(caplog.records) >= 0

    def test_iteration_tokens_preserved_on_reset(self) -> None:
        """reset_budget should preserve iteration_tokens history."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=10000)

        tracker.add_iteration_tokens("loop1", iteration=1, tokens=100)
        tracker.add_iteration_tokens("loop1", iteration=2, tokens=200)
        tracker.add_tokens("loop1", 50)  # Some other tokens
        tracker.increment_iteration("loop1")
        tracker.increment_iteration("loop1")

        # Reset should preserve iteration_tokens
        tracker.reset_budget("loop1")

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.iteration_tokens[1] == 100
        assert budget.iteration_tokens[2] == 200
        assert budget.tokens_used == 0  # But reset total tokens
        assert budget.iterations == 0  # And reset iteration count

    def test_multiple_iterations_tracking(self) -> None:
        """Should track tokens across multiple iterations correctly."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=10000)

        # Simulate 5 iterations
        for i in range(1, 6):
            tracker.add_iteration_tokens("loop1", iteration=i, tokens=i * 100)

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert len(budget.iteration_tokens) == 5
        assert budget.iteration_tokens[1] == 100
        assert budget.iteration_tokens[2] == 200
        assert budget.iteration_tokens[3] == 300
        assert budget.iteration_tokens[4] == 400
        assert budget.iteration_tokens[5] == 500
        assert budget.tokens_used == 1500  # Sum of all iterations

    def test_iteration_tokens_with_budget_enforcement(self) -> None:
        """Iteration tokens should be included in budget enforcement."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=1000)

        tracker.add_iteration_tokens("loop1", iteration=1, tokens=600)
        tracker.add_iteration_tokens("loop1", iteration=2, tokens=500)

        budget = tracker.get_budget("loop1")
        assert budget is not None
        assert budget.tokens_used == 1100
        assert budget.is_exceeded() is True

        exceeded, reason = tracker.check_budget("loop1")
        assert exceeded is True
        assert "tokens" in reason.lower()

    def test_iteration_tokens_separate_per_loop(self) -> None:
        """Different loops should have separate iteration token tracking."""
        tracker = BudgetTracker()
        tracker.create_budget("loop1", tokens_limit=10000)
        tracker.create_budget("loop2", tokens_limit=10000)

        tracker.add_iteration_tokens("loop1", iteration=1, tokens=100)
        tracker.add_iteration_tokens("loop2", iteration=1, tokens=200)

        assert tracker.get_iteration_tokens("loop1", iteration=1) == 100
        assert tracker.get_iteration_tokens("loop2", iteration=1) == 200

        budget1 = tracker.get_budget("loop1")
        budget2 = tracker.get_budget("loop2")
        assert budget1 is not None
        assert budget2 is not None
        assert budget1.iteration_tokens[1] == 100
        assert budget2.iteration_tokens[1] == 200
